# coach/longevity_coach.py
from openai import OpenAI
import os
from typing import Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class LongevityCoach:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o")

    def plan_search(self, query: str) -> str:
        """Generate a search strategy based on the user's query."""
        planning_prompt = f"""Given the following user query, identify the key information we need to search for to provide a comprehensive answer.
        Break down the types of information needed and explain why each is relevant.

        User Query: {query}

        Output your search strategy, including:
        1. Key topics to search for
        2. Specific data points that would be valuable
        3. How this information will help answer the query
        """
        
        messages = [
            SystemMessage(content="You are a longevity expert helping to plan an information search strategy."),
            HumanMessage(content=planning_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content

    def retrieve_context(self, search_strategy: str) -> list[str]:
        """Retrieve relevant context based on the search strategy, searching different categories separately."""
        search_prompt = f"""Based on the following search strategy, generate separate search queries for each category relevant to longevity.
    Categories to consider: Genetics, Lab Work, Supplements.
    For each category, provide 1-3 specific search queries that target information in that category.
    Respond with ONLY a Python dictionary where keys are the category names and values are lists of search queries.
    Example:
    {{"Genetics": ["gene variant longevity", "genetic test interpretation"],
    "Lab Work": ["blood panel longevity", "inflammation lab tests"],
    "Supplements": ["vitamin D supplement effects", "antioxidant supplement longevity"]}}

    Search Strategy:
    {search_strategy}
        """

        messages = [
            SystemMessage(content="You are a search expert. Respond ONLY with a Python dictionary mapping categories to search queries."),
            HumanMessage(content=search_prompt)
        ]

        search_queries_response = self.llm.invoke(messages)
        content = search_queries_response.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("python"):
                content = content[6:]
        content = content.strip()

        try:
            search_queries_dict = eval(content)
            if not isinstance(search_queries_dict, dict):
                search_queries_dict = {"General": [search_strategy]}
        except Exception:
            search_queries_dict = {"General": [search_strategy]}

        all_docs = []
        # For each category, run each search query individually
        for category, queries in search_queries_dict.items():
            for query in queries:
                # Combine the category with the search query to hone the retrieval
                final_query = f"{category}: {query}"
                docs = self.vector_store.search(final_query, top_k=5)
                all_docs.extend(docs)

        # Remove duplicate documents by doc_id and return the text from each unique document
        seen_ids = set()
        unique_docs = []
        for doc in all_docs:
            if doc["doc_id"] not in seen_ids:
                seen_ids.add(doc["doc_id"])
                unique_docs.append(doc["text"])
        return unique_docs

    def generate_response_with_context(self, query: str, context: list[str]) -> str:
        """Generate a thorough response by synthesizing the retrieved context."""
        context_str = "\n\n".join(context)
        
        response_prompt = f"""
    Using the following context documents, generate a thorough answer to the user's query with the following requirements:
    - Reference and integrate insights from as many of the context documents as possible.
    - Do not suggest any lab tests or interventions that already appear in the context.
    - If you detect that the provided context is sparse or missing relevant details, indicate what additional documents or information would be helpful.
    - Where possible, synthesize the known information into clear and actionable advice.

    Context:
    {context_str}

    User Query:
    {query}
        """
        
        messages = [
            SystemMessage(content="You are a knowledgeable longevity coach who uses comprehensive context to deliver actionable advice."),
            HumanMessage(content=response_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content

    def generate_response(self, query: str, return_context: bool = False) -> Union[str, dict]:
        """Legacy method for backward compatibility."""
        search_strategy = self.plan_search(query)
        context = self.retrieve_context(search_strategy)
        response = self.generate_response_with_context(query, context)
        
        if return_context:
            return {
                "answer": response,
                "retrieved_docs": context,
                "search_strategy": search_strategy
            }
        return response