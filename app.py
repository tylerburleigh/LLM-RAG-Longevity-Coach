import streamlit as st
from coach.longevity_coach import LongevityCoach
from coach.tenant import TenantManager
from coach.auth import AuthenticationManager, AuthenticationException, require_authentication
from coach.models import UserContext
from coach.navigation import display_user_context_sidebar, display_page_header, display_page_footer
from coach.page_setup import setup_main_page
import os
import logging

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Page and Session State ---
def setup_page():
    setup_main_page()

def initialize_session_state():
    """Initialize session state for the longevity coach application.
    
    Note: This preserves authentication-related session state while clearing
    conversation state.
    """
    # Preserve authentication state and coach instances
    auth_keys = ['user_context', 'session_created']
    preserved_state = {}
    
    # Preserve authentication
    for key in auth_keys:
        if key in st.session_state:
            preserved_state[key] = st.session_state[key]
    
    # Preserve coach instances (they start with 'coach_')
    coach_keys = [key for key in st.session_state.keys() if key.startswith('coach_')]
    for key in coach_keys:
        preserved_state[key] = st.session_state[key]
    
    # Clear all session state
    st.session_state.clear()
    
    # Restore preserved state
    for key, value in preserved_state.items():
        st.session_state[key] = value
    
    # Initialize conversation state
    st.session_state.app_state = "AWAITING_INITIAL_QUESTION"
    st.session_state.messages = []
    st.session_state.initial_query = ""
    st.session_state.clarifying_questions = []
    st.session_state.feedback = {}

def cleanup_user_coaches(user_id: str):
    """Clean up all coach instances for a specific user."""
    coach_keys = [key for key in st.session_state.keys() 
                  if key.startswith(f'coach_{user_id}_')]
    for key in coach_keys:
        del st.session_state[key]
        logger.info(f"Cleaned up coach instance: {key}")

# --- Coach Initialization ---
def get_tenant_coach(user_context: UserContext, model_name: str = "o3") -> LongevityCoach:
    """Get or create a tenant-specific coach instance for the user."""
    # Create a unique key for this user's coach instance
    coach_key = f"coach_{user_context.user_id}_{model_name}"
    
    # Check if coach already exists in session state
    if coach_key in st.session_state:
        return st.session_state[coach_key]
    
    # Create tenant manager
    tenant_manager = TenantManager(user_context)
    
    # Import here to avoid circular imports
    from coach.vector_store_factory import get_vector_store_for_tenant
    
    # Get tenant-specific vector store
    vector_store = get_vector_store_for_tenant(tenant_manager)
    
    # Load tenant-specific documents
    docs_path = tenant_manager.get_documents_path()
    if os.path.exists(docs_path):
        from coach.utils import load_tenant_docs_from_jsonl
        docs = load_tenant_docs_from_jsonl(tenant_manager)
        if docs:
            vector_store.add_documents(docs)
        vector_store.save()
    else:
        logger.info(f"Tenant docs file {docs_path} not found. Skipping update.")
    
    # Create coach with tenant-specific vector store and model
    coach = LongevityCoach(vector_store, model_name=model_name)
    
    # Store in session state for reuse
    st.session_state[coach_key] = coach
    
    logger.info(f"Initialized coach for tenant {user_context.user_id} with model {model_name}")
    return coach

# --- Authentication UI Components ---
def show_login_page():
    """Display the login page when user is not authenticated."""
    st.title("🧬 Longevity Coach")
    st.markdown("---")
    
    # Welcome message
    st.markdown("""
    ## Welcome to Longevity Coach
    
    Your personalized AI-powered health and longevity advisor. Get insights and recommendations 
    based on your health data and goals.
    
    ### Features:
    - 🎯 **Personalized Insights**: Get tailored recommendations based on your health profile
    - 📊 **Data-Driven Advice**: Leveraging scientific research and your personal data
    - 🔒 **Secure & Private**: Your data is encrypted and protected
    - 💬 **Interactive Chat**: Ask questions and get detailed explanations
    
    ### Get Started:
    Please log in with your Google account to begin your personalized longevity journey.
    """)
    
    # Login section
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Login Required")
        st.info("Please authenticate to access your personalized longevity coaching session.")
        
        # The authenticate_user method will handle the OAuth flow
        # and display the login button when needed
        try:
            auth_manager = AuthenticationManager()
            result = auth_manager.authenticate_user()
            
            # If authentication is not configured, show development mode
            if result is None and not auth_manager.oauth_config:
                st.warning("⚠️ Authentication is not configured.")
                st.info("""
                **Development Mode Detected**
                
                To enable authentication, please configure the following environment variables:
                - `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
                - `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
                - `OAUTH_REDIRECT_URI`: OAuth redirect URI (default: http://localhost:8501/)
                
                For development purposes, you can continue without authentication, but user-specific features will be limited.
                """)
                
                if st.button("Continue without Authentication", type="primary"):
                    # Create a temporary user context for development
                    from datetime import datetime
                    temp_user = UserContext(
                        user_id="dev_user",
                        email="developer@localhost",
                        name="Developer",
                        oauth_token="dev_token",
                        refresh_token="dev_refresh",
                        encryption_key=None
                    )
                    
                    # Store in session
                    st.session_state['user_context'] = {
                        'user_id': temp_user.user_id,
                        'email': temp_user.email,
                        'name': temp_user.name,
                        'oauth_token': temp_user.oauth_token,
                        'refresh_token': temp_user.refresh_token,
                        'encryption_key': temp_user.encryption_key
                    }
                    st.session_state['session_created'] = datetime.now()
                    st.rerun()
                    
        except AuthenticationException as e:
            st.error(f"Authentication error: {str(e)}")
            st.info("Please check your configuration and try again.")
            
            # Show configuration help
            with st.expander("Configuration Help"):
                st.markdown("""
                **Required Environment Variables:**
                - `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
                - `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
                - `OAUTH_REDIRECT_URI`: OAuth redirect URI (default: http://localhost:8501/)
                
                **How to set up Google OAuth:**
                1. Go to [Google Cloud Console](https://console.cloud.google.com/)
                2. Create a new project or select an existing one
                3. Enable the Google+ API
                4. Create OAuth 2.0 credentials
                5. Add your redirect URI to the authorized redirect URIs
                6. Set the environment variables with your credentials
                """)
                
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            st.error("An unexpected error occurred during authentication. Please try again.")

