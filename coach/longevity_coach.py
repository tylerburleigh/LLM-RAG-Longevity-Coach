# coach/longevity_coach.py
from typing import List, Callable, Optional, Dict, Any, Tuple
from langchain_core.messages import HumanMessage

from coach.search import plan_search, retrieve_context
from coach.models import (
    ClarifyingQuestions,
    Insight,
    Insights,
    FineTuneSuggestion,
    FineTuneSuggestions,
)
from coach.prompts import (
    CLARIFYING_QUESTIONS_PROMPT_TEMPLATE,
    INSIGHTS_PROMPT_TEMPLATE,
    FINE_TUNE_PROMPT_TEMPLATE,
)
from coach.llm_providers import get_llm
from coach.types import ProgressCallback
from coach.config import config




class LongevityCoach:
    def __init__(self, vector_store, model_name: Optional[str] = None):
        self.vector_store = vector_store
        self.model_name = model_name or config.DEFAULT_LLM_MODEL
        self.llm = get_llm(self.model_name)

        self.insights_llm = self.llm.bind_tools([Insights], tool_choice="Insights")
        self.clarifying_questions_llm = self.llm.bind_tools(
            [ClarifyingQuestions],
            tool_choice="ClarifyingQuestions",
        )
        self.fine_tune_llm = self.llm.bind_tools(
            [FineTuneSuggestions], tool_choice="FineTuneSuggestions"
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

    def generate_fine_tune_suggestions(
        self,
        initial_query: str,
        clarifying_questions: List[str],
        user_answers_str: str,
        context_str: str,
        insights: List[Dict[str, Any]],
    ) -> List[FineTuneSuggestion]:
        """Generate suggestions for fine-tuning the health plan."""
        questions_str = "\n".join(f"- {q}" for q in clarifying_questions)
        insights_str = "\n\n".join(
            f"Insight: {i['insight']}\nRationale: {i['rationale']}" for i in insights
        )

        prompt = FINE_TUNE_PROMPT_TEMPLATE.format(
            context_str=context_str,
            initial_query=initial_query,
            clarifying_questions=questions_str,
            user_answers_str=user_answers_str,
            insights=insights_str,
        )

        messages = [HumanMessage(content=prompt)]
        response = self.fine_tune_llm.invoke(messages)

        if not response.tool_calls:
            return []
        tool_args = response.tool_calls[0]["args"]
        suggestions_obj = FineTuneSuggestions.model_validate(tool_args)
        return suggestions_obj.suggestions

    def generate_insights(
        self,
        initial_query: str,
        clarifying_questions: List[str],
        user_answers_str: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Tuple[List[Insight], List[FineTuneSuggestion]]:
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
            return [], []
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
        insights_list = [i.model_dump() for i in insights_obj.insights]

        if progress_callback:
            progress_callback("💡 Generating ideas for other data to collect...")

        fine_tune_suggestions = self.generate_fine_tune_suggestions(
            initial_query,
            clarifying_questions,
            user_answers_str,
            context_str,
            insights_list,
        )

        return insights_obj.insights, fine_tune_suggestions