# coach/longevity_coach.py
from typing import Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from coach.search import plan_search, retrieve_context
from coach.prompts import RESPONSE_PROMPT_TEMPLATE

class LongevityCoach:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        # IMPORTANT: still use the "o1-mini" model, just remove system role usage
        self.llm = ChatOpenAI(temperature=1, model="o4-mini")

    def plan_search(self, query: str) -> str:
        """Generate a search strategy based on the user's query."""
        return plan_search(query, self.llm)

    def retrieve_context(self, search_strategy: str) -> list[str]:
        """Retrieve relevant context based on the search strategy."""
        return retrieve_context(search_strategy, self.llm, self.vector_store)

    def generate_response_with_context(self, query: str, context: list[str]) -> str:
        """Generate a thorough response by synthesizing the retrieved context."""
        context_str = "\n\n".join(context)

        response_prompt = RESPONSE_PROMPT_TEMPLATE.format(
            context_str=context_str, 
            query=query
        )

        messages = [
            HumanMessage(content=response_prompt)
        ]
        
        response = self.llm.invoke(messages)
        return response.content

    def continue_chat(self, query: str, previous_context: list[str]) -> str:
        """Continue the conversation using the previously retrieved context."""
        return self.generate_response_with_context(query, previous_context)

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