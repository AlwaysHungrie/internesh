"""Simple database connection for SQL execution."""

import psycopg2
import psycopg2.extras
from typing import List, Dict, Any, Optional
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Simple database client for executing SQL queries."""

    def __init__(self):
        """Initialize database connection."""
        if not settings.database_url:
            raise ValueError("DATABASE_URL not found in environment variables")

        self.connection_url = settings.database_url
        self._connection = None

        logger.info("Database client initialized")

    def connect(self):
        """Establish database connection."""
        try:
            self._connection = psycopg2.connect(self.connection_url)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def execute_query(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Optional parameters for the query

        Returns:
            List of dictionaries representing query results
        """
        if not self._connection:
            self.connect()

        try:
            with self._connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def execute_command(self, command: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE command.

        Args:
            command: SQL command string
            params: Optional parameters for the command

        Returns:
            Number of affected rows
        """
        if not self._connection:
            self.connect()

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(command, params)
                self._connection.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            self._connection.rollback()
            raise

    def execute_script(self, script: str) -> None:
        """Execute a SQL script with multiple statements.

        Args:
            script: SQL script string
        """
        if not self._connection:
            self.connect()

        try:
            with self._connection.cursor() as cursor:
                cursor.execute(script)
                self._connection.commit()
                logger.info("SQL script executed successfully")
        except Exception as e:
            logger.error(f"Error executing script: {e}")
            self._connection.rollback()
            raise

    def test_connection(self) -> bool:
        """Test database connection.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            self.connect()
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
        finally:
            self.disconnect()


# Global database client instance
db_client = DatabaseClient()
