"""Data models for the coach package.

This module contains all Pydantic models used throughout the coach package
for data validation and structured outputs.
"""

from typing import List, Literal, Dict, Any, Optional
from pydantic import BaseModel, Field


# --- Document Models ---
class Document(BaseModel):
    """Represents a document in the knowledge base."""
    doc_id: str = Field(..., description="Unique identifier for the document")
    text: str = Field(..., description="The full text content of the document")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata about the document"
    )


# --- Clarifying Questions Models ---
class ClarifyingQuestions(BaseModel):
    """A list of clarifying questions to ask the user."""
    questions: List[str] = Field(
        ..., 
        description="A list of 2-3 clarifying questions.",
        min_items=1,
        max_items=3
    )


# --- Insight Models ---
class Insight(BaseModel):
    """A single insight or recommendation."""
    insight: str = Field(
        ..., 
        description="The core insight or recommendation."
    )
    rationale: str = Field(
        ...,
        description="The supporting analysis and rationale for the insight, based on the provided context. (Don't include meta-comments)"
    )
    data_summary: str = Field(
        ...,
        description="A summary of the specific data points from the 'Context from health data' that were used to form the insight."
    )
    importance: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="An assessment of how important this insight is for the user's health."
    )
    confidence: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="Your confidence in the insight based on the available data."
    )


class Insights(BaseModel):
    """A list of insights or recommendations."""
    insights: List[Insight] = Field(
        ..., 
        description="A list of 1-5 insights or recommendations.",
        min_items=1,
        max_items=5
    )


# --- Fine-Tune Suggestion Models ---
class FineTuneSuggestion(BaseModel):
    """A single suggestion for a new measurement, data, test, or diagnostic to collect."""
    suggestion: str = Field(
        ..., 
        description="The core suggestion."
    )
    rationale: str = Field(
        ...,
        description="The supporting analysis and rationale for the suggestion."
    )
    importance: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="An assessment of how important this suggestion is for the user's health."
    )
    confidence: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="Your confidence in the suggestion based on the available data."
    )


class FineTuneSuggestions(BaseModel):
    """A list of suggestions for new measurements, data, tests, or diagnostics to collect."""
    suggestions: List[FineTuneSuggestion] = Field(
        ...,
        description="A list of 1-3 suggestions for new data to collect.",
        min_items=1,
        max_items=3
    )


# --- Search Strategy Models ---
class SearchStrategy(BaseModel):
    """Represents a search strategy for retrieving relevant documents."""
    key_topics: List[str] = Field(
        ...,
        description="Key topics to search for"
    )
    data_points: List[str] = Field(
        ...,
        description="Specific data points that would be valuable"
    )
    rationale: str = Field(
        ...,
        description="How this information will help answer the query"
    )


class SearchQueries(BaseModel):
    """Categorized search queries for different health aspects."""
    queries_by_category: Dict[str, List[str]] = Field(
        ...,
        description="Dictionary mapping categories to lists of search queries"
    )


# --- Processing Result Models ---
class DocumentProcessingResult(BaseModel):
    """Result of processing a document."""
    success: bool = Field(..., description="Whether processing was successful")
    documents: List[Document] = Field(
        default_factory=list,
        description="List of extracted documents"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if processing failed"
    )