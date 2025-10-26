"""Simple test file for the schema module."""

import os
import tempfile
from pathlib import Path

from src.schema import SchemaManager
from src.llm.client import LLMClient


def test_basic_operations():
    """Test basic get and set operations."""
    print("=" * 60)
    print("Test 1: Basic Schema Operations")
    print("=" * 60)
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SchemaManager(
            schema_dir=temp_dir,
            schema_file="test_schema.prisma"
        )
        
        # Create a test schema
        test_schema = """generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String?
  createdAt DateTime @default(now())
}
"""
        
        # Test set_schema
        manager.set_schema(test_schema)
        print("✓ Schema saved to filesystem")
        
        # Test get_schema
        retrieved = manager.get_schema()
        assert retrieved == test_schema, "Schema content mismatch!"
        print("✓ Schema retrieved from filesystem")
        print(f"  Schema length: {len(retrieved)} characters")
        print()


def test_validation_without_llm():
    """Test validation without LLM client."""
    print("=" * 60)
    print("Test 2: Schema Validation (without LLM)")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SchemaManager(schema_dir=temp_dir)
        
        # Valid schema
        valid_schema = """generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url = env("DATABASE_URL")
}

model Post {
  id        Int      @id @default(autoincrement())
  title     String
  content   String?
  published Boolean  @default(false)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}
"""
        
        manager.set_schema(valid_schema)
        
        # Try to validate (will fail if Prisma not installed, but that's okay)
        result = manager.validate_schema(max_retries=1)
        
        print(f"✓ Validation attempted")
        print(f"  Success: {result['success']}")
        print(f"  Attempts: {result['attempts']}")
        if result['error']:
            print(f"  Error: {result['error'][:100]}...")
        print()


def test_validation_with_llm():
    """Test validation with LLM client."""
    print("=" * 60)
    print("Test 3: Schema Validation with LLM")
    print("=" * 60)
    
    try:
        llm_client = LLMClient()
    except Exception as e:
        print(f"⚠ Skipping LLM test: {e}")
        print()
        return
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SchemaManager(schema_dir=temp_dir, llm_client=llm_client)
        
        # Schema with potential issues
        test_schema = """generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url = env("DATABASE_URL")
}

model Product {
  id          Int      @id @default(autoincrement())
  name        String
  description String?
  price       Float
  inStock     Boolean  @default(true)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
}
"""
        
        manager.set_schema(test_schema)
        
        # Validate with LLM backup
        result = manager.validate_schema(max_retries=2)
        
        print(f"✓ Validation with LLM attempted")
        print(f"  Success: {result['success']}")
        print(f"  Attempts: {result['attempts']}")
        if result['error']:
            print(f"  Error: {result['error'][:100]}...")
        print()


def test_file_operations():
    """Test file system operations."""
    print("=" * 60)
    print("Test 4: File System Operations")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SchemaManager(schema_dir=temp_dir)
        
        # Check that directory was created
        assert Path(temp_dir).exists(), "Schema directory not created!"
        print("✓ Schema directory created")
        
        # Write schema
        simple_schema = """generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url = env("DATABASE_URL")
}

model Test {
  id Int @id @default(autoincrement())
}
"""
        
        manager.set_schema(simple_schema)
        
        # Check file exists
        assert manager.schema_path.exists(), "Schema file not created!"
        print(f"✓ Schema file created at: {manager.schema_path}")
        
        # Read it back
        content = manager.get_schema()
        assert content == simple_schema, "Schema content mismatch!"
        print("✓ Schema content verified")
        print()


def test_empty_schema():
    """Test edge case with empty schema."""
    print("=" * 60)
    print("Test 5: Empty Schema Handling")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = SchemaManager(schema_dir=temp_dir)
        
        # Validate empty schema
        result = manager.validate_schema(schema_content="", max_retries=1)
        
        assert not result['success'], "Empty schema should fail validation!"
        assert result['error'] == "Schema content is empty"
        print("✓ Empty schema properly rejected")
        
        # Test get_schema when file doesn't exist
        empty_content = manager.get_schema()
        assert empty_content == "", "Non-existent file should return empty string!"
        print("✓ Non-existent schema file handled gracefully")
        print()


def run_all_tests():
    """Run all tests."""
    print("\n🚀 Running Schema Module Tests\n")
    
    try:
        test_basic_operations()
        test_validation_without_llm()
        test_validation_with_llm()
        test_file_operations()
        test_empty_schema()
        
        print("=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
