"""Schema manager for Prisma schemas with filesystem storage and validation."""

import os
import subprocess
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import logging

from ..llm.client import LLMClient

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages Prisma schema files with filesystem storage and validation."""

    def __init__(
        self,
        schema_dir: str = "prisma",
        schema_file: str = "schema.prisma",
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize the schema manager.

        Args:
            schema_dir: Directory to store schema files
            schema_file: Name of the schema file
            llm_client: Optional LLM client for error fixing
        """
        self.schema_dir = Path(schema_dir)
        self.schema_file = Path(schema_file)
        self.schema_path = self.schema_dir / self.schema_file
        self.llm_client = llm_client

        # Create schema directory if it doesn't exist
        self.schema_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized SchemaManager with schema path: {self.schema_path}")

    def get_schema(self) -> str:
        """Get the Prisma schema from the filesystem.

        Returns:
            The schema content as a string

        Raises:
            FileNotFoundError: If the schema file doesn't exist
        """
        if not self.schema_path.exists():
            logger.warning(f"Schema file not found at {self.schema_path}")
            return ""
        
        with open(self.schema_path, "r") as f:
            schema_content = f.read()
        
        logger.info(f"Read schema from {self.schema_path}")
        return schema_content

    def set_schema(self, schema_content: str) -> None:
        """Set and save the Prisma schema to the filesystem.

        Args:
            schema_content: The schema content to save
        """
        with open(self.schema_path, "w") as f:
            f.write(schema_content)
        
        logger.info(f"Saved schema to {self.schema_path}")

    def _run_prisma_validate(self, schema_content: str) -> Tuple[bool, str]:
        """Run prisma validate command on the given schema.

        Args:
            schema_content: The schema content to validate

        Returns:
            A tuple of (success: bool, error_message: str)
        """
        try:
            # Write schema to a temporary file
            temp_schema_path = self.schema_dir / "temp_schema.prisma"
            with open(temp_schema_path, "w") as f:
                f.write(schema_content)

            # Run prisma validate command with absolute path
            temp_schema_abs_path = temp_schema_path.resolve()
            result = subprocess.run(
                ["prisma", "validate", f"--schema={temp_schema_abs_path}"],
                capture_output=True,
                text=True,
            )

            # Clean up temporary file
            if temp_schema_path.exists():
                temp_schema_path.unlink()

            if result.returncode == 0:
                logger.info("Prisma validation passed")
                return True, ""
            else:
                error_msg = result.stderr or result.stdout or "Unknown validation error"
                logger.error(f"Prisma validation failed: {error_msg}")
                return False, error_msg

        except FileNotFoundError:
            error_msg = "Prisma CLI not found. Please install Prisma:\n  Python: pip install prisma\n  Node.js: npm install -g prisma"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error running prisma validate: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _fix_schema_with_llm(self, schema_content: str, error_message: str) -> str:
        """Use LLM to fix the schema based on validation error.

        Args:
            schema_content: The current schema content
            error_message: The validation error message

        Returns:
            The fixed schema content
        """
        if not self.llm_client:
            logger.warning("LLM client not available for error fixing")
            return schema_content

        prompt = f"""You are a Prisma schema expert. Fix the following Prisma schema based on the error message.

Error:
{error_message}

Current Schema:
```prisma
{schema_content}
```

Please provide the fixed Prisma schema. Return ONLY the complete, corrected schema without any explanations or markdown formatting outside of the code block."""

        try:
            system_message = """You are an expert at fixing Prisma schemas. Your job is to identify and fix syntax errors, validation issues, and schema problems in Prisma schema files.
            
When fixing schemas:
1. Ensure all model definitions are correct
2. Check that field types are valid
3. Verify relation syntax is correct
4. Do not change or add any extra information such as relations, fields, etc.

Return only the complete fixed schema in a prisma code block."""

            fixed_schema = self.llm_client.chat_completion(
                user_message=prompt,
                system_message=system_message
            )

            # Extract schema from markdown code block if present
            if "```" in fixed_schema:
                lines = fixed_schema.split("\n")
                in_code_block = False
                schema_lines = []
                
                for line in lines:
                    if line.strip().startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        schema_lines.append(line)
                
                fixed_schema = "\n".join(schema_lines)

            logger.info("LLM-generated schema fix")
            return fixed_schema.strip()

        except Exception as e:
            logger.error(f"Error fixing schema with LLM: {e}")
            return schema_content

    def validate_schema(
        self, schema_content: str, max_retries: int = 3
    ) -> Dict[str, Any]:
        """Validate the schema with automatic retry and LLM-based fixing.

        Args:
            schema_content: Optional schema content to validate. If None, reads from filesystem.
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            A dictionary with success status, error message, and fixed schema
        """

        if not schema_content:
            return {
                "success": False,
                "error": "Schema content is empty",
                "fixed_schema": "",
                "attempts": 0,
            }

        attempts = 0
        current_schema = schema_content

        while attempts < max_retries:
            attempts += 1
            logger.info(f"Validating schema (attempt {attempts}/{max_retries})")

            # Try to validate the schema
            success, error_message = self._run_prisma_validate(current_schema)

            if success:
                logger.info("Schema validation successful")
                # Save the validated schema
                if current_schema != schema_content:
                    self.set_schema(current_schema)
                
                return {
                    "success": True,
                    "error": "",
                    "fixed_schema": current_schema,
                    "attempts": attempts,
                }

            # If validation failed and we have retries left
            if attempts < max_retries and self.llm_client:
                logger.info(f"Validation failed, attempting to fix with LLM (attempt {attempts})")
                current_schema = self._fix_schema_with_llm(current_schema, error_message)
            else:
                # No more retries or no LLM client
                break

        # All attempts failed
        logger.error(f"Schema validation failed after {attempts} attempts")
        return {
            "success": False,
            "error": error_message,
            "fixed_schema": current_schema,
            "attempts": attempts,
        }


# Global schema manager instance
schema_manager = SchemaManager()
