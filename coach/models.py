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
        description="A list of 0-2 clarifying questions. Return an empty list if the query is already specific enough.",
        min_items=0,
        max_items=2
    )


# --- Insight Models ---
class Insight(BaseModel):
    """A single insight or recommendation."""
    insight: str = Field(
        ..., 
        description="The core insight or recommendation headline."
    )
    recommendation: Optional[str] = Field(
        None,
        description="Specific, actionable advice with implementation details including immediate actions, short-term goals, and long-term optimization strategies."
    )
    rationale: str = Field(
        ...,
        description="The supporting analysis and evidence for the insight, citing specific data points from the provided context. Include evidence level (A/B/C/D)."
    )
    data_summary: str = Field(
        ...,
        description="A summary of the specific data points from the 'Context from health data' that were used to form the insight."
    )
    implementation_protocol: Optional[str] = Field(
        None,
        description="Step-by-step implementation details including dosages, timing, and duration where applicable."
    )
    monitoring_plan: Optional[str] = Field(
        None,
        description="Biomarkers to track, timeline for reassessment, success metrics, and adjustment triggers."
    )
    safety_notes: Optional[str] = Field(
        None,
        description="Important safety considerations, contraindications, and when to consult healthcare providers."
    )
    importance: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="An assessment of how important this insight is for the user's health based on clinical impact."
    )
    confidence: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="Your confidence in the insight based on evidence quality (High=Level A/B evidence, Medium=Level C, Low=Level D)."
    )


class Insights(BaseModel):
    """A comprehensive response with executive summary and detailed insights."""
    executive_summary: Optional[str] = Field(
        None,
        description="A 2-3 sentence executive summary highlighting the most important insights and recommendations based on the context provided."
    )
    insights: List[Insight] = Field(
        ..., 
        description="A list of 1-5 detailed insights or recommendations organized by priority.",
        min_items=1,
        max_items=5
    )



# --- Search Strategy Models ---
class SearchCategory(BaseModel):
    """Represents a category-specific search plan with hybrid search optimization."""
    category: str = Field(
        ...,
        description="Search category (e.g., Genetics, Lab Work, Supplements, Lifestyle)"
    )
    keywords: List[str] = Field(
        ...,
        description="Specific technical terms for BM25 keyword search"
    )
    semantic_phrases: List[str] = Field(
        ...,
        description="Conceptual phrases for semantic vector search"
    )
    rationale: str = Field(
        ...,
        description="Explanation of why these search terms are important"
    )
    weight: float = Field(
        default=1.0,
        description="Importance weight for this category (0.0 to 2.0)",
        ge=0.0,
        le=2.0
    )

class SearchStrategy(BaseModel):
    """Enhanced search strategy for category-based hybrid retrieval."""
    search_plan: List[SearchCategory] = Field(
        ...,
        description="Category-specific search plans"
    )
    user_context: Optional[Dict[str, Any]] = Field(
        None,
        description="User-specific context for personalization"
    )
    confidence_score: float = Field(
        default=1.0,
        description="Confidence in the search strategy (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    query_intent: Optional[str] = Field(
        None,
        description="Interpreted intent of the user's query"
    )


