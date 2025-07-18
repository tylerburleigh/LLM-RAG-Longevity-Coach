# coach/utils.py
import json
import streamlit as st
import os
import logging
import ast
from typing import List, Dict, Any

from coach.vector_store_factory import get_vector_store
from coach.longevity_coach import LongevityCoach
from coach.config import config
from coach.models import Document
from coach.exceptions import VectorStoreException

# Configure logging
logger = logging.getLogger(__name__)


@st.cache_resource
def initialize_coach():
    """Initialize the vector store and coach."""
    vector_store = get_vector_store()
    if os.path.exists(config.DOCS_FILE):
        docs = load_docs_from_jsonl(config.DOCS_FILE)
        update_vector_store_from_docs(vector_store, docs)
        vector_store.save()
    else:
        logger.info(f"Docs file {config.DOCS_FILE} not found. Skipping update.")
    return LongevityCoach(vector_store)


def load_docs_from_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """
    Loads documents from a JSONL file, skipping any malformed lines.
    
    Args:
        file_path: Path to the JSONL file.
        
    Returns:
        List of document dictionaries.
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
                        # Handle string metadata by parsing it safely
                        if "metadata" in doc and isinstance(doc["metadata"], str):
                            try:
                                # Try to parse string metadata as Python literal
                                parsed_metadata = ast.literal_eval(doc["metadata"])
                                if isinstance(parsed_metadata, dict):
                                    doc["metadata"] = parsed_metadata
                                    logger.info(f"Parsed string metadata on line {i} in {file_path}")
                                else:
                                    logger.warning(f"String metadata on line {i} in {file_path} is not a dict, keeping as string")
                            except (ValueError, SyntaxError) as e:
                                logger.warning(f"Failed to parse string metadata on line {i} in {file_path}: {e}")
                        docs.append(doc)
                    else:
                        logger.warning(f"Skipping malformed document on line {i} in {file_path}: Missing 'doc_id' or 'text'.")
                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON on line {i} in {file_path}.")
    except FileNotFoundError:
        logger.warning(f"JSONL file not found at {file_path}. Returning empty list.")
        return []
    return docs

def update_vector_store_from_docs(vector_store, docs: List[Dict[str, Any]]) -> None:
    """
    Update the LangChain vector store with new documents.
    
    Args:
        vector_store: The LangChain vector store instance
        docs: List of document dictionaries to add
    """
    # LangChain vector store interface
    current_doc_count = vector_store.get_document_count()
    logger.info(f"Updating vector store. Loaded {len(docs)} docs from JSONL. Vector store currently has {current_doc_count} docs.")
    
    # Get existing document IDs
    existing_ids = set()
    for doc in vector_store.documents:
        if hasattr(doc, 'metadata') and 'doc_id' in doc.metadata:
            existing_ids.add(doc.metadata['doc_id'])

    new_docs = [doc for doc in docs if doc["doc_id"] not in existing_ids]
    
    if new_docs:
        logger.info(f"Found {len(new_docs)} new documents to add.")
        vector_store.add_documents(new_docs)
    else:
        logger.info("No new documents to add.")
