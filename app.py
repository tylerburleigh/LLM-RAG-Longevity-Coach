import streamlit as st
import json
import traceback
from coach.longevity_coach import LongevityCoach
from coach.utils import load_docs_from_jsonl, update_vector_store_from_docs
from coach.vector_store import PersistentVectorStore
from coach.document_processor import extract_text_from_pdf, create_structured_documents
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
DOCS_FILE = "docs.jsonl"
SESSION_STATE_MESSAGES = "messages"
SESSION_STATE_CONTEXT = "current_context"

# --- Page and Session State Setup ---
def setup_page():
    """Set up the Streamlit page configuration."""
    st.set_page_config(page_title="Longevity Coach", layout="wide")

def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if SESSION_STATE_MESSAGES not in st.session_state:
        st.session_state[SESSION_STATE_MESSAGES] = []
    if SESSION_STATE_CONTEXT not in st.session_state:
        st.session_state[SESSION_STATE_CONTEXT] = []

# --- Coach Initialization ---
@st.cache_resource
def initialize_coach():
    """Initialize the vector store and coach."""
    vector_store = PersistentVectorStore()
    
    if os.path.exists(DOCS_FILE):
        docs = load_docs_from_jsonl(DOCS_FILE)
        update_vector_store_from_docs(vector_store, docs)
        vector_store.save()
    else:
        logger.info(f"Docs file {DOCS_FILE} not found. Skipping update.")
    
    return LongevityCoach(vector_store)

# --- UI Components ---
def display_sidebar(coach):
    """Display the sidebar with a file uploader and processing logic."""
    with st.sidebar:
        st.header("Add New Documents")
        st.markdown("""
        Upload your lab reports or other health documents in PDF format. 
        The assistant will process them and add the information to its knowledge base.
        """)
        
        uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
        
        if st.button("Analyze and Add Document"):
            if uploaded_file is not None:
                with st.status("Processing document...", expanded=True) as status:
                    try:
                        status.write("📄 Extracting text from PDF...")
                        raw_text = extract_text_from_pdf(uploaded_file.getvalue())
                        
                        if not raw_text:
                            status.update(label="PDF processing failed.", state="error", expanded=True)
                            st.error("Could not extract text from the PDF. The file might be empty or corrupted.")
                            return

                        status.write("🤖 Structuring data with AI...")
                        structured_docs = create_structured_documents(raw_text, coach.llm)
                        logger.info(f"Structured documents from LLM: {structured_docs}")

                        if not structured_docs:
                            status.update(label="Data structuring failed.", state="error", expanded=True)
                            st.error("Failed to create any structured documents from the text. The content might be unsupported or empty.")
                            return
                        
                        valid_docs = []
                        malformed_count = 0
                        for doc in structured_docs:
                            if isinstance(doc, dict) and "doc_id" in doc and "text" in doc:
                                valid_docs.append(doc)
                            else:
                                malformed_count += 1
                        
                        if malformed_count > 0:
                            logger.warning(f"Discarded {malformed_count} malformed document objects from LLM output.")
                            st.warning(f"Could not process {malformed_count} entries from the document due to formatting issues.")

                        if not valid_docs:
                            status.update(label="No valid data found.", state="error", expanded=True)
                            st.error("The document could not be processed into any valid data entries.")
                            return

                        status.write(f"➕ Adding {len(valid_docs)} new document(s) to knowledge base...")
                        with open(DOCS_FILE, "a") as f:
                            for doc in valid_docs:
                                f.write(json.dumps(doc) + "\n")
                        
                        status.write("🔄 Reloading knowledge base...")
                        st.cache_resource.clear()
                        
                        status.update(label="Processing Complete!", state="complete", expanded=False)
                        st.success(f"Successfully processed and added {len(valid_docs)} new document(s).")
                        st.rerun()

                    except Exception as e:
                        logger.error(f"An error occurred during PDF processing: {e}")
                        # Also log the full traceback to the console
                        tb_str = traceback.format_exc()
                        logger.error(tb_str)
                        st.error(f"An error occurred during processing: {e}")
            else:
                st.warning("Please upload a PDF file first.")

def display_chat_history():
    """Display the chat history from the session state."""
    for message in st.session_state[SESSION_STATE_MESSAGES]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_new_conversation_button():
    """Handle the 'Start New Conversation' button click."""
    if st.button("Start New Conversation"):
        st.session_state[SESSION_STATE_CONTEXT] = []
        st.session_state[SESSION_STATE_MESSAGES] = []
        st.rerun()

def handle_chat_input(coach):
    """Handle the user's chat input and the conversation logic."""
    if prompt := st.chat_input("Ask your health and longevity questions..."):
        # Display user message and add to history
        st.session_state[SESSION_STATE_MESSAGES].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            if not st.session_state[SESSION_STATE_CONTEXT]:
                # First message in a conversation, perform full RAG
                response_container = st.empty()
                with st.status("Thinking...", expanded=True) as status:
                    status.write("🧠 Planning search strategy...")
                    search_strategy = coach.plan_search(prompt)
                    
                    status.write("🔎 Retrieving relevant documents...")
                    context = coach.retrieve_context(search_strategy)
                    
                    st.session_state[SESSION_STATE_CONTEXT] = context
                    
                    status.write("✍️ Synthesizing the final answer...")
                    response = coach.generate_response_with_context(prompt, context)
                    
                    # Show the thought process inside the collapsed status box
                    status.update(label="Coach's Thought Process", state="complete", expanded=False)
                    with status:
                        st.markdown("**Search Strategy:**")
                        st.text(search_strategy)
                        st.markdown("**Retrieved Context:**")
                        st.text("\n\n---\n\n".join(context))

                response_container.markdown(response)
            else:
                # Follow-up message
                response = coach.continue_chat(prompt, st.session_state[SESSION_STATE_CONTEXT])
                st.markdown(response)
            
        # Add assistant response to history
        st.session_state[SESSION_STATE_MESSAGES].append({"role": "assistant", "content": response})

# --- Main App ---
def main():
    """Main function to run the Streamlit app."""
    setup_page()
    initialize_session_state()
    
    st.title("🧬 Longevity Coach Chat")
    
    coach = initialize_coach()
    
    display_sidebar(coach)
    display_chat_history()
    handle_new_conversation_button()
    handle_chat_input(coach)

if __name__ == "__main__":
    main()