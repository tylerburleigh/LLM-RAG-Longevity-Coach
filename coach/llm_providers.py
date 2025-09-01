"""LLM provider management for the coach package.

This module handles the initialization and configuration of different LLM providers
(OpenAI, Google, etc.) in a centralized way.
"""

import os
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel

from coach.config import config
from coach.exceptions import (
    LLMInitializationException,
    UnsupportedModelException,
    APIKeyMissingException
)
from coach.types import ModelName, LLMConfig
from coach.embeddings import EmbeddingFactory

# Try to import callbacks
try:
    from coach.callbacks import callback_manager
    CALLBACKS_AVAILABLE = True
except ImportError:
    CALLBACKS_AVAILABLE = False


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def get_model_names(self) -> list[str]:
        """Get list of supported model names for this provider."""
        pass
    
    @abstractmethod
    def create_llm(self, model_name: str, **kwargs) -> BaseChatModel:
        """Create an LLM instance for the given model."""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """Validate that the required API key is present."""
        pass


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI models."""
    
    def get_model_names(self) -> list[str]:
        return ["gpt-5", "o3", "o4-mini"]
    
    def validate_api_key(self) -> bool:
        api_key = config.get_api_key("openai")
        return api_key is not None and len(api_key) > 0
    
    def create_llm(self, model_name: str, **kwargs) -> BaseChatModel:
        if not self.validate_api_key():
            raise APIKeyMissingException(
                "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
            )
        
        temperature = kwargs.get("temperature", config.DEFAULT_TEMPERATURE)
        
        # For reasoning models, use the reasoning parameter with dict format
        if model_name in ["gpt-5", "o3", "o4-mini"]:
            reasoning_effort = kwargs.get("reasoning_effort", config.DEFAULT_REASONING_EFFORT)
            
            # Create reasoning dict with effort and summary
            reasoning = {
                "effort": reasoning_effort,
                "summary": "auto"
            }
            
            # Create kwargs without reasoning_effort since we're using reasoning dict
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ["temperature", "reasoning_effort"]}
            
            return ChatOpenAI(
                model_name=model_name,
                temperature=temperature,
                reasoning=reasoning,
                output_version="responses/v1",  # Use Responses API for proper formatting
                **filtered_kwargs
            )
        else:
            return ChatOpenAI(
                model_name=model_name,
                temperature=temperature,
                **kwargs
            )


class GoogleProvider(LLMProvider):
    """Provider for Google Gemini models."""
    
    def get_model_names(self) -> list[str]:
        return ["gemini-2.5-pro"]
    
    def validate_api_key(self) -> bool:
        api_key = config.get_api_key("google")
        return api_key is not None and len(api_key) > 0
    
    def create_llm(self, model_name: str, **kwargs) -> BaseChatModel:
        if not self.validate_api_key():
            raise APIKeyMissingException(
                "Google API key not found. Please set the GOOGLE_API_KEY environment variable."
            )
        
        temperature = kwargs.get("temperature", config.DEFAULT_TEMPERATURE)
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            **kwargs
        )


class LLMFactory:
    """Factory class for creating LLM instances."""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """Register the default LLM providers."""
        openai_provider = OpenAIProvider()
        google_provider = GoogleProvider()
        
        # Register each model with its provider
        for model in openai_provider.get_model_names():
            self.providers[model] = openai_provider
        
        for model in google_provider.get_model_names():
            self.providers[model] = google_provider
    
    def register_provider(self, model_name: str, provider: LLMProvider):
        """Register a custom provider for a model.
        
        Args:
            model_name: The name of the model
            provider: The provider instance
        """
        self.providers[model_name] = provider
    
    def create_llm(
        self, 
        model_name: Optional[str] = None,
        use_callbacks: bool = True,
        **kwargs
    ) -> BaseChatModel:
        """Create an LLM instance.
        
        Args:
            model_name: Name of the model to use. If None, uses default from config.
            use_callbacks: Whether to add callbacks for monitoring
            **kwargs: Additional arguments to pass to the LLM constructor
            
        Returns:
            An initialized LLM instance
            
        Raises:
            UnsupportedModelException: If the model is not supported
            LLMInitializationException: If initialization fails
        """
        if model_name is None:
            model_name = config.DEFAULT_LLM_MODEL
        
        if model_name not in self.providers:
            raise UnsupportedModelException(
                f"Model '{model_name}' is not supported. "
                f"Supported models: {list(self.providers.keys())}"
            )
        
        provider = self.providers[model_name]
        
        try:
            # Add callbacks if available and requested
            if use_callbacks and CALLBACKS_AVAILABLE:
                if 'callbacks' not in kwargs:
                    kwargs['callbacks'] = callback_manager.get_callbacks()
            
            return provider.create_llm(model_name, **kwargs)
        except Exception as e:
            raise LLMInitializationException(
                f"Failed to initialize LLM '{model_name}': {str(e)}"
            ) from e
    
    def get_supported_models(self) -> list[str]:
        """Get list of all supported model names."""
        return list(self.providers.keys())
    
    def validate_model(self, model_name: str) -> bool:
        """Check if a model is supported.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if the model is supported, False otherwise
        """
        return model_name in self.providers


# Create a singleton factory instance
llm_factory = LLMFactory()


# Convenience functions
def get_llm(model_name: Optional[str] = None, use_callbacks: bool = True, **kwargs) -> BaseChatModel:
    """Get an LLM instance using the default factory.
    
    Args:
        model_name: Name of the model to use. If None, uses default from config.
        use_callbacks: Whether to add callbacks for monitoring
        **kwargs: Additional arguments to pass to the LLM constructor
        
    Returns:
        An initialized LLM instance
    """
    return llm_factory.create_llm(model_name, use_callbacks=use_callbacks, **kwargs)


def get_embeddings(provider: str = "openai", model: Optional[str] = None, **kwargs):
    """Get an embeddings instance.
    
    Args:
        provider: The embedding provider ('openai' or 'google')
        model: The model name (optional, uses config default)
        **kwargs: Additional parameters for the embedding model
        
    Returns:
        A LangChain embeddings instance
    """
    return EmbeddingFactory.create_embeddings(provider, model, **kwargs)


def get_supported_models() -> list[str]:
    """Get list of all supported model names."""
    return llm_factory.get_supported_models()