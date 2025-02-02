import streamlit as st
from coach.longevity_coach import LongevityCoach
from coach.utils import load_docs_from_jsonl, update_vector_store_from_docs
from coach.vector_store import PersistentVectorStore
import os

# Initialize the page config
st.set_page_config(page_title="Longevity Coach Chat", layout="wide")

# Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

@st.cache_resource
def initialize_coach():
    """Initialize the vector store and coach (cached to prevent reloading)"""
    # Initialize or load the persistent vector store
    vector_store = PersistentVectorStore()
    
    # Update the vector store from the docs.jsonl file, if it exists
    docs_file = "docs.jsonl"
    if os.path.exists(docs_file):
        docs = load_docs_from_jsonl(docs_file)
        update_vector_store_from_docs(vector_store, docs)
        vector_store.save()
    else:
        print(f"Docs file {docs_file} not found. Skipping update.")
    
    return LongevityCoach(vector_store)

def main():
    st.title("🧬 Longevity Coach Chat")
    
    # Initialize the coach
    coach = initialize_coach()
    
    # Display chat messages from history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask your health and longevity questions..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display assistant response with intermediate steps
        with st.chat_message("assistant"):
            # Create three columns for the intermediate steps
            with st.expander("View Coach's Thought Process", expanded=False):
                # Get and display search strategy
                search_strategy = coach.plan_search(prompt)
                st.markdown("### Search Strategy")
                st.markdown(search_strategy)
                
                # Get and display context
                context = coach.retrieve_context(search_strategy)
                st.markdown("### Retrieved Context")
                st.markdown("\n\n".join(context))
            
            # Generate and display final response
            response = coach.generate_response_with_context(prompt, context)
            st.markdown(response)
            
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()