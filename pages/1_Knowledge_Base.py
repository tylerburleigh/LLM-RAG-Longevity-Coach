import streamlit as st
import pandas as pd
import json
import os
import shutil
import logging

from coach.auth import require_authentication
from coach.navigation import display_page_footer
from coach.page_setup import setup_authenticated_page

# --- Configuration ---
DOCS_FILE = "docs.jsonl"
VECTOR_STORE_PATH = "vector_store_data"
logger = logging.getLogger(__name__)

@require_authentication
def show_knowledge_base():
    """Protected function to show the knowledge base management page."""
    # Set up authenticated page with navigation
    user_context = setup_authenticated_page("Knowledge Base Management", "📚")
    if not user_context:
        return
    
    st.markdown(f"""
    **Welcome, {user_context.name}!**
    
    Here you can directly view, edit, add, or delete the documents that form your personal knowledge base. 
    When you're finished, click the 'Save and Re-index' button to apply your changes.
    """)
    
    # Show user data location
    st.info(f"💾 Your data is stored in: `{DOCS_FILE}` (User: {user_context.email})")
    
    # Run the main logic
    manage_knowledge_base()
    
    # Display footer
    display_page_footer()

def manage_knowledge_base():
    """Main knowledge base management logic."""
    
    # --- Main Page Logic ---
    if 'docs_df' not in st.session_state:
        st.session_state.docs_df = load_data()

    # Display the data editor
    edited_df = st.data_editor(
        st.session_state.docs_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "metadata": st.column_config.TextColumn(
                "Metadata (JSON)",
                help="Metadata must be a valid JSON string.",
            ),
            "text": st.column_config.TextColumn(
                "Document Text",
                width="large"
            )
        }
    )

    # Save and Re-index Button
    st.markdown("---")
    if st.button("💾 Save and Re-index Knowledge Base", type="primary"):
        with st.status("Saving changes and re-indexing...", expanded=True) as status:
            try:
                status.write("Saving data to disk...")
                st.session_state.docs_df = edited_df
                save_data(st.session_state.docs_df)
                status.write("Data saved successfully.")

                status.write("Purging old search index...")
                if os.path.exists(VECTOR_STORE_PATH):
                    shutil.rmtree(VECTOR_STORE_PATH)
                status.write("Old index purged.")
                
                status.write("Clearing app cache to force re-load...")
                st.cache_resource.clear()
                
                status.update(label="Re-indexing complete! The chat bot is now using the updated knowledge.", state="complete", expanded=True)
                st.success("Knowledge base updated! Navigate back to the main chat page to use it.")

            except Exception as e:
                status.update(label="An error occurred.", state="error", expanded=True)
                st.error(f"Failed to save and re-index: {e}")

# --- Helper Functions ---
def load_data():
    """Loads documents from the JSONL file into a DataFrame, skipping malformed lines."""
    docs = []
    if not os.path.exists(DOCS_FILE):
        return pd.DataFrame(columns=["doc_id", "text", "metadata"])
    
    with open(DOCS_FILE, "r") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                docs.append(json.loads(line))
            except json.JSONDecodeError as e:
                warning_msg = f"Skipping malformed JSON on line {i} in {DOCS_FILE}: {e}"
                logger.warning(warning_msg)
                st.warning(f"Could not load an entry from the knowledge base (line {i}) due to a formatting error. This line will be skipped. You can fix it here and save.")
    
    if not docs:
        return pd.DataFrame(columns=["doc_id", "text", "metadata"])
        
    return pd.DataFrame(docs)

def save_data(df):
    """Saves the DataFrame back to the JSONL file."""
    docs = df.to_dict('records')
    with open(DOCS_FILE, "w") as f:
        for doc in docs:
            # Ensure metadata is stored as a dictionary, not a string
            if isinstance(doc.get('metadata'), str):
                try:
                    doc['metadata'] = json.loads(doc['metadata'].replace("'", "\""))
                except json.JSONDecodeError:
                    st.warning(f"Could not parse metadata for doc_id {doc.get('doc_id')}. Saving as raw string.")
            f.write(json.dumps(doc) + "\n")


# --- Main execution ---
if __name__ == "__main__":
    show_knowledge_base() 