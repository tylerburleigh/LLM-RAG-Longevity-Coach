import streamlit as st
import json
import os
import shutil
from langchain_core.messages import HumanMessage, AIMessage
from coach.prompts import GUIDED_ENTRY_PROMPT_TEMPLATE
from coach.longevity_coach import LongevityCoach

# --- Configuration ---
DOCS_FILE = "docs.jsonl"
VECTOR_STORE_PATH = "vector_store_data"

# --- Page Setup ---
st.set_page_config(page_title="Add Data via Chat", layout="wide")
st.title("🗣️ Add Data via Chat")
st.markdown("Describe the information you'd like to add, and the AI assistant will help structure it for the knowledge base.")

# --- Helper Functions ---
@st.cache_resource
def get_llm():
    """Initializes and returns the LLM from the LongevityCoach."""
    # This is a simplified way to get an LLM instance without a vector store
    # In a real app, you might have a dedicated LLM provider module.
    return LongevityCoach(vector_store=None).llm

def generate_structured_entry(history, user_input, llm):
    """Generates a structured JSON entry from a user's description."""
    history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in history])
    prompt = GUIDED_ENTRY_PROMPT_TEMPLATE.format(history=history_str, user_input=user_input)
    
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    try:
        # Clean the content and load as JSON
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except (json.JSONDecodeError, IndexError) as e:
        st.error(f"The AI failed to generate a valid JSON structure. Please try rephrasing your request. Error: {e}")
        return None

# --- Main Page Logic ---
llm = get_llm()

# Initialize session state
if "guided_messages" not in st.session_state:
    st.session_state.guided_messages = [AIMessage(content="What information would you like to add to the knowledge base?")]
if "proposed_entry" not in st.session_state:
    st.session_state.proposed_entry = None

# Display chat history
for msg in st.session_state.guided_messages:
    st.chat_message(msg.type).write(msg.content)

# Display proposed entry and confirmation buttons
if st.session_state.proposed_entry:
    with st.container(border=True):
        st.subheader("Proposed Knowledge Base Entry")
        st.text(f"Document ID: {st.session_state.proposed_entry.get('doc_id')}")
        st.text_area("Document Text", value=st.session_state.proposed_entry.get('text', ''), height=150)
        st.json(st.session_state.proposed_entry.get('metadata', {}))

        col1, col2, col3 = st.columns([1,1,5])
        with col1:
            if st.button("✅ Looks Good, Save It!", type="primary"):
                with st.status("Saving and re-indexing...", expanded=True) as status:
                    status.write("Appending to knowledge base file...")
                    with open(DOCS_FILE, "a") as f:
                        f.write(json.dumps(st.session_state.proposed_entry) + "\n")
                    
                    status.write("Purging old search index...")
                    if os.path.exists(VECTOR_STORE_PATH):
                        shutil.rmtree(VECTOR_STORE_PATH)

                    status.write("Clearing app cache to force re-load...")
                    st.cache_resource.clear()
                    
                    status.update(label="Save Complete!", state="complete")

                st.success("Entry saved successfully! The knowledge base is now updated.")
                st.session_state.proposed_entry = None
                st.session_state.guided_messages.append(AIMessage(content="Great! What else can I help you add?"))
                st.rerun()

        with col2:
            if st.button("❌ No, start over"):
                st.session_state.proposed_entry = None
                st.session_state.guided_messages.append(AIMessage(content="Okay, let's scrap that. What would you like to add instead?"))
                st.rerun()


# Handle user input
if prompt := st.chat_input("Describe the data or provide feedback..."):
    st.session_state.guided_messages.append(HumanMessage(content=prompt))
    st.chat_message("human").write(prompt)

    with st.spinner("Thinking..."):
        entry = generate_structured_entry(st.session_state.guided_messages, prompt, llm)
    
    if entry:
        st.session_state.proposed_entry = entry
        st.rerun()
    else:
        st.session_state.guided_messages.append(AIMessage(content="I had trouble creating a valid entry. Could you try describing it differently?"))
        st.rerun() 