"""RAG (Retrieval-Augmented Generation) prompt templates."""

COMPLETE_RAG_PROMPT_TEMPLATE = """
Based on the following context and user query, provide comprehensive insights and recommendations for longevity and health optimization.

Context: {context}
User Query: {query}

Please provide:
1. Key insights based on the context
2. Specific recommendations
3. Any important considerations or warnings

Response:
"""