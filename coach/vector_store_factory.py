# coach/vector_store_factory.py
"""Factory for creating vector store instances."""

from typing import Optional
from coach.langchain_vector_store import LangChainVectorStore


def create_vector_store(
    store_folder: Optional[str] = None,
    **kwargs
) -> LangChainVectorStore:
    """
    Create a vector store instance.
    
    Args:
        store_folder: Directory to store vector store files
        **kwargs: Additional parameters for vector store initialization
        
    Returns:
        A LangChain vector store instance
    """
    return LangChainVectorStore(
        store_folder=store_folder,
        **kwargs
    )


def get_vector_store(**kwargs) -> LangChainVectorStore:
    """
    Get a vector store instance.
    
    Args:
        **kwargs: Additional parameters for vector store initialization
        
    Returns:
        A LangChain vector store instance
    """
    return create_vector_store(**kwargs)