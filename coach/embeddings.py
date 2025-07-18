# coach/embeddings.py
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.embeddings import Embeddings

from coach.config import config
from coach.exceptions import EmbeddingException
from coach.types import EmbeddingVector


class EmbeddingFactory:
    """Factory for creating embedding instances."""
    
    @staticmethod
    def create_embeddings(
        provider: str = "openai",
        model: Optional[str] = None,
        **kwargs
    ) -> Embeddings:
        """
        Create an embedding instance based on the provider.
        
        Args:
            provider: The embedding provider ('openai' or 'google')
            model: The model name (optional, uses config default)
            **kwargs: Additional parameters for the embedding model
        
        Returns:
            A LangChain embeddings instance
            
        Raises:
            EmbeddingException: If the provider is not supported or configuration is invalid
        """
        try:
            if provider.lower() == "openai":
                api_key = config.get_api_key("openai")
                if not api_key:
                    raise EmbeddingException("OpenAI API key not found")
                
                return OpenAIEmbeddings(
                    model=model or config.EMBEDDING_MODEL,
                    openai_api_key=api_key,
                    **kwargs
                )
            
            elif provider.lower() == "google":
                api_key = config.get_api_key("google")
                if not api_key:
                    raise EmbeddingException("Google API key not found")
                
                return GoogleGenerativeAIEmbeddings(
                    model=model or "models/embedding-001",
                    google_api_key=api_key,
                    **kwargs
                )
            
            else:
                raise EmbeddingException(f"Unsupported embedding provider: {provider}")
                
        except Exception as e:
            raise EmbeddingException(f"Failed to create embeddings: {str(e)}") from e


class EmbeddingManager:
    """Manager for embedding operations with caching and error handling."""
    
    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
    
    def embed_documents(self, texts: List[str]) -> List[EmbeddingVector]:
        """
        Embed a list of documents.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingException: If embedding fails
        """
        try:
            return self.embeddings.embed_documents(texts)
        except Exception as e:
            raise EmbeddingException(f"Failed to embed documents: {str(e)}") from e
    
    def embed_query(self, text: str) -> EmbeddingVector:
        """
        Embed a single query.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            EmbeddingException: If embedding fails
        """
        try:
            return self.embeddings.embed_query(text)
        except Exception as e:
            raise EmbeddingException(f"Failed to embed query: {str(e)}") from e