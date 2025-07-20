import streamlit as st
import json
import traceback
import logging
from coach.document_processor import (
    extract_text_from_pdf,
    create_structured_documents,
)
from coach.utils import initialize_coach
from coach.auth import require_authentication
from coach.navigation import display_page_footer
from coach.page_setup import setup_authenticated_page

# --- Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DOCS_FILE = "docs.jsonl"


@require_authentication
def show_upload_documents():
    """Protected function to show the document upload page."""
    # Set up authenticated page with navigation
    user_context = setup_authenticated_page("Upload Documents", "📄")
    if not user_context:
        return
    
    st.markdown(f"""
    **Welcome, {user_context.name}!**
    
    Upload your lab reports or other health documents in PDF format. 
    The assistant will process them and add the information to your personal knowledge base.
    This will make the chat assistant's insights more personalized and relevant.
    """)
    
    # Show user data location
    st.info(f"💾 Documents will be added to: `{DOCS_FILE}` (User: {user_context.email})")
    
    # Run the main logic
    upload_documents_interface()
    
    # Display footer
    display_page_footer()


def upload_documents_interface():
    """Main document upload interface."""
    coach = initialize_coach()

    uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

    if st.button("Analyze and Add Document"):
        if uploaded_file is not None:
            with st.status("Processing document...", expanded=True) as status:
                try:
                    status.write("📄 Extracting text from PDF...")
                    raw_text = extract_text_from_pdf(uploaded_file.getvalue())

                    if not raw_text:
                        status.update(
                            label="PDF processing failed.", state="error", expanded=True
                        )
                        st.error(
                            "Could not extract text from the PDF. The file might be empty or corrupted."
                        )
                        return

                    status.write("🤖 Structuring data with AI...")
                    structured_docs = create_structured_documents(raw_text, coach.llm)
                    logger.info(f"Structured documents from LLM: {structured_docs}")

                    if not structured_docs:
                        status.update(
                            label="Data structuring failed.",
                            state="error",
                            expanded=True,
                        )
                        st.error(
                            "Failed to create any structured documents from the text. The content might be unsupported or empty."
                        )
                        return

                    valid_docs = []
                    malformed_count = 0
                    for doc in structured_docs:
                        if isinstance(doc, dict) and "doc_id" in doc and "text" in doc:
                            valid_docs.append(doc)
                        else:
                            malformed_count += 1

                    if malformed_count > 0:
                        logger.warning(
                            f"Discarded {malformed_count} malformed document objects from LLM output."
                        )
                        st.warning(
                            f"Could not process {malformed_count} entries from the document due to formatting issues."
                        )

                    if not valid_docs:
                        status.update(
                            label="No valid data found.", state="error", expanded=True
                        )
                        st.error(
                            "The document could not be processed into any valid data entries."
                        )
                        return

                    status.write(
                        f"➕ Adding {len(valid_docs)} new document(s) to knowledge base..."
                    )
                    with open(DOCS_FILE, "a") as f:
                        for doc in valid_docs:
                            f.write(json.dumps(doc) + "\n")

                    status.write("🔄 Reloading knowledge base...")
                    st.cache_resource.clear()

                    status.update(
                        label="Processing Complete!", state="complete", expanded=False
                    )
                    st.success(
                        f"Successfully processed and added {len(valid_docs)} new document(s)."
                    )

                except Exception as e:
                    logger.error(f"An error occurred during PDF processing: {e}")
                    tb_str = traceback.format_exc()
                    logger.error(tb_str)
                    st.error(f"An error occurred during processing: {e}")
        else:
            st.warning("Please upload a PDF file first.")


# --- Main execution ---
if __name__ == "__main__":
    show_upload_documents() 