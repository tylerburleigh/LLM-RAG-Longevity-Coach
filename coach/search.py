# coach/search.py
import json
from typing import Dict, List
from langchain_core.messages import HumanMessage
from coach.prompts import PLANNING_PROMPT_TEMPLATE, SEARCH_QUERIES_PROMPT_TEMPLATE

def plan_search(query: str, llm) -> str:
    """
    Generate a search strategy based on the user's query.
    
    Args:
        query: The user's input query.
        llm: The language model instance to use for planning.

    Returns:
        A string containing the search strategy.
    """
    prompt = PLANNING_PROMPT_TEMPLATE.format(query=query)
    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    return response.content

def _generate_search_queries(search_strategy: str, llm) -> Dict[str, List[str]]:
    """
    Generates structured search queries from a search strategy using an LLM.

    Args:
        search_strategy: The search strategy planned by the LLM.
        llm: The language model instance.

    Returns:
        A dictionary mapping search categories to a list of queries.
    """
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
        return {"General": [search_strategy]}

def retrieve_context(search_strategy: str, llm, vector_store) -> list[str]:
    """
    Retrieve relevant context based on the search strategy.
    
    This function now uses the hybrid search capabilities of the vector store.

    Args:
        search_strategy: The search strategy planned by the LLM.
        llm: The language model instance.
        vector_store: The vector store instance with a .search() method.

    Returns:
        A list of unique document texts.
    """
    search_queries_dict = _generate_search_queries(search_strategy, llm)

    all_docs = []
    for category, queries in search_queries_dict.items():
        for query in queries:
            final_query = f"{category}: {query}"
            # This now calls the new hybrid search method in the vector store
            docs = vector_store.search(final_query, top_k=5)
            all_docs.extend(docs)

    # De-duplicate documents based on 'doc_id' while preserving order
    unique_docs = []
    seen_ids = set()
    for doc in all_docs:
        if doc['doc_id'] not in seen_ids:
            seen_ids.add(doc['doc_id'])
            unique_docs.append(doc['text'])
            
    return unique_docs 