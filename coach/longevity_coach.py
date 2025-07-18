# coach/longevity_coach.py
from typing import List, Callable, Optional, Dict, Any, Tuple
from langchain_core.messages import HumanMessage

from coach.search import plan_search, retrieve_context
from coach.models import (
    ClarifyingQuestions,
    Insight,
    Insights,
)
from coach.prompts import (
    CLARIFYING_QUESTIONS_PROMPT_TEMPLATE,
    INSIGHTS_PROMPT_TEMPLATE,
)
from coach.llm_providers import get_llm
from coach.types import ProgressCallback
from coach.config import config

# Try to import chains if available
try:
    from coach.chains import LongevityCoachChains, create_rag_workflow
    CHAINS_AVAILABLE = True
except ImportError:
    CHAINS_AVAILABLE = False




class LongevityCoach:
    def __init__(self, vector_store, model_name: Optional[str] = None, use_chains: Optional[bool] = None):
        self.vector_store = vector_store
        self.model_name = model_name or config.DEFAULT_LLM_MODEL
        self.llm = get_llm(self.model_name)
        
        # Initialize chains if enabled and available
        self.use_chains = use_chains if use_chains is not None else config.USE_LANGCHAIN_CHAINS
        self.chains = None
        self.rag_workflow = None
        
        if self.use_chains and CHAINS_AVAILABLE:
            try:
                self.chains = LongevityCoachChains(self.llm)
                self.rag_workflow = create_rag_workflow(self.llm, self.vector_store)
            except Exception as e:
                print(f"Warning: Could not initialize chains: {e}")
                self.use_chains = False

        self.insights_llm = self.llm.bind_tools([Insights], tool_choice="Insights")
        self.clarifying_questions_llm = self.llm.bind_tools(
            [ClarifyingQuestions],
            tool_choice="ClarifyingQuestions",
        )

    def generate_clarifying_questions(self, query: str) -> List[str]:
        """Generate clarifying questions based on the user's query."""
        prompt = CLARIFYING_QUESTIONS_PROMPT_TEMPLATE.format(query=query)
        messages = [HumanMessage(content=prompt)]
        response = self.clarifying_questions_llm.invoke(messages)
        if not response.tool_calls:
            return []
        tool_args = response.tool_calls[0]["args"]
        questions_obj = ClarifyingQuestions.model_validate(tool_args)
        return questions_obj.questions


    def generate_insights(
        self,
        initial_query: str,
        clarifying_questions: List[str],
        user_answers_str: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[Insight]:
        """Generate insights based on the user's query and answers."""
        if progress_callback:
            progress_callback("🧠 Planning search strategy...")
        search_strategy = plan_search(initial_query, self.llm)

        if progress_callback:
            progress_callback("🔎 Retrieving relevant documents...")
        context = retrieve_context(search_strategy, self.llm, self.vector_store)
        context_str = "\n\n".join(context)

        # Format questions for the prompt
        questions_str = "\n".join(f"- {q}" for q in clarifying_questions)

        prompt = INSIGHTS_PROMPT_TEMPLATE.format(
            context_str=context_str,
            initial_query=initial_query,
            clarifying_questions=questions_str,
            user_answers_str=user_answers_str,
        )

        if progress_callback:
            progress_callback("✍️ Generating insights and recommendations...")
        messages = [HumanMessage(content=prompt)]
        response = self.insights_llm.invoke(messages)

        if not response.tool_calls:
            return []
        tool_args = response.tool_calls[0]["args"]
        insights_obj = Insights.model_validate(tool_args)

        # Sort by importance, then confidence (both descending)
        importance_map = {"High": 2, "Medium": 1, "Low": 0}
        insights_obj.insights.sort(
            key=lambda x: (
                importance_map.get(x.importance, -1),
                importance_map.get(x.confidence, -1),
            ),
            reverse=True,
        )

        return insights_obj.insights