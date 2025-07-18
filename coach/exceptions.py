"""Custom exceptions for the coach package.

This module defines custom exception classes for better error handling
and debugging throughout the coach package.
"""


class CoachException(Exception):
    """Base exception class for all coach-related exceptions."""
    pass


# Vector Store Exceptions
class VectorStoreException(CoachException):
    """Base exception for vector store operations."""
    pass


class VectorStoreNotInitializedException(VectorStoreException):
    """Raised when trying to use a vector store that hasn't been initialized."""
    pass


class VectorStoreSaveException(VectorStoreException):
    """Raised when saving the vector store fails."""
    pass


class VectorStoreLoadException(VectorStoreException):
    """Raised when loading the vector store fails."""
    pass


class EmbeddingException(VectorStoreException):
    """Raised when embedding generation fails."""
    pass


# Document Processing Exceptions
class DocumentProcessingException(CoachException):
    """Base exception for document processing errors."""
    pass


class PDFExtractionException(DocumentProcessingException):
    """Raised when PDF text extraction fails."""
    pass


class DocumentStructuringException(DocumentProcessingException):
    """Raised when document structuring fails."""
    pass


class InvalidDocumentFormatException(DocumentProcessingException):
    """Raised when a document has an invalid format."""
    pass


# LLM Exceptions
class LLMException(CoachException):
    """Base exception for LLM-related errors."""
    pass


class LLMInitializationException(LLMException):
    """Raised when LLM initialization fails."""
    pass


class LLMInvocationException(LLMException):
    """Raised when LLM invocation fails."""
    pass


class UnsupportedModelException(LLMException):
    """Raised when an unsupported model is requested."""
    pass


class APIKeyMissingException(LLMException):
    """Raised when a required API key is missing."""
    pass


# Search Exceptions
class SearchException(CoachException):
    """Base exception for search-related errors."""
    pass


class SearchStrategyException(SearchException):
    """Raised when search strategy planning fails."""
    pass


class QueryGenerationException(SearchException):
    """Raised when query generation fails."""
    pass


class RetrievalException(SearchException):
    """Raised when document retrieval fails."""
    pass


# Configuration Exceptions
class ConfigurationException(CoachException):
    """Base exception for configuration errors."""
    pass


class InvalidConfigurationException(ConfigurationException):
    """Raised when configuration values are invalid."""
    pass


# Data Validation Exceptions
class ValidationException(CoachException):
    """Base exception for data validation errors."""
    pass


class InsightValidationException(ValidationException):
    """Raised when insight validation fails."""
    pass


class QuestionValidationException(ValidationException):
    """Raised when question validation fails."""
    pass


# Utility function for exception handling
def handle_exception(exception: Exception, context: str = "") -> str:
    """
    Utility function to format exception messages consistently.
    
    Args:
        exception: The exception that was raised
        context: Additional context about where the exception occurred
        
    Returns:
        Formatted error message
    """
    error_type = type(exception).__name__
    error_message = str(exception)
    
    if context:
        return f"[{error_type}] in {context}: {error_message}"
    return f"[{error_type}]: {error_message}"