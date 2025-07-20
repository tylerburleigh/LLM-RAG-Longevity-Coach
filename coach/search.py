# coach/search.py
import json
import logging
from typing import Dict, List
from langchain_core.messages import HumanMessage

from coach.prompts import PLANNING_PROMPT_TEMPLATE, SEARCH_QUERIES_PROMPT_TEMPLATE
from coach.types import Query, SearchQueryDict
from coach.exceptions import (
    SearchStrategyException,
    QueryGenerationException,
    RetrievalException,
)
from coach.config import config
from coach.retrievers import create_advanced_retriever
from coach.llm_providers import get_embeddings

logger = logging.getLogger(__name__)

def plan_search(query: Query, llm) -> str:
    """
    Generate a search strategy based on the user's query.
    
    Args:
        query: The user's input query.
        llm: The language model instance to use for planning.

    Returns:
        A string containing the search strategy.
        
    Raises:
        SearchStrategyException: If search planning fails.
    """
    try:
        prompt = PLANNING_PROMPT_TEMPLATE.format(query=query)
        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        return response.content
    except Exception as e:
        raise SearchStrategyException(f"Failed to plan search strategy: {str(e)}") from e

def _generate_search_queries(search_strategy: str, llm) -> SearchQueryDict:
    """
    Generates structured search queries from a search strategy using an LLM.

    Args:
        search_strategy: The search strategy planned by the LLM.
        llm: The language model instance.

    Returns:
        A dictionary mapping search categories to a list of queries.
        
    Raises:
        QueryGenerationException: If query generation fails.
    """
    try:
        prompt = SEARCH_QUERIES_PROMPT_TEMPLATE.format(search_strategy=search_strategy)
        messages = [HumanMessage(content=prompt)]
        
        response = llm.invoke(messages)
        content = response.content.strip()

        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        try:
            search_queries_dict = json.loads(content)
            if not isinstance(search_queries_dict, dict):
                return {"General": [search_strategy]}
            return search_queries_dict
        except json.JSONDecodeError:
            logger.warning("Failed to parse search queries JSON, using fallback")
            return {"General": [search_strategy]}
    except Exception as e:
        raise QueryGenerationException(f"Failed to generate search queries: {str(e)}") from e

def retrieve_context(
    search_strategy: str,
    llm,
    vector_store,
    retrieval_strategy: str = "ensemble",
    use_multi_strategy: bool = False,
    **kwargs
) -> List[str]:
    """
    Retrieve context using advanced retrieval strategies.
    
    Args:
        search_strategy: The search strategy planned by the LLM
        llm: The language model instance
        vector_store: The vector store instance
        retrieval_strategy: Advanced retrieval strategy to use
        use_multi_strategy: Whether to use multiple strategies
        **kwargs: Additional parameters for advanced retrieval
        
    Returns:
        A list of unique document texts
        
    Raises:
        RetrievalException: If document retrieval fails
    """
    try:
        # Create advanced retriever
        embedding_model = get_embeddings()
        
        advanced_retriever = create_advanced_retriever(
            vector_store=vector_store,
            llm=llm,
            embedding_model=embedding_model,
            **kwargs
        )
        
        # Generate search queries
        search_queries_dict = _generate_search_queries(search_strategy, llm)
        
        all_docs = []
        for category, queries in search_queries_dict.items():
            for query in queries:
                final_query = f"{category}: {query}"
                
                if use_multi_strategy:
                    # Use multiple strategies
                    strategies = ["ensemble", "multi_query", "compressed"]
                    docs = advanced_retriever.multi_strategy_retrieve(
                        final_query,
                        strategies=strategies,
                        top_k=config.DEFAULT_TOP_K,
                        merge_method="rank_fusion"
                    )
                else:
                    # Use single strategy
                    docs = advanced_retriever.retrieve(
                        final_query,
                        strategy=retrieval_strategy,
                        top_k=config.DEFAULT_TOP_K
                    )
                
                all_docs.extend(docs)
        
        # De-duplicate documents based on 'doc_id' while preserving order
        unique_docs = []
        seen_ids = set()
        for doc in all_docs:
            if doc['doc_id'] not in seen_ids:
                seen_ids.add(doc['doc_id'])
                unique_docs.append(doc['text'])
        
        logger.info(f"Advanced retrieval returned {len(unique_docs)} unique documents")
        return unique_docs
        
    except Exception as e:
        logger.error(f"Advanced retrieval failed: {e}")
        raise RetrievalException(f"Failed to retrieve context: {str(e)}") from e


# Alias for backward compatibility
advanced_retrieve_context = retrieve_context 