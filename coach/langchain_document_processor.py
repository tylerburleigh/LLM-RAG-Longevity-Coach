# coach/langchain_document_processor.py
import logging
from typing import List, Optional, IO, Union
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel

from coach.models import Document
from coach.prompts import DOCUMENT_STRUCTURE_PROMPT_TEMPLATE
from coach.exceptions import (
    PDFExtractionException,
    DocumentStructuringException,
)

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """LangChain-based document processor with text splitting and structuring."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            separators: List of separators for text splitting
            **kwargs: Additional arguments for text splitter
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
            **kwargs
        )
        
        logger.info(f"Initialized DocumentProcessor with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
    
    def extract_text_from_pdf_file(self, file_path: str) -> str:
        """
        Extract text from a PDF file using LangChain's PyMuPDFLoader.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            The extracted text as a single string
            
        Raises:
            PDFExtractionException: If text extraction fails
        """
        try:
            loader = PyMuPDFLoader(file_path)
            documents = loader.load()
            
            # Combine all pages into a single text
            text = "\n\n".join(doc.page_content for doc in documents)
            
            logger.info(f"Extracted {len(text)} characters from {len(documents)} pages")
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise PDFExtractionException(f"Failed to extract text from PDF: {str(e)}") from e
    
    def extract_text_from_pdf_stream(self, file_stream: Union[IO[bytes], bytes]) -> str:
        """
        Extract text from a PDF file stream.
        
        Args:
            file_stream: A file-like object or bytes representing the PDF
            
        Returns:
            The extracted text as a single string
            
        Raises:
            PDFExtractionException: If text extraction fails
        """
        import tempfile
        import os
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                # Handle both bytes and file-like objects
                if isinstance(file_stream, bytes):
                    tmp_file.write(file_stream)
                else:
                    tmp_file.write(file_stream.read())
                tmp_file_path = tmp_file.name
            
            try:
                # Extract text using file path
                text = self.extract_text_from_pdf_file(tmp_file_path)
                return text
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Error extracting text from PDF stream: {e}")
            raise PDFExtractionException(f"Failed to extract text from PDF stream: {str(e)}") from e
    
    def split_text(self, text: str) -> List[LangChainDocument]:
        """
        Split text into chunks using RecursiveCharacterTextSplitter.
        
        Args:
            text: The text to split
            
        Returns:
            List of LangChain Document objects
        """
        try:
            # Create a document from the text
            doc = LangChainDocument(page_content=text)
            
            # Split the document
            chunks = self.text_splitter.split_documents([doc])
            
            logger.info(f"Split text into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting text: {e}")
            return [LangChainDocument(page_content=text)]
    
    def create_structured_documents(self, raw_text: str, llm) -> List[Document]:
        """
        Convert raw text into structured documents using LLM.
        
        Args:
            raw_text: The raw text to structure
            llm: The language model instance
            
        Returns:
            List of structured Document objects
            
        Raises:
            DocumentStructuringException: If structuring fails
        """
        try:
            # Create prompt template
            prompt = PromptTemplate.from_template(DOCUMENT_STRUCTURE_PROMPT_TEMPLATE)
            
            # Format the prompt
            formatted_prompt = prompt.format(raw_text=raw_text)
            messages = [HumanMessage(content=formatted_prompt)]
            
            # Get response from LLM
            response = llm.invoke(messages)
            content = response.content.strip()
            
            # Clean the content to get just the JSONL part
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            # Parse the structured documents
            structured_docs = []
            for line in content.splitlines():
                line = line.strip()
                if line:
                    try:
                        import json
                        doc_dict = json.loads(line)
                        # Convert to Document model
                        doc = Document(
                            doc_id=doc_dict.get("doc_id", ""),
                            text=doc_dict.get("text", ""),
                            metadata=doc_dict.get("metadata", {})
                        )
                        structured_docs.append(doc)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping line that is not valid JSON: {line}")
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to create Document from: {line}. Error: {e}")
                        continue
            
            logger.info(f"Created {len(structured_docs)} structured documents")
            return structured_docs
            
        except Exception as e:
            logger.error(f"Error creating structured documents: {e}")
            raise DocumentStructuringException(
                f"Failed to create structured documents: {str(e)}"
            ) from e
    
    def process_pdf_to_structured_documents(
        self, 
        file_path: Optional[str] = None,
        file_stream: Optional[IO[bytes]] = None,
        llm=None,
        use_chunking: bool = False
    ) -> List[Document]:
        """
        Process a PDF file into structured documents.
        
        Args:
            file_path: Path to PDF file (alternative to file_stream)
            file_stream: PDF file stream (alternative to file_path)
            llm: Language model for structuring
            use_chunking: Whether to use text chunking before structuring
            
        Returns:
            List of structured Document objects
            
        Raises:
            PDFExtractionException: If PDF processing fails
            DocumentStructuringException: If structuring fails
        """
        if file_path is None and file_stream is None:
            raise ValueError("Either file_path or file_stream must be provided")
        
        if file_path is not None and file_stream is not None:
            raise ValueError("Only one of file_path or file_stream should be provided")
        
        # Extract text
        if file_path:
            raw_text = self.extract_text_from_pdf_file(file_path)
        else:
            raw_text = self.extract_text_from_pdf_stream(file_stream)
        
        if not raw_text.strip():
            logger.warning("No text extracted from PDF")
            return []
        
        # Optionally split text into chunks
        if use_chunking:
            chunks = self.split_text(raw_text)
            all_documents = []
            
            for i, chunk in enumerate(chunks):
                chunk_docs = self.create_structured_documents(chunk.page_content, llm)
                # Add chunk index to metadata
                for doc in chunk_docs:
                    doc.metadata["chunk_index"] = i
                all_documents.extend(chunk_docs)
                
            return all_documents
        else:
            # Process as single document
            return self.create_structured_documents(raw_text, llm)


# Backward compatibility functions
def extract_text_from_pdf(file_stream: IO[bytes]) -> str:
    """
    Extract text from a PDF file stream (backward compatibility).
    
    Args:
        file_stream: A file-like object representing the PDF
        
    Returns:
        The extracted text as a single string
        
    Raises:
        PDFExtractionException: If text extraction fails
    """
    processor = DocumentProcessor()
    return processor.extract_text_from_pdf_stream(file_stream)


def create_structured_documents(raw_text: str, llm) -> List[Document]:
    """
    Create structured documents from raw text (backward compatibility).
    
    Args:
        raw_text: The raw text to structure
        llm: The language model instance
        
    Returns:
        List of structured Document objects
        
    Raises:
        DocumentStructuringException: If structuring fails
    """
    processor = DocumentProcessor()
    return processor.create_structured_documents(raw_text, llm)