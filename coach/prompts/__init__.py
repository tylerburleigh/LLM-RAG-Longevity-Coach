"""Prompts package for the coach module.

This package contains all prompt templates organized by functionality.
"""

# Re-export commonly used prompts for backward compatibility
from coach.prompts.clarifying import CLARIFYING_QUESTIONS_PROMPT_TEMPLATE
from coach.prompts.insights import INSIGHTS_PROMPT_TEMPLATE
from coach.prompts.planning import PLANNING_PROMPT_TEMPLATE
from coach.prompts.search import SEARCH_QUERIES_PROMPT_TEMPLATE
from coach.prompts.document import DOCUMENT_STRUCTURE_PROMPT_TEMPLATE
from coach.prompts.guided_entry import GUIDED_ENTRY_PROMPT_TEMPLATE

__all__ = [
    "CLARIFYING_QUESTIONS_PROMPT_TEMPLATE",
    "INSIGHTS_PROMPT_TEMPLATE",
    "PLANNING_PROMPT_TEMPLATE",
    "SEARCH_QUERIES_PROMPT_TEMPLATE",
    "DOCUMENT_STRUCTURE_PROMPT_TEMPLATE",
    "GUIDED_ENTRY_PROMPT_TEMPLATE",
]