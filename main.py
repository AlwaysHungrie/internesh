"""Main application entry point."""

import asyncio
import logging
import sys
from typing import Optional

from src.agents.unconfigured_agent import UnconfiguredAgent
from src.llm.client import LLMClient
from src.database.connection import db_client
from src.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InterNeshApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        self.agent: Optional[UnconfiguredAgent] = None
        self.llm_client: Optional[LLMClient] = None
        
    def initialize(self):
        """Initialize all components."""
        try:
            logger.info("Initializing InterNesh application...")
            
            # Test database connection
            if db_client.test_connection():
                logger.info("Database connection test successful")
            else:
                logger.warning("Database connection test failed - continuing without database")
            
            # Initialize LLM client
            self.llm_client = LLMClient()
            logger.info("LLM client initialized successfully")
            
            # Initialize agent
            self.agent = UnconfiguredAgent(llm_client=self.llm_client)
            logger.info("Agent initialized successfully")
            
            logger.info("Application initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            sys.exit(1)
    
    async def run_interactive(self):
        """Run interactive chat mode."""
        if not self.agent:
            logger.error("Agent not initialized")
            return
        
        logger.info("Starting interactive chat mode...")
        print("Welcome to InterNesh! Type 'quit' or 'exit' to end the conversation.")
        print("=" * 50)
        
        while True:
            try:
                # Use asyncio to handle input in a non-blocking way
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\nYou: "
                )
                user_input = user_input.strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Run agent (this is still synchronous, but we can await it)
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self.agent.run, user_input
                )
                
                if result["error"]:
                    print(f"Error: {result['error']}")
                else:
                    print(f"Assistant: {result['response']}")
                
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive mode: {e}")
                print(f"Error: {e}")
    


def main():
    """Main entry point."""
    # Create and initialize app
    app = InterNeshApp()
    app.initialize()
    
    # Run interactive mode
    asyncio.run(app.run_interactive())


if __name__ == "__main__":
    main()
