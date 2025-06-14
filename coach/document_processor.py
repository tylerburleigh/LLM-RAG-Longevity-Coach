# coach/document_processor.py
import fitz  # PyMuPDF
import json
from langchain_core.messages import HumanMessage
from coach.prompts import DOCUMENT_STRUCTURE_PROMPT_TEMPLATE
import logging
from typing import List

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_stream) -> str:
    """
    Extracts text from a PDF file stream.

    Args:
        file_stream: A file-like object representing the PDF.

    Returns:
        The extracted text as a single string.
    """
    text = ""
    try:
        with fitz.open(stream=file_stream, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""
    return text

def create_structured_documents(raw_text: str, llm) -> List[dict]:
    """
    Uses an LLM to convert raw text into a list of structured JSON documents.

    Args:
        raw_text: The raw text extracted from a document.
        llm: The language model instance to use.

    Returns:
        A list of dictionaries, each representing a structured document.
    """
    prompt = DOCUMENT_STRUCTURE_PROMPT_TEMPLATE.format(raw_text=raw_text)
    messages = [HumanMessage(content=prompt)]
    
    structured_docs = []
    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # Clean the content to get just the JSONL part
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        # Split the content by newlines and parse each line as a JSON object
        for line in content.splitlines():
            line = line.strip()
            if line:
                try:
                    structured_docs.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Skipping line that is not valid JSON: {line}")
                    continue
        
        return structured_docs

    except Exception as e:
        logger.error(f"An unexpected error occurred while creating structured documents: {e}")
        return [] 