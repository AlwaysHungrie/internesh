"""LangGraph agent implementation."""

from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import logging
import uuid

from src.config import settings

from ..llm.client import LLMClient
from ..schema.schema_manager import schema_manager

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the LangGraph agent."""

    messages: List[BaseMessage]
    user_input: str
    response: str
    error: Optional[str]
    metadata: Dict[str, Any]


class UnconfiguredAgent:
    """Unconfigured LangGraph agent implementation."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
    ):
        """Initialize the agent.

        Args:
            llm_client: LLM client instance
            tools: List of tools available to the agent
            system_prompt: System prompt for the agent
        """
        self.llm_client = llm_client or LLMClient()
        self.tools = tools or []
        self.system_prompt = system_prompt or self._get_default_system_prompt()

        # Create the graph
        self.graph = self._create_graph()

        logger.info("UnconfiguredAgent initialized successfully")

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt."""
        return """You are a helpful AI assistant. You can help users with various tasks including:
        - Answering questions
        - Providing information
        - Having conversations
        - Helping with problem-solving
        
        Be helpful, accurate, and friendly in your responses."""

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("process_input", self._process_input)
        workflow.add_node("generate_response", self._generate_response)

        # Add edges - process_input now goes directly to END
        workflow.add_edge(START, "process_input")
        workflow.add_edge("process_input", END)
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    def _process_input(self, state: AgentState) -> AgentState:
        """Process user input and generate a valid Prisma schema."""
        try:
            # Clear any previous errors
            if "error" in state:
                logger.info(f"Clearing previous error: {state['error']}")
                del state["error"]

            logger.info("Generating Prisma schema from user input")
            
            # Prompt the LLM to generate a Prisma schema from user input
            user_input = state["user_input"]
            
            schema_prompt = f"""Based on the following user requirements, generate a complete Prisma schema file.

User Requirements:
{user_input}

Please generate a valid Prisma schema that matches these requirements. Include all necessary models, fields, and relationships.

Return ONLY the Prisma schema, starting with 'generator client' and including the 'datasource db' block. Use the postgresql provider with 'postgresql' as the provider."""

            system_message = f"""You are a Prisma schema expert. Generate valid, production-ready Prisma schemas based on user requirements.

Requirements:
- Always include 'generator client' and 'datasource db' blocks
- Use PostgreSQL as the database provider
- Define all necessary models with appropriate fields
- Use proper Prisma field types (String, Int, Float, Boolean, DateTime, Json, etc.)
- Include necessary relations between models
- Add appropriate constraints and indexes when needed
- {settings.database_url} is the database URL

Return only the complete, valid Prisma schema without any additional explanations."""

            # Generate the schema using LLM
            schema_content = self.llm_client.chat_completion(
                user_message=schema_prompt,
                system_message=system_message
            )
            
            # Clean up the schema - remove markdown code blocks if present
            if "```" in schema_content:
                lines = schema_content.split("\n")
                in_code_block = False
                schema_lines = []
                
                for line in lines:
                    if line.strip().startswith("```"):
                        in_code_block = not in_code_block
                        continue
                    if in_code_block:
                        schema_lines.append(line)
                
                schema_content = "\n".join(schema_lines)
            
            schema_content = schema_content.strip()
            
            logger.info(f"Generated schema with {len(schema_content)} characters")
            
            # Validate and fix the schema using schema_manager
            # Initialize schema_manager with the LLM client for auto-fixing
            schema_manager.llm_client = self.llm_client
            
            validation_result = schema_manager.validate_schema(
                schema_content=schema_content,
                max_retries=3
            )
            
            if validation_result["success"]:
                # Save the validated schema
                schema_manager.set_schema(validation_result["fixed_schema"])
                logger.info("Schema generated and validated successfully")
                
                state["response"] = f"Successfully generated and validated Prisma schema!\n\nSchema saved to {schema_manager.schema_path}\n\nGenerated schema:\n{validation_result['fixed_schema']}"
                state["error"] = None
            else:
                logger.error(f"Schema validation failed: {validation_result['error']}")
                state["response"] = f"Failed to validate the generated schema after {validation_result['attempts']} attempts.\n\nError: {validation_result['error']}\n\nGenerated schema:\n{schema_content}"
                state["error"] = validation_result["error"]

            logger.info("Processed input successfully")

        except Exception as e:
            logger.error(f"Error processing input: {e}")
            state["error"] = str(e)
            state["response"] = f"I encountered an error while generating the schema: {str(e)}"

        return state

    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate response using LLM."""
        try:
            # Check if there was a previous error and log it
            if state.get("error"):
                logger.warning(
                    f"Skipping response generation due to previous error: {state['error']}"
                )
                # Set a fallback response instead of skipping
                state["response"] = (
                    f"I encountered an error earlier: {state['error']}. Please try again."
                )
                return state

            logger.info(f"Generating response for {len(state['messages'])} messages")
            response = self.llm_client.generate_response(state["messages"])

            if not response or response.strip() == "":
                logger.warning("LLM returned empty response")
                state["response"] = (
                    "I apologize, but I couldn't generate a response. Please try again."
                )
            else:
                state["response"] = response
                logger.info(
                    f"Generated response successfully: {len(response)} characters"
                )

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            state["error"] = str(e)
            state["response"] = f"I encountered an error: {str(e)}"

        return state

    def run(
        self, user_input: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the agent with user input.

        Args:
            user_input: User's input message
            metadata: Optional metadata

        Returns:
            Agent response and metadata
        """
        try:
            # Prepare initial state
            initial_state = AgentState(
                messages=[],
                user_input=user_input,
                response="",
                error=None,
                metadata=metadata or {},
            )

            # Run the graph
            result = self.graph.invoke(initial_state)

            response = result.get("response", "")
            error = result.get("error")

            # If we have an error but no response, provide a fallback
            if error and not response:
                response = f"I encountered an error: {error}"

            return {"response": response, "error": error, "metadata": metadata or {}}

        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return {"response": "", "error": str(e), "metadata": metadata or {}}