def display_user_info(user_context: UserContext):
    """Display user information in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 👤 User Info")
        st.markdown(f"**Name:** {user_context.name}")
        st.markdown(f"**Email:** {user_context.email}")
        
        # Show development mode indicator
        if user_context.name == "Developer":
            st.info("🔧 Development Mode")
        
        # Logout button
        logout_text = "🚪 Exit Dev Mode" if user_context.name == "Developer" else "🚪 Logout"
        if st.button(logout_text, type="secondary"):
            try:
                # Clean up user's coach instances before logout
                cleanup_user_coaches(user_context.user_id)
                
                auth_manager = AuthenticationManager()
                auth_manager.logout()
            except AuthenticationException as e:
                st.error(f"Logout error: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected logout error: {e}")
                st.error("An unexpected error occurred during logout.")

# --- UI Components ---
def display_sidebar(user_context: UserContext = None):
    # Use the new navigation system (includes conversation control)
    display_user_context_sidebar()

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
    
    # Initialize authentication
    auth_manager = AuthenticationManager()
    
    # Handle OAuth callback if present
    if 'code' in st.query_params:
        try:
            # The authenticate_user method will handle the callback
            user_context = auth_manager.authenticate_user()
            if user_context:
                st.success(f"Welcome {user_context.name}! You have been successfully authenticated.")
                st.info("Redirecting to the main application...")
                # Clear the URL parameters and redirect
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Authentication failed. Please try again.")
                st.query_params.clear()
                st.rerun()
        except AuthenticationException as e:
            st.error(f"Authentication error: {str(e)}")
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            st.error("An unexpected error occurred during authentication.")
            st.query_params.clear()
            st.rerun()
    
    # Get current user context
    user_context = auth_manager.get_user_context()
    
    # Check if user is authenticated
    if not user_context:
        show_login_page()
        return
    
    # User is authenticated, continue with main app
    st.title("🧬 Longevity Coach")
    
    # Mark that we're on the main page for navigation
    st.session_state['current_page'] = 'main'
    
    # Show a welcome message with user's name
    if user_context.name != "Developer":  # Don't show welcome for dev mode
        st.markdown(f"Welcome back, **{user_context.name}**! 👋")
        st.markdown("*Get personalized longevity insights based on your health data*")
    else:
        st.warning("⚠️ Running in development mode - authentication is disabled")
    
    model_name = st.selectbox(
        "Choose a model",
        ("o4-mini", "o3", "gemini-2.5-pro"),
        index=1,  # Default to 'o3'
    )
    
    # Initialize coach and session state
    try:
        # Get tenant-specific coach instance
        coach = get_tenant_coach(user_context, model_name)
        
        if 'app_state' not in st.session_state:
            initialize_session_state()

        # Show user data info
        st.info(f"💾 Your data is stored securely and privately in your personal workspace")
        
        # Display UI with user context
        display_sidebar(user_context)
        display_chat_history()
        handle_chat_input(coach)
        
        # Display footer
        display_page_footer()
        
    except Exception as e:
        logger.error(f"Error initializing coach: {e}")
        st.error("An error occurred while initializing the coach. Please try refreshing the page.")
        st.info("If the problem persists, please contact support.")
        
        # Still show sidebar for logout option
        display_sidebar(user_context)

if __name__ == "__main__":
    main()