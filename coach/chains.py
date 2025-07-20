# coach/chains.py
"""LangChain chains for complex workflows in the longevity coach."""

import logging
from typing import List, Dict, Any, Optional
from langchain.chains import LLMChain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser

from coach.prompts import (
    PLANNING_PROMPT_TEMPLATE,
    SEARCH_QUERIES_PROMPT_TEMPLATE,
    INSIGHTS_PROMPT_TEMPLATE,
    CLARIFYING_QUESTIONS_PROMPT_TEMPLATE,
    COMPLETE_RAG_PROMPT_TEMPLATE,
)
from coach.models import Insights, ClarifyingQuestions
from coach.exceptions import ChainExecutionException
from coach.config import config

logger = logging.getLogger(__name__)


class LongevityCoachChains:
    """Collection of LangChain chains for the longevity coach."""
    
    def __init__(self, llm: BaseLanguageModel):
        """
        Initialize the chain collection.
        
        Args:
            llm: The language model to use for chains
        """
        self.llm = llm
        self.chains = {}
        self._initialize_chains()
        
        logger.info("Initialized LongevityCoachChains")
    
    def _initialize_chains(self):
        """Initialize all the chains."""
        try:
            # Search planning chain
            self.chains['search_planning'] = self._create_search_planning_chain()
            
            # Query generation chain
            self.chains['query_generation'] = self._create_query_generation_chain()
            
            # Insights generation chain
            self.chains['insights_generation'] = self._create_insights_generation_chain()
            
            # Clarifying questions chain
            self.chains['clarifying_questions'] = self._create_clarifying_questions_chain()
            
            # Complete RAG chain
            self.chains['rag_complete'] = self._create_complete_rag_chain()
            
            logger.info(f"Initialized {len(self.chains)} chains")
            
        except Exception as e:
            logger.error(f"Failed to initialize chains: {e}")
            raise ChainExecutionException(f"Chain initialization failed: {str(e)}") from e
    
    def _create_search_planning_chain(self) -> LLMChain:
        """Create search planning chain."""
        prompt = PromptTemplate.from_template(PLANNING_PROMPT_TEMPLATE)
        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_key="search_strategy",
            verbose=True
        )
    
    def _create_query_generation_chain(self) -> LLMChain:
        """Create query generation chain."""
        prompt = PromptTemplate.from_template(SEARCH_QUERIES_PROMPT_TEMPLATE)
        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_key="search_queries",
            verbose=True
        )
    
    def _create_insights_generation_chain(self) -> LLMChain:
        """Create insights generation chain."""
        prompt = PromptTemplate.from_template(INSIGHTS_PROMPT_TEMPLATE)
        
        # Use structured output with Pydantic
        parser = PydanticOutputParser(pydantic_object=Insights)
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        
        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_key="insights",
            verbose=True
        )
        
        # Add parser to chain
        chain = chain | parser
        
        return chain
    
    def _create_clarifying_questions_chain(self) -> LLMChain:
        """Create clarifying questions chain."""
        prompt = PromptTemplate.from_template(CLARIFYING_QUESTIONS_PROMPT_TEMPLATE)
        
        # Use structured output with Pydantic
        parser = PydanticOutputParser(pydantic_object=ClarifyingQuestions)
        prompt = prompt.partial(format_instructions=parser.get_format_instructions())
        
        chain = LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_key="clarifying_questions",
            verbose=True
        )
        
        # Add parser to chain
        chain = chain | parser
        
        return chain
    
    def _create_complete_rag_chain(self):
        """Create a complete RAG chain that combines retrieval and generation."""
        # This is a more complex chain that combines multiple steps
        
        # Create a prompt for the final generation step
        prompt = ChatPromptTemplate.from_template(COMPLETE_RAG_PROMPT_TEMPLATE)
        
        # Create a chain that formats documents
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)
        
        # Create the complete chain
        chain = (
            {
                "context": lambda x: format_docs(x["documents"]),
                "query": RunnablePassthrough()
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        return chain
    
    def run_search_planning(self, query: str) -> str:
        """
        Run the search planning chain.
        
        Args:
            query: User query to plan search for
            
        Returns:
            Search strategy
        """
        try:
            result = self.chains['search_planning'].run(query=query)
            return result
        except Exception as e:
            logger.error(f"Search planning chain failed: {e}")
            raise ChainExecutionException(f"Search planning failed: {str(e)}") from e
    
    def run_query_generation(self, search_strategy: str) -> str:
        """
        Run the query generation chain.
        
        Args:
            search_strategy: Search strategy to generate queries for
            
        Returns:
            Generated search queries (JSON format)
        """
        try:
            result = self.chains['query_generation'].run(search_strategy=search_strategy)
            return result
        except Exception as e:
            logger.error(f"Query generation chain failed: {e}")
            raise ChainExecutionException(f"Query generation failed: {str(e)}") from e
    
    def run_insights_generation(self, context: str, query: str) -> Insights:
        """
        Run the insights generation chain.
        
        Args:
            context: Retrieved context
            query: User query
            
        Returns:
            Structured insights
        """
        try:
            result = self.chains['insights_generation'].run(
                context=context,
                query=query
            )
            return result
        except Exception as e:
            logger.error(f"Insights generation chain failed: {e}")
            raise ChainExecutionException(f"Insights generation failed: {str(e)}") from e
    
    def run_clarifying_questions(self, query: str) -> ClarifyingQuestions:
        """
        Run the clarifying questions chain.
        
        Args:
            query: User query to generate clarifying questions for
            
        Returns:
            Structured clarifying questions
        """
        try:
            result = self.chains['clarifying_questions'].run(query=query)
            return result
        except Exception as e:
            logger.error(f"Clarifying questions chain failed: {e}")
            raise ChainExecutionException(f"Clarifying questions failed: {str(e)}") from e
    
    def run_complete_rag(self, query: str, documents: List[Document]) -> str:
        """
        Run the complete RAG chain.
        
        Args:
            query: User query
            documents: Retrieved documents
            
        Returns:
            Generated response
        """
        try:
            result = self.chains['rag_complete'].invoke({
                "query": query,
                "documents": documents
            })
            return result
        except Exception as e:
            logger.error(f"Complete RAG chain failed: {e}")
            raise ChainExecutionException(f"Complete RAG failed: {str(e)}") from e
    
    def get_available_chains(self) -> List[str]:
        """Get list of available chains."""
        return list(self.chains.keys())
    
    def get_chain(self, name: str):
        """Get a specific chain by name."""
        return self.chains.get(name)


class RAGWorkflow:
    """Complete RAG workflow using LangChain chains."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        vector_store,
        retriever=None,
        use_advanced_retrieval: bool = False
    ):
        """
        Initialize the RAG workflow.
        
        Args:
            llm: Language model to use
            vector_store: Vector store for retrieval
            retriever: Custom retriever (optional)
            use_advanced_retrieval: Whether to use advanced retrieval strategies
        """
        self.llm = llm
        self.vector_store = vector_store
        self.retriever = retriever
        self.use_advanced_retrieval = use_advanced_retrieval
        
        # Initialize chains
        self.chains = LongevityCoachChains(llm)
        
        # Set up retriever
        if not self.retriever:
            if hasattr(vector_store, 'ensemble_retriever') and vector_store.ensemble_retriever:
                self.retriever = vector_store.ensemble_retriever
            elif hasattr(vector_store, 'faiss_store') and vector_store.faiss_store:
                self.retriever = vector_store.faiss_store.as_retriever()
            else:
                logger.warning("No retriever available, will use vector store search method")
        
        logger.info("Initialized RAG workflow")
    
    def execute_full_workflow(
        self,
        query: str,
        generate_clarifying_questions: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the full RAG workflow.
        
        Args:
            query: User query
            generate_clarifying_questions: Whether to generate clarifying questions
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with workflow results
        """
        try:
            results = {}
            
            # Step 1: Search Planning
            logger.info("Step 1: Search Planning")
            search_strategy = self.chains.run_search_planning(query)
            results['search_strategy'] = search_strategy
            
            # Step 2: Query Generation
            logger.info("Step 2: Query Generation")
            search_queries = self.chains.run_query_generation(search_strategy)
            results['search_queries'] = search_queries
            
            # Step 3: Document Retrieval
            logger.info("Step 3: Document Retrieval")
            documents = self._retrieve_documents(query, search_strategy)
            results['retrieved_documents'] = len(documents)
            
            # Step 4: Context Preparation
            context = "\n\n".join(doc.page_content for doc in documents)
            results['context_length'] = len(context)
            
            # Step 5: Insights Generation
            logger.info("Step 5: Insights Generation")
            insights = self.chains.run_insights_generation(context, query)
            results['insights'] = insights
            
            # Step 6: Clarifying Questions (optional)
            if generate_clarifying_questions:
                logger.info("Step 6: Clarifying Questions")
                clarifying_questions = self.chains.run_clarifying_questions(query)
                results['clarifying_questions'] = clarifying_questions
            
            # Step 7: Complete Response
            logger.info("Step 7: Complete Response")
            complete_response = self.chains.run_complete_rag(query, documents)
            results['complete_response'] = complete_response
            
            logger.info("RAG workflow completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"RAG workflow failed: {e}")
            raise ChainExecutionException(f"RAG workflow failed: {str(e)}") from e
    
    def _retrieve_documents(self, query: str, search_strategy: str) -> List[Document]:
        """Retrieve documents using the configured retriever."""
        if self.retriever:
            try:
                docs = self.retriever.get_relevant_documents(query)
                return docs
            except Exception as e:
                logger.warning(f"Retriever failed: {e}, falling back to vector store")
        
        # Fallback to vector store search
        try:
            vector_docs = self.vector_store.search(query, top_k=config.DEFAULT_TOP_K)
            # Convert to LangChain documents
            documents = []
            for doc in vector_docs:
                documents.append(Document(
                    page_content=doc["text"],
                    metadata=doc.get("metadata", {})
                ))
            return documents
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return []


def create_rag_workflow(
    llm: BaseLanguageModel,
    vector_store,
    **kwargs
) -> RAGWorkflow:
    """
    Create a RAG workflow instance.
    
    Args:
        llm: Language model to use
        vector_store: Vector store for retrieval
        **kwargs: Additional parameters
        
    Returns:
        RAGWorkflow instance
    """
    return RAGWorkflow(llm, vector_store, **kwargs)