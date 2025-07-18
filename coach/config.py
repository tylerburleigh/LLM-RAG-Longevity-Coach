"""Configuration module for the coach package.

This module centralizes all configuration settings used throughout the coach package.
Settings can be overridden via environment variables.
"""

import os
from typing import Optional


class Config:
    """Central configuration class for the coach package."""
    
    # Vector Store Configuration
    VECTOR_STORE_FOLDER: str = os.getenv("VECTOR_STORE_FOLDER", "vector_store_data")
    FAISS_INDEX_FILENAME: str = os.getenv("FAISS_INDEX_FILENAME", "faiss_index.bin")
    DOCUMENTS_FILENAME: str = os.getenv("DOCUMENTS_FILENAME", "documents.pkl")
    
    # Optional Features
    USE_LANGCHAIN_CHAINS: bool = os.getenv("USE_LANGCHAIN_CHAINS", "false").lower() == "true"
    
    # Embedding Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "3072"))
    
    # LLM Configuration
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "o3")
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "1.0"))
    SUPPORTED_MODELS: list = ["o3", "o4-mini", "gemini-2.5-pro"]
    
    # Search Configuration
    DEFAULT_TOP_K: int = int(os.getenv("DEFAULT_TOP_K", "5"))
    RRF_K: int = int(os.getenv("RRF_K", "60"))
    SEARCH_MULTIPLIER: int = int(os.getenv("SEARCH_MULTIPLIER", "2"))  # For fetching more results before RRF
    
    # Document Processing
    DOCS_FILE: str = os.getenv("DOCS_FILE", "docs.jsonl")
    MAX_DOCUMENT_LENGTH: int = int(os.getenv("MAX_DOCUMENT_LENGTH", "10000"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # API Keys (handled separately, just documenting expected env vars)
    # OPENAI_API_KEY: Set via environment variable
    # GOOGLE_API_KEY: Set via environment variable (if using Gemini)
    
    # Insight Generation
    MAX_INSIGHTS: int = int(os.getenv("MAX_INSIGHTS", "5"))
    MAX_CLARIFYING_QUESTIONS: int = int(os.getenv("MAX_CLARIFYING_QUESTIONS", "3"))
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour default
    
    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        """Get API key for a specific provider.
        
        Args:
            provider: The provider name ('openai', 'google', etc.)
            
        Returns:
            The API key if found, None otherwise.
        """
        key_mapping = {
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        env_var = key_mapping.get(provider.lower())
        return os.getenv(env_var) if env_var else None
    
    @classmethod
    def validate(cls) -> None:
        """Validate the configuration settings.
        
        Raises:
            ValueError: If any required settings are invalid.
        """
        if cls.EMBEDDING_DIMENSION <= 0:
            raise ValueError("EMBEDDING_DIMENSION must be positive")
        
        if cls.DEFAULT_TOP_K <= 0:
            raise ValueError("DEFAULT_TOP_K must be positive")
        
        if cls.DEFAULT_TEMPERATURE < 0 or cls.DEFAULT_TEMPERATURE > 2:
            raise ValueError("DEFAULT_TEMPERATURE must be between 0 and 2")
        
        if cls.DEFAULT_LLM_MODEL not in cls.SUPPORTED_MODELS:
            raise ValueError(f"DEFAULT_LLM_MODEL must be one of {cls.SUPPORTED_MODELS}")


# Create a singleton instance
config = Config()