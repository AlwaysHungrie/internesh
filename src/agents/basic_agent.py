"""LangGraph agent implementation."""

from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import logging
import uuid

from ..llm.client import LLMClient

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the LangGraph agent."""
    messages: List[BaseMessage]
    user_input: str
    response: str
    error: Optional[str]
    metadata: Dict[str, Any]


class BasicAgent:
    """Basic LangGraph agent implementation."""
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None
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
        
        logger.info("BasicAgent initialized successfully")
    
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
        
        # Add edges
        workflow.add_edge(START, "process_input")
        workflow.add_edge("process_input", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _process_input(self, state: AgentState) -> AgentState:
        """Process user input and prepare messages."""
        try:
            # Clear any previous errors
            if "error" in state:
                logger.info(f"Clearing previous error: {state['error']}")
                del state["error"]
            
            # Prepare messages
            messages = [SystemMessage(content=self.system_prompt)]
            
            # Add current user input
            messages.append(HumanMessage(content=state["user_input"]))
            
            state["messages"] = messages
            
            logger.info("Processed input successfully")
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            state["error"] = str(e)
        
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """Generate response using LLM."""
        try:
            # Check if there was a previous error and log it
            if state.get("error"):
                logger.warning(f"Skipping response generation due to previous error: {state['error']}")
                # Set a fallback response instead of skipping
                state["response"] = f"I encountered an error earlier: {state['error']}. Please try again."
                return state
            
            logger.info(f"Generating response for {len(state['messages'])} messages")
            response = self.llm_client.generate_response(state["messages"])
            
            if not response or response.strip() == "":
                logger.warning("LLM returned empty response")
                state["response"] = "I apologize, but I couldn't generate a response. Please try again."
            else:
                state["response"] = response
                logger.info(f"Generated response successfully: {len(response)} characters")
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            state["error"] = str(e)
            state["response"] = f"I encountered an error: {str(e)}"
        
        return state
    
    
    def run(
        self,
        user_input: str,
        metadata: Optional[Dict[str, Any]] = None
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
                metadata=metadata or {}
            )
            
            # Run the graph
            result = self.graph.invoke(initial_state)
            
            response = result.get("response", "")
            error = result.get("error")
            
            # If we have an error but no response, provide a fallback
            if error and not response:
                response = f"I encountered an error: {error}"
            
            return {
                "response": response,
                "error": error,
                "metadata": metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Error running agent: {e}")
            return {
                "response": "",
                "error": str(e),
                "metadata": metadata or {}
            }
    
    def stream_run(
        self,
        user_input: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Stream the agent response.
        
        Args:
            user_input: User's input message
            metadata: Optional metadata
            
        Yields:
            Chunks of the response
        """
        try:
            # Prepare messages
            messages = [SystemMessage(content=self.system_prompt)]
            messages.append(HumanMessage(content=user_input))
            
            # Stream response
            for chunk in self.llm_client.stream_response(messages):
                yield chunk
            
        except Exception as e:
            logger.error(f"Error streaming agent response: {e}")
            yield f"Error: {str(e)}"
