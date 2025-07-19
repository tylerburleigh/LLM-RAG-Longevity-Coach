# coach/utils.py
import json
import streamlit as st
import os
import logging
import ast
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from coach.vector_store_factory import get_vector_store
from coach.longevity_coach import LongevityCoach
from coach.config import config
from coach.models import Document
from coach.exceptions import VectorStoreException

if TYPE_CHECKING:
    from coach.tenant import TenantManager

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


@st.cache_resource
def initialize_tenant_coach(tenant_manager: "TenantManager"):
    """Initialize a tenant-specific vector store and coach."""
    from coach.vector_store_factory import get_tenant_vector_store
    
    # Get tenant-specific vector store
    vector_store = get_tenant_vector_store(tenant_manager)
    
    # Load tenant-specific documents
    docs_path = tenant_manager.get_documents_path()
    if os.path.exists(docs_path):
        docs = load_tenant_docs_from_jsonl(tenant_manager)
        update_vector_store_from_docs(vector_store, docs)
        vector_store.save()
    else:
        logger.info(f"Tenant docs file {docs_path} not found. Skipping update.")
    
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


def load_tenant_docs_from_jsonl(tenant_manager: "TenantManager") -> List[Dict[str, Any]]:
    """
    Loads documents from a tenant-specific JSONL file.
    
    Args:
        tenant_manager: TenantManager instance for accessing tenant-specific paths.
        
    Returns:
        List of document dictionaries.
    """
    file_path = tenant_manager.get_documents_path()
    return load_docs_from_jsonl(file_path)


def save_docs_to_jsonl(file_path: str, docs: List[Dict[str, Any]], mode: str = 'w') -> None:
    """
    Saves documents to a JSONL file.
    
    Args:
        file_path: Path to the JSONL file.
        docs: List of document dictionaries to save.
        mode: File open mode ('w' for write/overwrite, 'a' for append).
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    try:
        with open(file_path, mode, encoding='utf-8') as f:
            for doc in docs:
                # Ensure required fields exist
                if not isinstance(doc, dict) or "doc_id" not in doc or "text" not in doc:
                    logger.warning(f"Skipping invalid document: {doc}")
                    continue
                
                # Write as JSON line
                f.write(json.dumps(doc, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved {len(docs)} documents to {file_path}")
        
    except Exception as e:
        logger.error(f"Error saving documents to {file_path}: {e}")
        raise


def save_tenant_docs_to_jsonl(tenant_manager: "TenantManager", docs: List[Dict[str, Any]], mode: str = 'w') -> None:
    """
    Saves documents to a tenant-specific JSONL file.
    
    Args:
        tenant_manager: TenantManager instance for accessing tenant-specific paths.
        docs: List of document dictionaries to save.
        mode: File open mode ('w' for write/overwrite, 'a' for append).
    """
    file_path = tenant_manager.get_documents_path()
    save_docs_to_jsonl(file_path, docs, mode)


def append_doc_to_jsonl(file_path: str, doc: Dict[str, Any]) -> None:
    """
    Appends a single document to a JSONL file.
    
    Args:
        file_path: Path to the JSONL file.
        doc: Document dictionary to append.
    """
    save_docs_to_jsonl(file_path, [doc], mode='a')


def append_tenant_doc_to_jsonl(tenant_manager: "TenantManager", doc: Dict[str, Any]) -> None:
    """
    Appends a single document to a tenant-specific JSONL file.
    
    Args:
        tenant_manager: TenantManager instance for accessing tenant-specific paths.
        doc: Document dictionary to append.
    """
    file_path = tenant_manager.get_documents_path()
    append_doc_to_jsonl(file_path, doc)


def delete_doc_from_jsonl(file_path: str, doc_id: str) -> bool:
    """
    Deletes a document from a JSONL file by doc_id.
    
    Args:
        file_path: Path to the JSONL file.
        doc_id: ID of the document to delete.
        
    Returns:
        True if document was found and deleted, False otherwise.
    """
    if not os.path.exists(file_path):
        logger.warning(f"JSONL file not found at {file_path}")
        return False
    
    # Load all documents
    docs = load_docs_from_jsonl(file_path)
    original_count = len(docs)
    
    # Filter out the document to delete
    filtered_docs = [doc for doc in docs if doc.get("doc_id") != doc_id]
    
    if len(filtered_docs) == original_count:
        logger.warning(f"Document with ID {doc_id} not found in {file_path}")
        return False
    
    # Rewrite the file without the deleted document
    save_docs_to_jsonl(file_path, filtered_docs)
    logger.info(f"Deleted document with ID {doc_id} from {file_path}")
    return True


def delete_tenant_doc_from_jsonl(tenant_manager: "TenantManager", doc_id: str) -> bool:
    """
    Deletes a document from a tenant-specific JSONL file by doc_id.
    
    Args:
        tenant_manager: TenantManager instance for accessing tenant-specific paths.
        doc_id: ID of the document to delete.
        
    Returns:
        True if document was found and deleted, False otherwise.
    """
    file_path = tenant_manager.get_documents_path()
    return delete_doc_from_jsonl(file_path, doc_id)


def update_doc_in_jsonl(file_path: str, doc_id: str, updated_doc: Dict[str, Any]) -> bool:
    """
    Updates a document in a JSONL file by doc_id.
    
    Args:
        file_path: Path to the JSONL file.
        doc_id: ID of the document to update.
        updated_doc: Updated document dictionary (must contain doc_id and text).
        
    Returns:
        True if document was found and updated, False otherwise.
    """
    if not os.path.exists(file_path):
        logger.warning(f"JSONL file not found at {file_path}")
        return False
    
    # Ensure updated_doc has required fields
    if "doc_id" not in updated_doc or "text" not in updated_doc:
        logger.error("Updated document must contain 'doc_id' and 'text' fields")
        return False
    
    # Load all documents
    docs = load_docs_from_jsonl(file_path)
    found = False
    
    # Update the matching document
    for i, doc in enumerate(docs):
        if doc.get("doc_id") == doc_id:
            docs[i] = updated_doc
            found = True
            break
    
    if not found:
        logger.warning(f"Document with ID {doc_id} not found in {file_path}")
        return False
    
    # Rewrite the file with the updated document
    save_docs_to_jsonl(file_path, docs)
    logger.info(f"Updated document with ID {doc_id} in {file_path}")
    return True


def update_tenant_doc_in_jsonl(tenant_manager: "TenantManager", doc_id: str, updated_doc: Dict[str, Any]) -> bool:
    """
    Updates a document in a tenant-specific JSONL file by doc_id.
    
    Args:
        tenant_manager: TenantManager instance for accessing tenant-specific paths.
        doc_id: ID of the document to update.
        updated_doc: Updated document dictionary (must contain doc_id and text).
        
    Returns:
        True if document was found and updated, False otherwise.
    """
    file_path = tenant_manager.get_documents_path()
    return update_doc_in_jsonl(file_path, doc_id, updated_doc)

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
