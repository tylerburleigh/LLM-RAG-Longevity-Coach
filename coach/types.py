"""Common type definitions for the coach package.

This module contains type aliases and custom types used throughout the coach package
for better type hints and code clarity.
"""

from typing import TypedDict, List, Dict, Any, Optional, Callable, Union
from typing import Literal

# Type aliases for clarity
DocumentID = str
Query = str
EmbeddingVector = List[float]
Score = float
Category = str
MetadataDict = Dict[str, Any]

# Literal types for constrained values
ImportanceLevel = Literal["Low", "Medium", "High"]
ConfidenceLevel = Literal["Low", "Medium", "High"]
ModelName = Literal["o3", "o4-mini", "gemini-2.5-pro"]

# TypedDicts for structured data
class SearchResult(TypedDict):
    """Structure for a search result."""
    doc_id: DocumentID
    text: str
    score: Score
    metadata: Optional[MetadataDict]


class MessageDict(TypedDict):
    """Structure for chat messages."""
    role: Literal["user", "assistant", "system"]
    content: Union[str, Dict[str, Any]]


class InsightDict(TypedDict):
    """Structure for insight data."""
    insight: str
    rationale: str
    data_summary: str
    importance: ImportanceLevel
    confidence: ConfidenceLevel


class ProgressCallback(Callable[[str], None]):
    """Type for progress callback functions."""
    pass


# Search-related types
SearchQueryDict = Dict[Category, List[Query]]
DocumentList = List[Dict[str, Any]]

# Vector store types
class VectorStoreDocument(TypedDict):
    """Structure for documents stored in the vector store."""
    doc_id: DocumentID
    text: str
    metadata: Optional[MetadataDict]
    embedding: Optional[EmbeddingVector]


# LLM-related types
class LLMConfig(TypedDict, total=False):
    """Configuration for LLM initialization."""
    model_name: ModelName
    temperature: float
    api_key: Optional[str]
    max_tokens: Optional[int]
    timeout: Optional[int]


# Processing status types
class ProcessingStatus(TypedDict):
    """Status of a processing operation."""
    success: bool
    message: str
    data: Optional[Any]
    error: Optional[str]