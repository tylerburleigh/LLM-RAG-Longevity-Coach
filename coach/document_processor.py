# coach/document_processor.py
"""Document processing using LangChain components."""

import logging
from typing import List

from coach.langchain_document_processor import (
    DocumentProcessor as LangChainDocumentProcessor,
    extract_text_from_pdf as langchain_extract_text_from_pdf,
    create_structured_documents as langchain_create_structured_documents,
)
from coach.models import Document
from coach.exceptions import (
    PDFExtractionException,
    DocumentStructuringException,
)

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_stream) -> str:
    """
    Extract text from a PDF file stream using LangChain.

    Args:
        file_stream: A file-like object representing the PDF.

    Returns:
        The extracted text as a single string.
        
    Raises:
        PDFExtractionException: If text extraction fails.
    """
    return langchain_extract_text_from_pdf(file_stream)


def create_structured_documents(raw_text: str, llm) -> List[Document]:
    """
    Use LangChain to convert raw text into structured documents.

    Args:
        raw_text: The raw text extracted from a document.
        llm: The language model instance to use.

    Returns:
        A list of Document objects, each representing a structured document.
        
    Raises:
        DocumentStructuringException: If document structuring fails.
    """
    return langchain_create_structured_documents(raw_text, llm)


# Create a document processor instance for advanced use cases
def create_document_processor(**kwargs) -> LangChainDocumentProcessor:
    """
    Create a LangChain document processor instance.
    
    Args:
        **kwargs: Additional parameters for the document processor
        
    Returns:
        LangChainDocumentProcessor instance
    """
    return LangChainDocumentProcessor(**kwargs)