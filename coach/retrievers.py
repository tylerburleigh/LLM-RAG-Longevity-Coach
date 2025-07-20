# coach/retrievers.py
"""Advanced retrieval strategies using LangChain retrievers."""

import logging
from typing import List, Dict, Any, Optional, Union
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import (
    EnsembleRetriever,
    ContextualCompressionRetriever,
    MultiQueryRetriever,
)
from langchain.retrievers.document_compressors import (
    LLMChainExtractor,
    EmbeddingsFilter,
)
from langchain_core.language_models import BaseLanguageModel

from coach.config import config
from coach.exceptions import RetrievalException
from coach.types import Query, VectorStoreDocument

logger = logging.getLogger(__name__)


class AdvancedRetriever:
    """Advanced retrieval strategies using LangChain retrievers."""
    
    def __init__(
        self,
        vector_store,
        llm: Optional[BaseLanguageModel] = None,
        embedding_model=None,
        **kwargs
    ):
        """
        Initialize the advanced retriever.
        
        Args:
            vector_store: The vector store instance
            llm: Language model for query expansion and compression
            embedding_model: Embedding model for similarity filtering
            **kwargs: Additional configuration options
        """
        self.vector_store = vector_store
        self.llm = llm
        self.embedding_model = embedding_model
        self.retrievers = {}
        
        # Initialize basic retrievers
        self._initialize_retrievers()
        
        logger.info("Initialized AdvancedRetriever with multiple retrieval strategies")
    
    def _initialize_retrievers(self):
        """Initialize various retrieval strategies."""
        try:
            # Basic vector store retriever
            if hasattr(self.vector_store, 'faiss_store') and self.vector_store.faiss_store:
                self.retrievers['vector'] = self.vector_store.faiss_store.as_retriever(
                    search_kwargs={"k": config.DEFAULT_TOP_K * config.SEARCH_MULTIPLIER}
                )
            
            # BM25 retriever
            if hasattr(self.vector_store, 'bm25_retriever') and self.vector_store.bm25_retriever:
                self.retrievers['bm25'] = self.vector_store.bm25_retriever
            
            # Ensemble retriever (hybrid search)
            if hasattr(self.vector_store, 'ensemble_retriever') and self.vector_store.ensemble_retriever:
                self.retrievers['ensemble'] = self.vector_store.ensemble_retriever
            
            # Multi-query retriever (if LLM is available)
            if self.llm and 'vector' in self.retrievers:
                self.retrievers['multi_query'] = MultiQueryRetriever.from_llm(
                    retriever=self.retrievers['vector'],
                    llm=self.llm,
                    include_original=True
                )
            
            # Contextual compression retriever (if LLM is available)
            if self.llm and 'ensemble' in self.retrievers:
                compressor = LLMChainExtractor.from_llm(self.llm)
                self.retrievers['compressed'] = ContextualCompressionRetriever(
                    base_compressor=compressor,
                    base_retriever=self.retrievers['ensemble']
                )
            
            # Embedding filter retriever (if embedding model is available)
            if self.embedding_model and 'ensemble' in self.retrievers:
                embeddings_filter = EmbeddingsFilter(
                    embeddings=self.embedding_model,
                    similarity_threshold=0.7
                )
                self.retrievers['filtered'] = ContextualCompressionRetriever(
                    base_compressor=embeddings_filter,
                    base_retriever=self.retrievers['ensemble']
                )
                
        except Exception as e:
            logger.error(f"Error initializing retrievers: {e}")
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available retrieval strategies."""
        return list(self.retrievers.keys())
    
    def retrieve(
        self,
        query: Query,
        strategy: str = "ensemble",
        top_k: Optional[int] = None,
        **kwargs
    ) -> List[VectorStoreDocument]:
        """
        Retrieve documents using the specified strategy.
        
        Args:
            query: The search query
            strategy: Retrieval strategy to use
            top_k: Number of documents to retrieve
            **kwargs: Additional parameters for the retrieval strategy
            
        Returns:
            List of retrieved documents
            
        Raises:
            RetrievalException: If retrieval fails
        """
        top_k = top_k or config.DEFAULT_TOP_K
        
        if strategy not in self.retrievers:
            available = list(self.retrievers.keys())
            logger.warning(f"Strategy '{strategy}' not available. Using 'ensemble'. Available: {available}")
            strategy = "ensemble" if "ensemble" in self.retrievers else available[0] if available else None
        
        if strategy is None:
            raise RetrievalException("No retrieval strategies available")
        
        try:
            retriever = self.retrievers[strategy]
            
            # Set k parameter if the retriever supports it
            if hasattr(retriever, 'search_kwargs'):
                retriever.search_kwargs['k'] = top_k
            
            # Retrieve documents
            docs = retriever.invoke(query)
            
            # Convert to expected format
            results = []
            for doc in docs[:top_k]:
                result = {
                    "doc_id": doc.metadata.get("doc_id", ""),
                    "text": doc.page_content,
                    "metadata": doc.metadata
                }
                results.append(result)
            
            logger.info(f"Retrieved {len(results)} documents using '{strategy}' strategy")
            return results
            
        except Exception as e:
            logger.error(f"Retrieval failed with strategy '{strategy}': {e}")
            raise RetrievalException(f"Failed to retrieve documents: {str(e)}") from e
    
    def multi_strategy_retrieve(
        self,
        query: Query,
        strategies: List[str],
        top_k: Optional[int] = None,
        merge_method: str = "concatenate"
    ) -> List[VectorStoreDocument]:
        """
        Retrieve documents using multiple strategies and merge results.
        
        Args:
            query: The search query
            strategies: List of retrieval strategies to use
            top_k: Number of documents to retrieve per strategy
            merge_method: How to merge results ('concatenate', 'deduplicate', 'rank_fusion')
            
        Returns:
            List of merged documents
        """
        top_k = top_k or config.DEFAULT_TOP_K
        all_results = []
        
        for strategy in strategies:
            try:
                results = self.retrieve(query, strategy, top_k)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Strategy '{strategy}' failed: {e}")
                continue
        
        # Merge results based on method
        if merge_method == "concatenate":
            return all_results[:top_k]
        elif merge_method == "deduplicate":
            return self._deduplicate_results(all_results)[:top_k]
        elif merge_method == "rank_fusion":
            return self._rank_fusion_merge(all_results, strategies)[:top_k]
        else:
            logger.warning(f"Unknown merge method '{merge_method}', using concatenate")
            return all_results[:top_k]
    
    def _deduplicate_results(self, results: List[VectorStoreDocument]) -> List[VectorStoreDocument]:
        """Remove duplicate documents based on doc_id."""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            doc_id = result.get("doc_id", "")
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(result)
        
        return unique_results
    
    def _rank_fusion_merge(
        self,
        results: List[VectorStoreDocument],
        strategies: List[str]
    ) -> List[VectorStoreDocument]:
        """Merge results using reciprocal rank fusion."""
        # Group results by strategy
        strategy_results = {}
        results_per_strategy = len(results) // len(strategies)
        
        for i, strategy in enumerate(strategies):
            start_idx = i * results_per_strategy
            end_idx = (i + 1) * results_per_strategy
            strategy_results[strategy] = results[start_idx:end_idx]
        
        # Calculate RRF scores
        rrf_scores = {}
        k = config.RRF_K
        
        for strategy, docs in strategy_results.items():
            for rank, doc in enumerate(docs):
                doc_id = doc.get("doc_id", "")
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = {"score": 0, "doc": doc}
                rrf_scores[doc_id]["score"] += 1 / (k + rank + 1)
        
        # Sort by RRF score
        sorted_docs = sorted(
            rrf_scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        return [item["doc"] for item in sorted_docs]
    
    def explain_retrieval(self, query: Query, strategy: str = "ensemble") -> Dict[str, Any]:
        """
        Explain how the retrieval strategy works for the given query.
        
        Args:
            query: The search query
            strategy: Retrieval strategy to explain
            
        Returns:
            Dictionary with explanation details
        """
        explanation = {
            "strategy": strategy,
            "query": query,
            "available_strategies": self.get_available_strategies(),
            "description": self._get_strategy_description(strategy),
            "parameters": self._get_strategy_parameters(strategy)
        }
        
        return explanation
    
    def _get_strategy_description(self, strategy: str) -> str:
        """Get description of a retrieval strategy."""
        descriptions = {
            "vector": "Semantic search using vector embeddings",
            "bm25": "Keyword search using BM25 algorithm",
            "ensemble": "Hybrid search combining vector and BM25",
            "multi_query": "Multiple query variations for better recall",
            "compressed": "Contextual compression to reduce noise",
            "filtered": "Embedding-based filtering for relevance"
        }
        return descriptions.get(strategy, f"Unknown strategy: {strategy}")
    
    def _get_strategy_parameters(self, strategy: str) -> Dict[str, Any]:
        """Get parameters for a retrieval strategy."""
        if strategy in self.retrievers:
            retriever = self.retrievers[strategy]
            params = {}
            
            if hasattr(retriever, 'search_kwargs'):
                params.update(retriever.search_kwargs)
            
            if hasattr(retriever, 'k'):
                params['k'] = retriever.k
                
            return params
        
        return {}


def create_advanced_retriever(
    vector_store,
    llm: Optional[BaseLanguageModel] = None,
    embedding_model=None,
    **kwargs
) -> AdvancedRetriever:
    """
    Create an advanced retriever instance.
    
    Args:
        vector_store: The vector store instance
        llm: Language model for advanced features
        embedding_model: Embedding model for filtering
        **kwargs: Additional configuration options
        
    Returns:
        AdvancedRetriever instance
    """
    return AdvancedRetriever(
        vector_store=vector_store,
        llm=llm,
        embedding_model=embedding_model,
        **kwargs
    )