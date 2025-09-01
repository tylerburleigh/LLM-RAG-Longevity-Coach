import streamlit as st
from coach.longevity_coach import LongevityCoach
from coach.utils import load_docs_from_jsonl, update_vector_store_from_docs, initialize_coach
from coach.vector_store_factory import get_vector_store
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
def initialize_coach(model_name: str = "o3", reasoning_effort: str = None):
    vector_store = get_vector_store()
    if os.path.exists(DOCS_FILE):
        docs = load_docs_from_jsonl(DOCS_FILE)
        update_vector_store_from_docs(vector_store, docs)
        vector_store.save()
    else:
        logger.info(f"Docs file {DOCS_FILE} not found. Skipping update.")
    return LongevityCoach(vector_store, model_name=model_name, reasoning_effort=reasoning_effort)

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
            elif isinstance(content, list):  # Backwards compatibility for old format
                render_insights(content)
            else:
                st.markdown(str(content))

def render_insights(insights_response):
    # --- Define styles for visual presentation ---
    IMPORTANCE_EMOJI = {"High": "🔥", "Medium": "⭐", "Low": "⚪️"}
    CONFIDENCE_EMOJI = {"High": "✅", "Medium": "✔️", "Low": "❔"}
    
    st.markdown("### ✍️ Insights and Recommendations")
    
    # Display executive summary if available
    if hasattr(insights_response, 'executive_summary') and insights_response.executive_summary:
        st.markdown("#### 📊 Executive Summary")
        st.info(insights_response.executive_summary)
        st.divider()
    
    # Handle both list and Insights object
    insights_list = insights_response.insights if hasattr(insights_response, 'insights') else insights_response
    
    st.info(
        "Here are detailed insights and recommendations based on your health data:"
    )

    for i, insight in enumerate(insights_list):
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
            
            # Display recommendation if available, otherwise use insight text
            if hasattr(insight, 'recommendation') and insight.recommendation:
                st.markdown("**Recommendation:**")
                st.write(insight.recommendation)
            else:
                # Fallback for insights without separate recommendation field
                st.markdown("**Details:**")
                st.write(insight.insight)
            
            # Display implementation protocol if available
            if hasattr(insight, 'implementation_protocol') and insight.implementation_protocol:
                st.markdown("**Implementation Protocol:**")
                st.write(insight.implementation_protocol)
            
            # Display monitoring plan if available
            if hasattr(insight, 'monitoring_plan') and insight.monitoring_plan:
                st.markdown("**Monitoring Plan:**")
                st.write(insight.monitoring_plan)
            
            # Display safety notes if available
            if hasattr(insight, 'safety_notes') and insight.safety_notes:
                st.markdown("**⚠️ Safety Considerations:**")
                st.warning(insight.safety_notes)

            with st.expander("Show Evidence & Rationale"):
                st.markdown("**Rationale & Evidence:**")
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
                        
                        # If no clarifying questions needed, go directly to insights
                        if not questions:
                            with st.status(
                                "Generating your personalized insights...", expanded=True
                            ) as status:
                                def progress_callback(message: str):
                                    status.write(message)
                                
                                insights = coach.generate_insights(
                                    initial_query=st.session_state.initial_query,
                                    clarifying_questions=[],
                                    user_answers_str="",
                                    progress_callback=progress_callback,
                                )
                                status.update(
                                    label="Insights Complete!", state="complete", expanded=False
                                )
                            
                            render_insights(insights)
                            
                            # Store insights in the chat history
                            assistant_response = {
                                "insights": insights,
                            }
                            st.session_state.messages.append(
                                {"role": "assistant", "content": assistant_response}
                            )
                            # Transition to ended state
                            st.session_state.app_state = "CONVERSATION_ENDED"
                            st.session_state.initial_query = ""
                            st.session_state.clarifying_questions = []
                        else:
                            # Questions needed - show them and wait for answers
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

                        insights = coach.generate_insights(
                            initial_query=st.session_state.initial_query,
                            clarifying_questions=st.session_state.clarifying_questions,
                            user_answers_str=user_answers,
                            progress_callback=progress_callback,
                        )
                        status.update(
                            label="Insights Complete!", state="complete", expanded=False
                        )

                    render_insights(insights)

                # Store insights in the chat history
                assistant_response = {
                    "insights": insights,
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
    
    # Create columns for model selection and reasoning effort
    col1, col2 = st.columns([1, 1])
    
    with col1:
        model_name = st.selectbox(
            "Choose a model",
            ("o4-mini", "gpt-5", "o3", "gemini-2.5-pro"),
            index=1,  # Default to 'gpt-5'
        )
    
    # Show reasoning effort selector for reasoning models
    reasoning_effort = None
    if model_name in ["gpt-5", "o3", "o4-mini"]:
        with col2:
            # GPT-5 supports minimal, others don't
            if model_name == "gpt-5":
                effort_options = ["minimal", "low", "medium", "high"]
                default_index = 3  # Default to 'high'
                help_text = "Higher effort = better quality but slower responses. Minimal = fastest with minimal reasoning (GPT-5 only)."
            else:
                effort_options = ["low", "medium", "high"]
                default_index = 2  # Default to 'high'
                help_text = "Higher effort = better quality but slower responses."
            
            reasoning_effort = st.selectbox(
                "Reasoning effort",
                effort_options,
                index=default_index,
                help=help_text
            )
    
    # Initialize coach and session state
    coach = initialize_coach(model_name, reasoning_effort)
    if 'app_state' not in st.session_state:
        initialize_session_state()

    # Display UI
    display_sidebar()
    display_chat_history()
    handle_chat_input(coach)

if __name__ == "__main__":
    main()