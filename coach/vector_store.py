import os
import pickle
import logging
import faiss
import numpy as np
from openai import OpenAI
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

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
    EmbeddingVector,
    VectorStoreDocument,
    SearchResult,
)

# Configure logging
logger = logging.getLogger(__name__)

class PersistentVectorStore:
    def __init__(self, 
                 store_folder: Optional[str] = None, 
                 index_filename: Optional[str] = None, 
                 docs_filename: Optional[str] = None,
                 embedding_model: Optional[str] = None,
                 vector_dim: Optional[int] = None):
        """
        Initializes the vector store.
        """
        self.store_folder = store_folder or config.VECTOR_STORE_FOLDER
        self.embedding_model = embedding_model or config.EMBEDDING_MODEL
        self.dimension = vector_dim or config.EMBEDDING_DIMENSION
        
        api_key = config.get_api_key("openai")
        if not api_key:
            raise VectorStoreException(
                "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
            )
        self.client = OpenAI(api_key=api_key)
        self.bm25_index = None
        
        index_filename = index_filename or config.FAISS_INDEX_FILENAME
        docs_filename = docs_filename or config.DOCUMENTS_FILENAME

        if not os.path.exists(self.store_folder):
            os.makedirs(self.store_folder)
            logger.info(f"Created folder: {self.store_folder}")
        
        self.index_path = os.path.join(self.store_folder, index_filename)
        self.docs_path = os.path.join(self.store_folder, docs_filename)
        
        if os.path.exists(self.index_path) and os.path.exists(self.docs_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.docs_path, "rb") as f:
                self.documents = pickle.load(f)
            logger.info(f"Loaded existing vector store with {len(self.documents)} documents.")
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.documents = []
            logger.info("Initialized new vector store.")

        self._build_bm25_index()

    def _build_bm25_index(self):
        """Builds or rebuilds the BM25 index from the documents."""
        if self.documents:
            logger.info("Building BM25 index...")
            tokenized_corpus = [doc["text"].lower().split() for doc in self.documents]
            self.bm25_index = BM25Okapi(tokenized_corpus)
            logger.info("BM25 index built successfully.")
        else:
            self.bm25_index = None

    def get_embeddings(self, texts: List[str]) -> List[EmbeddingVector]:
        """Get embeddings for a list of texts using OpenAI's API."""
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=self.embedding_model
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise EmbeddingException(f"Failed to generate embeddings: {str(e)}") from e

    def add_documents(self, docs: List[Dict[str, Any]]):
        """Add a list of documents to the vector store."""
        if not docs:
            return

        texts = [doc["text"] for doc in docs]
        logger.info(f"Adding {len(texts)} documents.")
        
        embeddings = self.get_embeddings(texts)
        embeddings_np = np.array(embeddings, dtype=np.float32)
        
        if embeddings_np.shape[1] != self.dimension:
            raise ValueError(f"Embedding dimension {embeddings_np.shape[1]} does not match index dimension {self.dimension}")
            
        self.index.add(embeddings_np)
        self.documents.extend(docs)
        self._build_bm25_index() # Rebuild BM25 index after adding new documents
        logger.info(f"Successfully added documents. Total documents: {len(self.documents)}")

    def add_document(self, doc_id: DocumentID, text: str, metadata: Optional[Dict] = None):
        """Add a single document to the vector store."""
        doc = {"doc_id": doc_id, "text": text, "metadata": metadata}
        self.add_documents([doc])

    def save(self):
        """Save the vector store (both index and documents) to the specified folder."""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.docs_path, "wb") as f:
                pickle.dump(self.documents, f)
            logger.info(f"Saved vector store with {len(self.documents)} documents in folder {self.store_folder}.")
        except Exception as e:
            raise VectorStoreSaveException(f"Failed to save vector store: {str(e)}") from e

    def semantic_search(self, query: Query, top_k: int) -> List[VectorStoreDocument]:
        """Performs semantic search using FAISS."""
        query_embedding = self.get_embeddings([query])[0]
        query_np = np.expand_dims(query_embedding, axis=0).astype(np.float32)
        
        distances, indices = self.index.search(query_np, top_k)
        
        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(self.documents):
                results.append(self.documents[idx])
        return results

    def keyword_search(self, query: Query, top_k: int) -> List[VectorStoreDocument]:
        """Performs keyword search using BM25."""
        if not self.bm25_index:
            return []

        tokenized_query = query.lower().split()
        doc_scores = self.bm25_index.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = np.argsort(doc_scores)[::-1][:top_k]

        return [self.documents[i] for i in top_indices if doc_scores[i] > 0]

    def search(self, query: Query, top_k: Optional[int] = None, k_rrf: Optional[int] = None) -> List[VectorStoreDocument]:
        """
        Performs hybrid search by combining semantic and keyword search results using RRF.
        """
        top_k = top_k or config.DEFAULT_TOP_K
        k_rrf = k_rrf or config.RRF_K
        
        semantic_results = self.semantic_search(query, top_k=top_k * config.SEARCH_MULTIPLIER)
        keyword_results = self.keyword_search(query, top_k=top_k * config.SEARCH_MULTIPLIER)

        rrf_scores = {}
        all_docs = {}

        for i, doc in enumerate(semantic_results):
            doc_id = doc['doc_id']
            all_docs[doc_id] = doc
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0
            rrf_scores[doc_id] += 1 / (k_rrf + i + 1)

        for i, doc in enumerate(keyword_results):
            doc_id = doc['doc_id']
            all_docs[doc_id] = doc
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0
            rrf_scores[doc_id] += 1 / (k_rrf + i + 1)

        if not rrf_scores:
            return []

        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        final_results = [all_docs[doc_id] for doc_id in sorted_doc_ids]

        return final_results[:top_k]