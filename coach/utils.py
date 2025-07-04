# coach/utils.py
import json
from langchain.docstore.document import Document
import streamlit as st
import os
import logging

from coach.vector_store import PersistentVectorStore
from coach.longevity_coach import LongevityCoach

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOCS_FILE = "docs.jsonl"


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


def load_docs_from_jsonl(file_path):
    """
    Loads documents from a JSONL file, skipping any malformed lines.
    """
    docs = []
    try:
        with open(file_path, "r") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                    if isinstance(doc, dict) and "doc_id" in doc and "text" in doc:
                        docs.append(doc)
                    else:
                        logger.warning(f"Skipping malformed document on line {i} in {file_path}: Missing 'doc_id' or 'text'.")
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON on line {i} in {file_path}.")
    except FileNotFoundError:
        logger.warning(f"JSONL file not found at {file_path}. Returning empty list.")
        return []
    return docs

def update_vector_store_from_docs(vector_store, docs):
    logger.info(f"Updating vector store. Loaded {len(docs)} docs from JSONL. Vector store currently has {len(vector_store.documents)} docs.")
    try:
        existing_ids = {doc["doc_id"] for doc in vector_store.documents}
    except KeyError as e:
        logger.error("A document in the existing vector store cache (documents.pkl) is malformed and missing a 'doc_id'.")
        # Find and log the problematic document
        for i, doc in enumerate(vector_store.documents):
            if "doc_id" not in doc:
                logger.error(f"Problematic document at index {i}: {doc}")
        raise e

    new_docs = [doc for doc in docs if doc["doc_id"] not in existing_ids]
    
    if new_docs:
        logger.info(f"Found {len(new_docs)} new documents to add.")
        vector_store.add_documents(new_docs)
    else:
        logger.info("No new documents to add.")
