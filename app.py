import streamlit as st
from coach.longevity_coach import LongevityCoach
from coach.utils import load_docs_from_jsonl, update_vector_store_from_docs, initialize_coach
from coach.vector_store import PersistentVectorStore
import os
import logging

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DOCS_FILE = "docs.jsonl"

# --- Page and Session State ---
def setup_page():
    st.set_page_config(page_title="Longevity Coach", layout="wide")

def initialize_session_state():
    st.session_state.clear()
    st.session_state.app_state = "AWAITING_INITIAL_QUESTION"
    st.session_state.messages = []
    st.session_state.initial_query = ""
    st.session_state.clarifying_questions = []
    st.session_state.feedback = {}

# --- Coach Initialization ---
@st.cache_resource
def initialize_coach(model_name: str = "o3"):
    vector_store = PersistentVectorStore()
    if os.path.exists(DOCS_FILE):
        docs = load_docs_from_jsonl(DOCS_FILE)
        update_vector_store_from_docs(vector_store, docs)
        vector_store.save()
    else:
        logger.info(f"Docs file {DOCS_FILE} not found. Skipping update.")
    return LongevityCoach(vector_store, model_name=model_name)

# --- UI Components ---
def display_sidebar():
    with st.sidebar:
        st.header("Conversation Control")
        if st.button("Start New Conversation"):
            initialize_session_state()
            st.rerun()

def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            content = message["content"]
            # This is a bit of a hack to render raw HTML for insights
            if isinstance(content, dict) and "insights" in content:
                render_insights(content["insights"])
                if content.get("suggestions"):
                    render_fine_tune_suggestions(content["suggestions"])
            elif isinstance(content, list):  # Backwards compatibility for old format
                render_insights(content)
            else:
                st.markdown(str(content))

def render_insights(insights: list):
    # --- Define styles for visual presentation ---
    IMPORTANCE_EMOJI = {"High": "🔥", "Medium": "⭐", "Low": "⚪️"}
    CONFIDENCE_EMOJI = {"High": "✅", "Medium": "✔️", "Low": "❔"}
    
    st.markdown("### ✍️ Insights and Recommendations")
    st.info(
        "Here are some insights and recommendations based on your health data:"
    )

    for i, insight in enumerate(insights):
        with st.container(border=True):
            st.markdown(f"#### {insight.insight}")

            cols = st.columns(2)
            with cols[0]:
                st.markdown(
                    f"**Importance:** {IMPORTANCE_EMOJI.get(insight.importance, '')} {insight.importance}"
                )
            with cols[1]:
                st.markdown(
                    f"**Confidence:** {CONFIDENCE_EMOJI.get(insight.confidence, '')} {insight.confidence}"
                )
            
            st.divider()

            with st.expander("Show Rationale"):
                st.markdown("**Rationale:**")
                st.info(insight.rationale)
                st.markdown("**Supporting Data:**")
                st.info(insight.data_summary)

            feedback_cols = st.columns([1, 1, 8])
            feedback_state = st.session_state.feedback.get(i)

            with feedback_cols[0]:
                if st.button(
                    "👍",
                    key=f"thumb_up_{i}",
                    type="primary" if feedback_state == "up" else "secondary",
                ):
                    st.session_state.feedback[i] = "up" if feedback_state != "up" else None
                    st.rerun()
            with feedback_cols[1]:
                if st.button(
                    "👎",
                    key=f"thumb_down_{i}",
                    type="primary" if feedback_state == "down" else "secondary",
                ):
                    st.session_state.feedback[i] = "down" if feedback_state != "down" else None
                    st.rerun()

def render_fine_tune_suggestions(suggestions: list):
    """Renders the fine-tuning suggestions in the UI."""
    # --- Define styles for visual presentation ---
    IMPORTANCE_EMOJI = {"High": "🔥", "Medium": "⭐", "Low": "⚪️"}
    CONFIDENCE_EMOJI = {"High": "✅", "Medium": "✔️", "Low": "❔"}

    if suggestions:
        st.markdown("### 💡 Suggestions for Next Steps")
        st.info(
            "To further refine your health plan, you might consider collecting the following data:"
        )
        for suggestion in suggestions:
            with st.container(border=True):
                st.markdown(f"#### {suggestion.suggestion}")
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(
                        f"**Importance:** {IMPORTANCE_EMOJI.get(suggestion.importance, '')} {suggestion.importance}"
                    )
                with cols[1]:
                    st.markdown(
                        f"**Confidence:** {CONFIDENCE_EMOJI.get(suggestion.confidence, '')} {suggestion.confidence}"
                    )
                st.divider()
                with st.expander("View Rationale"):
                    st.markdown(suggestion.rationale)

def handle_chat_input(coach: LongevityCoach):
    if st.session_state.app_state != "CONVERSATION_ENDED":
        if prompt := st.chat_input("Ask a question or state your goal..."):
            st.session_state.messages.append({"role": "user", "content": prompt})

            if st.session_state.app_state == "AWAITING_INITIAL_QUESTION":
                st.session_state.initial_query = prompt
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing request..."):
                        questions = coach.generate_clarifying_questions(prompt)
                        st.session_state.clarifying_questions = questions
                        response_text = "I have some questions to better understand your needs:\n\n" + "\n".join(
                            f"- {q}" for q in questions
                        )
                        st.markdown(response_text)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response_text}
                )
                st.session_state.app_state = "AWAITING_ANSWERS"

            elif st.session_state.app_state == "AWAITING_ANSWERS":
                user_answers = prompt
                with st.chat_message("assistant"):
                    with st.status(
                        "Generating your personalized insights...", expanded=True
                    ) as status:

                        def progress_callback(message: str):
                            status.write(message)

                        insights, fine_tune_suggestions = coach.generate_insights(
                            initial_query=st.session_state.initial_query,
                            clarifying_questions=st.session_state.clarifying_questions,
                            user_answers_str=user_answers,
                            progress_callback=progress_callback,
                        )
                        status.update(
                            label="Insights Complete!", state="complete", expanded=False
                        )

                    render_insights(insights)
                    render_fine_tune_suggestions(fine_tune_suggestions)

                # Store insights and suggestions together in the chat history
                assistant_response = {
                    "insights": insights,
                    "suggestions": fine_tune_suggestions,
                }
                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_response}
                )
                # Transition to ended state
                st.session_state.app_state = "CONVERSATION_ENDED"
                st.session_state.initial_query = ""
                st.session_state.clarifying_questions = []

            st.rerun()
    else:
        st.info(
            "This conversation has concluded. To ask another question, please start a new conversation using the button in the sidebar."
        )

# --- Main App ---
def main():
    setup_page()
    st.title("🧬 Longevity Coach")
    
    model_name = st.selectbox(
        "Choose a model",
        ("o4-mini", "o3", "gemini-2.5-pro"),
        index=1,  # Default to 'o3'
    )
    
    # Initialize coach and session state
    coach = initialize_coach(model_name)
    if 'app_state' not in st.session_state:
        initialize_session_state()

    # Display UI
    display_sidebar()
    display_chat_history()
    handle_chat_input(coach)

if __name__ == "__main__":
    main()