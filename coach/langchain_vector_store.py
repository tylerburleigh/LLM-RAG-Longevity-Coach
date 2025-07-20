# coach/langchain_vector_store.py
import os
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

from coach.config import config
from coach.exceptions import (
    VectorStoreException,
    VectorStoreSaveException,
    VectorStoreLoadException,
    EmbeddingException,
)
from coach.types import (
    DocumentID,
    Query,
    VectorStoreDocument,
    SearchResult,
)
from coach.llm_providers import get_embeddings
from coach.embeddings import EmbeddingManager

if TYPE_CHECKING:
    from coach.tenant import TenantManager

logger = logging.getLogger(__name__)


class LangChainVectorStore:
    """LangChain-based vector store with hybrid search capabilities."""
    
    def __init__(
        self,
        store_folder: Optional[str] = None,
        embedding_provider: str = "openai",
        embedding_model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the LangChain vector store.
        
        Args:
            store_folder: Directory to store vector store files
            embedding_provider: Provider for embeddings ('openai' or 'google')
            embedding_model: Specific embedding model to use
            **kwargs: Additional parameters for embeddings
        """
        self.store_folder = store_folder or config.VECTOR_STORE_FOLDER
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model or config.EMBEDDING_MODEL
        
        # Create store folder if it doesn't exist
        if not os.path.exists(self.store_folder):
            os.makedirs(self.store_folder)
            logger.info(f"Created folder: {self.store_folder}")
        
        # Initialize embeddings
        try:
            self.embeddings = get_embeddings(
                provider=embedding_provider,
                model=embedding_model,
                **kwargs
            )
            self.embedding_manager = EmbeddingManager(self.embeddings)
        except Exception as e:
            raise VectorStoreException(f"Failed to initialize embeddings: {str(e)}") from e
        
        # Initialize vector store components
        self.faiss_store: Optional[FAISS] = None
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.ensemble_retriever: Optional[EnsembleRetriever] = None
        self.documents: List[Document] = []
        
        # Load existing store if available
        self._load_existing_store()
    
    def _get_faiss_index_path(self) -> str:
        """Get FAISS index path."""
        return os.path.join(self.store_folder, "faiss_index")
    
    def _load_existing_store(self):
        """Load existing vector store from disk."""
        faiss_path = self._get_faiss_index_path()
        
        try:
            if os.path.exists(faiss_path):
                self.faiss_store = FAISS.load_local(
                    faiss_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                # Get documents from FAISS store
                self.documents = list(self.faiss_store.docstore._dict.values())
                logger.info(f"Loaded existing FAISS store with {len(self.documents)} documents")
                
                # Rebuild retrievers
                self._build_retrievers()
            else:
                logger.info("No existing vector store found, will create new one")
        except Exception as e:
            logger.warning(f"Failed to load existing store: {e}")
            self.faiss_store = None
            self.documents = []
    
    def _build_retrievers(self):
        """Build BM25 and ensemble retrievers from current documents."""
        if not self.documents:
            self.bm25_retriever = None
            self.ensemble_retriever = None
            return
        
        try:
            # Create BM25 retriever
            self.bm25_retriever = BM25Retriever.from_documents(self.documents)
            
            # Create ensemble retriever if we have both components
            if self.faiss_store and self.bm25_retriever:
                faiss_retriever = self.faiss_store.as_retriever(
                    search_kwargs={"k": config.DEFAULT_TOP_K * config.SEARCH_MULTIPLIER}
                )
                
                self.ensemble_retriever = EnsembleRetriever(
                    retrievers=[faiss_retriever, self.bm25_retriever],
                    weights=[0.5, 0.5],  # Equal weights for semantic and keyword search
                    search_type="mmr",
                    search_kwargs={"k": config.DEFAULT_TOP_K}
                )
                
                logger.info("Built ensemble retriever with FAISS and BM25")
        except Exception as e:
            logger.error(f"Failed to build retrievers: {e}")
            self.bm25_retriever = None
            self.ensemble_retriever = None
    
    def add_documents(self, docs: List[Dict[str, Any]]):
        """
        Add documents to the vector store.
        
        Args:
            docs: List of document dictionaries with keys: doc_id, text, metadata
        """
        if not docs:
            return
        
        logger.info(f"Adding {len(docs)} documents to vector store")
        
        # Convert to LangChain Document objects
        langchain_docs = []
        for doc in docs:
            langchain_doc = Document(
                page_content=doc["text"],
                metadata={
                    "doc_id": doc["doc_id"],
                    **(doc.get("metadata", {}))
                }
            )
            langchain_docs.append(langchain_doc)
        
        try:
            # Add to FAISS store
            if self.faiss_store is None:
                self.faiss_store = FAISS.from_documents(langchain_docs, self.embeddings)
            else:
                self.faiss_store.add_documents(langchain_docs)
            
            # Update document list
            self.documents.extend(langchain_docs)
            
            # Rebuild retrievers
            self._build_retrievers()
            
            logger.info(f"Successfully added documents. Total: {len(self.documents)}")
            
        except Exception as e:
            raise VectorStoreException(f"Failed to add documents: {str(e)}") from e
    
    def add_document(self, doc_id: DocumentID, text: str, metadata: Optional[Dict] = None):
        """Add a single document to the vector store."""
        doc = {
            "doc_id": doc_id,
            "text": text,
            "metadata": metadata or {}
        }
        self.add_documents([doc])
    
    def search(self, query: Query, top_k: Optional[int] = None) -> List[VectorStoreDocument]:
        """
        Perform hybrid search using ensemble retriever.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        top_k = top_k or config.DEFAULT_TOP_K
        
        if not self.ensemble_retriever:
            logger.warning("No ensemble retriever available, returning empty results")
            return []
        
        try:
            # Use ensemble retriever for hybrid search
            results = self.ensemble_retriever.get_relevant_documents(query)
            
            # Convert back to expected format
            formatted_results = []
            for doc in results[:top_k]:
                result = {
                    "doc_id": doc.metadata.get("doc_id", ""),
                    "text": doc.page_content,
                    "metadata": doc.metadata
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def semantic_search(self, query: Query, top_k: int) -> List[VectorStoreDocument]:
        """Perform semantic search using FAISS only."""
        if not self.faiss_store:
            return []
        
        try:
            docs = self.faiss_store.similarity_search(query, k=top_k)
            
            results = []
            for doc in docs:
                result = {
                    "doc_id": doc.metadata.get("doc_id", ""),
                    "text": doc.page_content,
                    "metadata": doc.metadata
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def keyword_search(self, query: Query, top_k: int) -> List[VectorStoreDocument]:
        """Perform keyword search using BM25 only."""
        if not self.bm25_retriever:
            return []
        
        try:
            docs = self.bm25_retriever.get_relevant_documents(query)
            
            results = []
            for doc in docs[:top_k]:
                result = {
                    "doc_id": doc.metadata.get("doc_id", ""),
                    "text": doc.page_content,
                    "metadata": doc.metadata
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def save(self):
        """Save the vector store to disk."""
        if not self.faiss_store:
            logger.warning("No FAISS store to save")
            return
        
        try:
            faiss_path = self._get_faiss_index_path()
            self.faiss_store.save_local(faiss_path)
            logger.info(f"Saved vector store with {len(self.documents)} documents")
            
        except Exception as e:
            raise VectorStoreSaveException(f"Failed to save vector store: {str(e)}") from e
    
    def get_document_count(self) -> int:
        """Get the number of documents in the store."""
        return len(self.documents)
    
    def clear(self):
        """Clear all documents from the store."""
        self.faiss_store = None
        self.bm25_retriever = None
        self.ensemble_retriever = None
        self.documents = []
        logger.info("Cleared vector store")


class TenantAwareLangChainVectorStore(LangChainVectorStore):
    """Tenant-aware vector store that isolates data by tenant."""
    
    def __init__(
        self,
        tenant_manager: "TenantManager",
        embedding_provider: str = "openai",
        embedding_model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the tenant-aware vector store.
        
        Args:
            tenant_manager: TenantManager instance for tenant isolation
            embedding_provider: Provider for embeddings ('openai' or 'google')
            embedding_model: Specific embedding model to use
            **kwargs: Additional parameters for embeddings
        """
        self.tenant_manager = tenant_manager
        
        # Override the store folder to use tenant-specific path
        tenant_store_folder = tenant_manager.get_vector_store_path()
        
        # Initialize parent class with tenant-specific folder
        super().__init__(
            store_folder=tenant_store_folder,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            **kwargs
        )
        
        logger.info(f"Initialized tenant-aware vector store for tenant {tenant_manager.tenant_id}")
    
    def _get_faiss_index_path(self) -> str:
        """Get tenant-specific FAISS index path."""
        return os.path.join(self.store_folder, "faiss_index")
    
    def _get_documents_path(self) -> str:
        """Get tenant-specific documents path."""
        return self.tenant_manager.get_documents_path()
    
    def _load_existing_store(self):
        """Load existing tenant-specific vector store from disk."""
        faiss_path = self._get_faiss_index_path()
        
        try:
            if os.path.exists(faiss_path):
                self.faiss_store = FAISS.load_local(
                    faiss_path, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                # Get documents from FAISS store
                self.documents = list(self.faiss_store.docstore._dict.values())
                logger.info(
                    f"Loaded existing FAISS store for tenant {self.tenant_manager.tenant_id} "
                    f"with {len(self.documents)} documents"
                )
                
                # Rebuild retrievers
                self._build_retrievers()
            else:
                logger.info(
                    f"No existing vector store found for tenant {self.tenant_manager.tenant_id}, "
                    "will create new one"
                )
        except Exception as e:
            logger.warning(
                f"Failed to load existing store for tenant {self.tenant_manager.tenant_id}: {e}"
            )
            self.faiss_store = None
            self.documents = []
    
    def save(self):
        """Save the tenant-specific vector store to disk."""
        if not self.faiss_store:
            logger.warning(f"No FAISS store to save for tenant {self.tenant_manager.tenant_id}")
            return
        
        try:
            faiss_path = self._get_faiss_index_path()
            self.faiss_store.save_local(faiss_path)
            logger.info(
                f"Saved vector store for tenant {self.tenant_manager.tenant_id} "
                f"with {len(self.documents)} documents"
            )
            
        except Exception as e:
            raise VectorStoreSaveException(
                f"Failed to save vector store for tenant {self.tenant_manager.tenant_id}: {str(e)}"
            ) from e
    
    def get_tenant_id(self) -> str:
        """Get the tenant ID for this vector store."""
        return self.tenant_manager.tenant_id