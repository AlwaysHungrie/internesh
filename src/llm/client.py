"""LLM wrapper class for OpenAI integration."""

from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks.base import BaseCallbackHandler
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper class for OpenAI LLM operations."""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ):
        """Initialize the LLM client.
        
        Args:
            model: OpenAI model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            callbacks: Optional callback handlers
        """
        if not settings.openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file or environment.")
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.openai_api_key,
            callbacks=callbacks
        )
        
        logger.info(f"Initialized LLM client with model: {model}")
    
    def generate_response(
        self,
        messages: List[BaseMessage],
        **kwargs
    ) -> str:
        """Generate a response from the LLM.
        
        Args:
            messages: List of messages for the conversation
            **kwargs: Additional parameters for the LLM
            
        Returns:
            Generated response as string
        """
        try:
            logger.info(f"Calling LLM with {len(messages)} messages")
            response = self.llm.invoke(messages, **kwargs)
            
            if not response or not response.content:
                logger.warning("LLM returned empty or None response")
                return ""
            
            logger.info(f"LLM response received: {len(response.content)} characters")
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            logger.error(f"Messages sent to LLM: {[msg.content[:100] + '...' if len(msg.content) > 100 else msg.content for msg in messages]}")
            raise
    
    def chat_completion(
        self,
        user_message: str,
        system_message: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Generate a chat completion.
        
        Args:
            user_message: The user's message
            system_message: Optional system message
            conversation_history: Optional conversation history
            
        Returns:
            Generated response
        """
        messages = []
        
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=user_message))
        
        return self.generate_response(messages)
    
