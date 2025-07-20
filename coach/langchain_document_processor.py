# coach/langchain_document_processor.py
import logging
import os
import json
import tempfile
from typing import List, Optional, IO, TYPE_CHECKING
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

if TYPE_CHECKING:
    from coach.tenant import TenantManager
    from coach.config import Config

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
    
    def extract_text_from_pdf_stream(self, file_stream: IO[bytes]) -> str:
        """
        Extract text from a PDF file stream.
        
        Args:
            file_stream: A file-like object representing the PDF
            
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


class TenantAwareDocumentProcessor(DocumentProcessor):
    """Tenant-aware document processor that extends DocumentProcessor with multi-tenant support."""
    
    def __init__(
        self,
        tenant_manager: "TenantManager",
        config: Optional["Config"] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize the tenant-aware document processor.
        
        Args:
            tenant_manager: TenantManager instance for handling tenant-specific operations
            config: Configuration object (optional, will use default if not provided)
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks
            separators: List of separators for text splitting
            **kwargs: Additional arguments for text splitter
        """
        from coach.config import config as default_config
        
        super().__init__(chunk_size, chunk_overlap, separators, **kwargs)
        self.tenant_manager = tenant_manager
        self.config = config or default_config
        
        logger.info(f"Initialized TenantAwareDocumentProcessor for tenant: {tenant_manager.tenant_id}")
    
    def get_temp_directory(self) -> str:
        """Get tenant-specific temporary directory."""
        temp_dir = self.tenant_manager.get_tenant_path("temp")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
    
    def extract_text_from_pdf_stream(self, file_stream: IO[bytes]) -> str:
        """
        Extract text from a PDF file stream using tenant-specific temporary storage.
        
        Args:
            file_stream: A file-like object representing the PDF
            
        Returns:
            The extracted text as a single string
            
        Raises:
            PDFExtractionException: If text extraction fails
        """
        try:
            # Use tenant-specific temp directory
            temp_dir = self.get_temp_directory()
            
            # Create temporary file in tenant directory
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.pdf',
                dir=temp_dir
            ) as tmp_file:
                tmp_file.write(file_stream.read())
                tmp_file_path = tmp_file.name
            
            try:
                # Extract text using file path
                text = self.extract_text_from_pdf_file(tmp_file_path)
                return text
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    
        except Exception as e:
            logger.error(f"Error extracting text from PDF stream for tenant {self.tenant_manager.tenant_id}: {e}")
            raise PDFExtractionException(f"Failed to extract text from PDF stream: {str(e)}") from e
    
    def save_documents(self, documents: List[Document]) -> None:
        """
        Save documents to tenant-specific JSONL file.
        
        Args:
            documents: List of Document objects to save
        """
        docs_path = self.tenant_manager.get_documents_path()
        
        # Ensure tenant directory exists
        os.makedirs(os.path.dirname(docs_path), exist_ok=True)
        
        # Convert documents to dictionaries
        docs_data = []
        for doc in documents:
            doc_dict = {
                "doc_id": doc.doc_id,
                "text": doc.text,
                "metadata": doc.metadata
            }
            docs_data.append(doc_dict)
        
        # Append to existing JSONL file
        try:
            with open(docs_path, 'a', encoding='utf-8') as f:
                for doc_dict in docs_data:
                    f.write(json.dumps(doc_dict, ensure_ascii=False) + '\n')
            
            logger.info(f"Saved {len(documents)} documents to {docs_path}")
            
        except Exception as e:
            logger.error(f"Error saving documents for tenant {self.tenant_manager.tenant_id}: {e}")
            raise
    
    def load_documents(self) -> List[Document]:
        """
        Load documents from tenant-specific JSONL file.
        
        Returns:
            List of Document objects
        """
        docs_path = self.tenant_manager.get_documents_path()
        
        if not os.path.exists(docs_path):
            logger.info(f"No documents file found for tenant {self.tenant_manager.tenant_id}")
            return []
        
        documents = []
        try:
            with open(docs_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        doc_dict = json.loads(line)
                        doc = Document(
                            doc_id=doc_dict.get("doc_id", ""),
                            text=doc_dict.get("text", ""),
                            metadata=doc_dict.get("metadata", {})
                        )
                        documents.append(doc)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Error loading document on line {line_num} for tenant {self.tenant_manager.tenant_id}: {e}")
                        continue
            
            logger.info(f"Loaded {len(documents)} documents for tenant {self.tenant_manager.tenant_id}")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading documents for tenant {self.tenant_manager.tenant_id}: {e}")
            raise
    
    def process_and_save_pdf(
        self,
        file_path: Optional[str] = None,
        file_stream: Optional[IO[bytes]] = None,
        llm=None,
        use_chunking: bool = False,
        auto_save: bool = True
    ) -> List[Document]:
        """
        Process a PDF file into structured documents and optionally save them.
        
        Args:
            file_path: Path to PDF file (alternative to file_stream)
            file_stream: PDF file stream (alternative to file_path)
            llm: Language model for structuring
            use_chunking: Whether to use text chunking before structuring
            auto_save: Whether to automatically save documents to tenant storage
            
        Returns:
            List of structured Document objects
        """
        # Process PDF to structured documents
        documents = self.process_pdf_to_structured_documents(
            file_path=file_path,
            file_stream=file_stream,
            llm=llm,
            use_chunking=use_chunking
        )
        
        # Save documents if auto_save is enabled
        if auto_save and documents:
            self.save_documents(documents)
        
        return documents


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


def get_document_processor(tenant_manager: Optional["TenantManager"] = None, **kwargs):
    """
    Factory function to get appropriate document processor.
    
    Args:
        tenant_manager: Optional TenantManager for tenant-aware processing
        **kwargs: Additional arguments passed to processor constructor
        
    Returns:
        DocumentProcessor or TenantAwareDocumentProcessor instance
    """
    if tenant_manager is not None:
        return TenantAwareDocumentProcessor(tenant_manager, **kwargs)
    else:
        return DocumentProcessor(**kwargs)