class SearchStrategyResponse(BaseModel):
    """Wrapper for search strategy LLM response using structured output."""
    search_plan: List[SearchCategory] = Field(
        ...,
        description="Array of category-specific search strategies"
    )
    query_intent: Optional[str] = Field(
        None,
        description="Brief description of what the user wants to achieve"
    )
    confidence_score: float = Field(
        default=1.0,
        description="Confidence in the search strategy (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )


# NOTE: The following model is currently unused but preserved for potential future use
# class SearchQueries(BaseModel):
#     """Categorized search queries for different health aspects."""
#     queries_by_category: Dict[str, List[str]] = Field(
#         ...,
#         description="Dictionary mapping categories to lists of search queries"
#     )


# --- Processing Result Models ---
class DocumentBatch(BaseModel):
    """Batch of processed documents for structured output."""
    documents: List[Document] = Field(
        ..., 
        description="List of extracted documents from the text",
        min_items=1
    )


# NOTE: The following model is currently unused but preserved for potential future use
# class DocumentProcessingResult(BaseModel):
#     """Result of processing a document."""
#     success: bool = Field(..., description="Whether processing was successful")
#     documents: List[Document] = Field(
#         default_factory=list,
#         description="List of extracted documents"
#     )
#     error_message: Optional[str] = Field(
#         None,
#         description="Error message if processing failed"
#     )


# --- RAG Response Models ---
# NOTE: The following RAG-related models are currently unused but preserved for potential future use
# They were designed for structured RAG chain responses but the current implementation uses 
# direct LLM responses with the Insights model instead

# class CategoryInsight(BaseModel):
#     """Insights for a specific category."""
#     category_name: str = Field(..., description="Name of the category")
#     key_findings: List[str] = Field(
#         ..., 
#         description="Key findings from the context with citations",
#         min_items=1
#     )
#     recommendations: List[str] = Field(
#         ..., 
#         description="Specific, actionable recommendations with implementation details"
#     )
#     evidence_level: Literal["High", "Medium", "Low"] = Field(
#         ...,
#         description="Quality of evidence supporting this category's recommendations"
#     )
#     confidence: Literal["High", "Medium", "Low"] = Field(
#         ...,
#         description="Confidence in the recommendations for this category"
#     )
#
#
# class SafetyConsideration(BaseModel):
#     """Safety considerations and warnings."""
#     consideration: str = Field(..., description="The safety consideration or warning")
#     severity: Literal["Critical", "Important", "Minor"] = Field(
#         ...,
#         description="Severity level of this consideration"
#     )
#
#
# class ImplementationAction(BaseModel):
#     """An implementation action with details."""
#     action: str = Field(..., description="The action to take")
#     timeline: str = Field(..., description="When to implement this action")
#     details: Optional[str] = Field(None, description="Additional implementation details")
#
#
# class MonitoringPlan(BaseModel):
#     """Monitoring and adjustment plan."""
#     biomarkers_to_track: List[str] = Field(
#         ...,
#         description="Specific biomarkers with optimal ranges"
#     )
#     reassessment_timeline: str = Field(
#         ...,
#         description="When to reassess and retest"
#     )
#     success_metrics: List[str] = Field(
#         ...,
#         description="How to measure improvement"
#     )
#     adjustment_triggers: List[str] = Field(
#         ...,
#         description="Conditions that warrant adjusting the approach"
#     )
#
#
# class Citation(BaseModel):
#     """Evidence citation from context."""
#     claim: str = Field(..., description="The claim being made")
#     evidence: str = Field(..., description="Specific excerpt from context supporting the claim")
#     source_category: Optional[str] = Field(None, description="Category of the source document")
#
#
# class RAGResponse(BaseModel):
#     """Structured response from RAG chain."""
#     executive_summary: str = Field(
#         ...,
#         description="2-3 sentence summary of key insights and recommendations"
#     )
#     category_insights: List[CategoryInsight] = Field(
#         ...,
#         description="Category-based analysis aligned with search strategy"
#     )
#     safety_considerations: List[SafetyConsideration] = Field(
#         default_factory=list,
#         description="Safety warnings and contraindications"
#     )
#     immediate_actions: List[ImplementationAction] = Field(
#         ...,
#         description="Actions that can be started immediately"
#     )
#     short_term_goals: List[ImplementationAction] = Field(
#         ...,
#         description="Goals for the next 1-4 weeks"
#     )
#     long_term_optimization: List[ImplementationAction] = Field(
#         ...,
#         description="Strategic goals for 1-6 months"
#     )
#     monitoring_plan: MonitoringPlan = Field(
#         ...,
#         description="Plan for monitoring progress and adjusting approach"
#     )
#     citations: List[Citation] = Field(
#         ...,
#         description="Evidence citations supporting major claims"
#     )
#     overall_confidence: Literal["High", "Medium", "Low"] = Field(
#         ...,
#         description="Overall confidence in the recommendations"
#     )
#     limitations: Optional[List[str]] = Field(
#         None,
#         description="Any limitations or gaps in available information"
#     )