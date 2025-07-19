# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Running the Application
```bash
streamlit run app.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup
Create a `.env` file with required API keys. Copy the template and fill in your values:
```bash
cp .env.example .env
```

Then edit `.env` with your actual values:
```
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here  # Optional, for Gemini models

# OAuth2 Configuration (required for multi-tenant mode)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
OAUTH_REDIRECT_URI=http://localhost:8501/

# Development Configuration (optional)
OAUTH_INSECURE_TRANSPORT=true  # Allows HTTP for local development
```

**Note**: The application now operates in multi-tenant mode by default. Each user authenticates via Google OAuth2 and gets their own isolated data environment. For development/testing, you can still use single-tenant mode by bypassing authentication.

Optional configuration environment variables:
```
VECTOR_STORE_FOLDER=vector_store_data
EMBEDDING_MODEL=text-embedding-3-large
DEFAULT_LLM_MODEL=o3
DEFAULT_TOP_K=5
DOCS_FILE=docs.jsonl
USE_LANGCHAIN_CHAINS=false  # Enable advanced workflow chains
```

## High-Level Architecture

This is a RAG-powered longevity coaching application built with Streamlit that provides personalized health advice using hybrid search and LLM integration. The application supports multi-tenant architecture with complete data isolation between users.

## Architecture Overview

The application follows a modular architecture with clear separation of concerns:

### Design Principles
- **Separation of Concerns**: Each module has a single responsibility
- **Multi-Tenant Isolation**: Complete data separation between users with secure tenant management
- **Type Safety**: Comprehensive type hints and Pydantic models throughout
- **Configuration Management**: Centralized, environment-driven configuration
- **Error Handling**: Structured exception hierarchy with informative error messages
- **Extensibility**: Plugin-style architecture for adding new providers and features

### Data Flow
```
User Authentication → Tenant Isolation → User Query → Search Planning → Query Generation → Hybrid Search → Context Retrieval → LLM Processing → Insights Generation
```

### Key Architectural Components
1. **Authentication Layer** (`coach/auth.py`): OAuth2 authentication and user management
2. **Multi-Tenant Layer** (`coach/tenant.py`): Tenant isolation and resource management
3. **Configuration Layer** (`coach/config.py`): Centralized settings management
4. **Data Layer** (`coach/models.py`, `coach/types.py`): Type-safe data structures
5. **Provider Layer** (`coach/llm_providers.py`): Pluggable LLM provider system
6. **Processing Layer** (`coach/longevity_coach.py`, `coach/search.py`): Core business logic
7. **Storage Layer** (`coach/langchain_vector_store.py`): LangChain-powered hybrid search and document storage with tenant isolation
8. **Presentation Layer** (`app.py`, `pages/`): Streamlit UI components with authentication

### Error Handling Strategy
- Custom exception hierarchy for different error types
- Graceful degradation with fallback mechanisms
- Detailed error logging and user-friendly error messages
- Validation at data boundaries (API inputs, configuration, etc.)

### Extensibility Points
- **New LLM Providers**: Implement `LLMProvider` interface
- **New Search Strategies**: Extend search planning and query generation
- **New Document Types**: Add processors in `coach/langchain_document_processor.py`
- **New Prompt Templates**: Add to `coach/prompts/` directory
- **New Storage Backends**: Phase 3 will add cloud storage providers
- **New Authentication Methods**: Extend the authentication system

## Configuration

The application uses environment variables for configuration. All settings have sensible defaults and can be overridden:

### Required Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key_here  # Required for OpenAI models
GOOGLE_API_KEY=your_google_api_key_here  # Optional, for Gemini models

# OAuth2 Configuration (required for multi-tenant authentication)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
OAUTH_REDIRECT_URI=http://localhost:8501/
```

### Optional Configuration Variables
```bash
# Vector Store Configuration (single-tenant legacy, ignored for multi-tenant)
VECTOR_STORE_FOLDER=vector_store_data        # Default: "vector_store_data"
VECTOR_STORE_CACHE_SIZE=5                    # Default: 5 (tenant vector store cache)

# Multi-Tenant Configuration
USER_DATA_ROOT=user_data                     # Default: "user_data" (tenant isolation root)

# Embedding Configuration
EMBEDDING_MODEL=text-embedding-3-large      # Default: "text-embedding-3-large"
EMBEDDING_DIMENSION=3072                     # Default: 3072

# LLM Configuration
DEFAULT_LLM_MODEL=o3                         # Default: "o3"
DEFAULT_TEMPERATURE=1.0                      # Default: 1.0

# Search Configuration
DEFAULT_TOP_K=5                              # Default: 5
RRF_K=60                                     # Default: 60
SEARCH_MULTIPLIER=2                          # Default: 2

# Document Processing (single-tenant legacy, now per-tenant)
DOCS_FILE=docs.jsonl                         # Default: "docs.jsonl" (now per tenant)
MAX_DOCUMENT_LENGTH=10000                    # Default: 10000

# Development Configuration
OAUTH_INSECURE_TRANSPORT=true               # Default: false (allows HTTP for local dev)

# Insight Generation
MAX_INSIGHTS=5                               # Default: 5
MAX_CLARIFYING_QUESTIONS=3                   # Default: 3

# Logging
LOG_LEVEL=INFO                               # Default: "INFO"
```

### Configuration Validation
The application validates configuration on startup and will raise errors for invalid settings:
- Model names must be supported
- Numeric values must be positive
- Required API keys must be present when using specific providers

## Module Documentation

### `coach/config.py`
Centralized configuration management with environment variable support:
- `Config` class with all configuration settings
- `get_api_key()` method for provider-specific API keys
- `validate()` method for configuration validation
- Singleton `config` instance for global access

### `coach/models.py`
Pydantic data models for type safety and validation:
- `Document`: Knowledge base document structure
- `ClarifyingQuestions`: User question clarification
- `Insight`/`Insights`: Generated insights and recommendations
- `SearchStrategy`: Search planning structure
- `DocumentProcessingResult`: Processing status and results

### `coach/types.py`
Type definitions and aliases for better code clarity:
- Type aliases: `DocumentID`, `Query`, `EmbeddingVector`, etc.
- Literal types: `ImportanceLevel`, `ConfidenceLevel`, `ModelName`
- TypedDict classes: `SearchResult`, `MessageDict`, `InsightDict`
- Callback types: `ProgressCallback`

### `coach/exceptions.py`
Custom exception hierarchy for better error handling:
- Base `CoachException` class
- Module-specific exceptions: `VectorStoreException`, `LLMException`, etc.
- Specific error types: `APIKeyMissingException`, `UnsupportedModelException`
- Utility functions for consistent error formatting

### `coach/llm_providers.py`
Factory pattern for LLM provider management:
- Abstract `LLMProvider` base class
- Concrete providers: `OpenAIProvider`, `GoogleProvider`
- `LLMFactory` for creating LLM instances
- Extensible system for adding new providers
- Automatic API key validation

### `coach/prompts/`
Organized prompt templates by functionality:
- `clarifying.py`: Clarifying questions generation
- `insights.py`: Insight and recommendation generation
- `planning.py`: Search strategy planning
- `search.py`: Search query generation
- `document.py`: Document processing and structuring
- `guided_entry.py`: Guided data entry
- `rag.py`: RAG workflow and chain-specific prompts
- `__init__.py`: Centralized prompt exports

## Multi-Tenant Architecture

The application supports complete multi-tenant isolation with user authentication and data separation.

### Tenant Isolation

Each authenticated user gets their own isolated environment:

```
user_data/
├── {user_id_1}/
│   ├── docs.jsonl          # User's documents
│   ├── vector_store/       # User's FAISS indexes
│   │   └── faiss_index/
│   └── config/             # User settings
├── {user_id_2}/
│   └── ...
```

### Authentication Flow

1. **OAuth2 Login**: Users authenticate via Google OAuth2
2. **Session Management**: User context stored in Streamlit session
3. **Tenant Creation**: TenantManager created from UserContext
4. **Resource Isolation**: All operations scoped to tenant

### Key Multi-Tenant Components

1. **TenantManager** (`coach/tenant.py`):
   - Manages tenant-specific paths and directories
   - Ensures data isolation between users
   - Automatic directory creation and cleanup

2. **TenantAwareLangChainVectorStore** (`coach/langchain_vector_store.py`):
   - Extends base vector store with tenant isolation
   - Separate FAISS indexes per tenant
   - No cross-tenant data access

3. **Vector Store Factory** (`coach/vector_store_factory.py`):
   - Creates tenant-aware or standard vector stores
   - Optional LRU caching for performance
   - Factory pattern for backwards compatibility

4. **Tenant-Aware Document Processing** (`coach/langchain_document_processor.py`):
   - PDF processing with tenant isolation
   - Tenant-specific document storage
   - Secure temporary file handling

5. **Authentication System** (`coach/auth.py`):
   - OAuth2 integration with Google
   - Session management and user context
   - Protected route decorators

### Multi-Tenant Usage

```python
# Get authenticated user context
from coach.auth import get_current_user
from coach.tenant import TenantManager
from coach.vector_store_factory import get_vector_store_for_tenant

# Create tenant-aware resources
user_context = get_current_user()
tenant_manager = TenantManager(user_context)
vector_store = get_vector_store_for_tenant(tenant_manager)

# All operations are now tenant-isolated
documents = load_tenant_docs_from_jsonl(tenant_manager)
vector_store.add_documents(documents)
results = vector_store.search("query")  # Only returns user's data
```

### Migration from Single-Tenant

The application maintains backwards compatibility:
- Single-tenant mode: `create_vector_store()` (no tenant_manager)
- Multi-tenant mode: `create_vector_store(tenant_manager=tm)`

### Core Components

1. **Configuration Management** (`coach/config.py`):
   - Centralized configuration with environment variable support
   - Validation and default values for all settings
   - API key management for different providers
   - Streamlined configuration with minimal feature flags

2. **Data Models** (`coach/models.py`):
   - Pydantic models for structured data validation
   - Type-safe document, insight, and suggestion models
   - Consistent data structures throughout the application

3. **LLM Provider System** (`coach/llm_providers.py`):
   - Factory pattern for LLM initialization with LangChain integration
   - Support for OpenAI (o3, o4-mini) and Google Gemini
   - Extensible provider system with automatic callback integration
   - Unified embeddings management through LangChain

4. **Hybrid Search System** (`coach/langchain_vector_store.py`):
   - LangChain FAISS integration with ensemble retrievers
   - Combines BM25 (keyword) and FAISS (semantic) search
   - Advanced retrieval strategies and automatic persistence
   - Multi-strategy retrieval with rank fusion
   - **Multi-tenant support** with `TenantAwareLangChainVectorStore`

5. **Search and Retrieval** (`coach/search.py`):
   - Advanced retrieval strategies using LangChain retrievers
   - Multi-query expansion and contextual compression
   - Strategic search planning with LLM assistance
   - Context retrieval with intelligent deduplication

6. **Document Processing** (`coach/langchain_document_processor.py`):
   - LangChain PDF processing with PyMuPDFLoader
   - Intelligent text splitting and chunking via RecursiveCharacterTextSplitter
   - LLM-powered document structuring with validation
   - Configurable chunking strategies for different document types
   - **Multi-tenant support** with `TenantAwareDocumentProcessor`

7. **Prompt Management** (`coach/prompts/`):
   - Organized prompt templates by functionality
   - Modular prompt system for maintainability
   - Includes RAG-specific prompts for chain workflows
   - Centralized prompt template management

8. **Advanced Retrievers** (`coach/retrievers.py`):
   - Multi-strategy retrieval with LangChain retrievers
   - Contextual compression and embedding filtering
   - Rank fusion for combining multiple retrieval methods
   - Configurable retrieval strategies

9. **Observability & Monitoring** (`coach/callbacks.py`):
   - LangChain callback system for comprehensive monitoring
   - Performance tracking and cost analysis
   - Detailed logging of all LLM and retrieval operations
   - Configurable callback handlers

10. **Workflow Chains** (`coach/chains.py`):
    - Complete RAG workflows using LangChain chains
    - Structured output generation with Pydantic integration
    - Composable chain components for different tasks
    - Advanced workflow orchestration

11. **Longevity Coach** (`coach/longevity_coach.py`):
    - Main orchestration class for insights generation
    - Clarifying questions and insights generation
    - Optional LangChain chains integration
    - Progress tracking and user interaction

12. **Exception Handling** (`coach/exceptions.py`):
    - Custom exception hierarchy for better error handling
    - Structured error reporting and debugging
    - Module-specific exception types including chain execution errors

13. **Type Definitions** (`coach/types.py`):
    - Common type aliases and TypedDict classes
    - Enhanced type safety throughout the codebase
    - Consistent type annotations

14. **Knowledge Base Management**:
    - Primary storage in `docs.jsonl` (JSON Lines format) **per tenant**
    - Multiple ingestion methods: PDF upload, guided entry, direct editing
    - Data structure includes metadata fields for categorization
    - Automatic migration to LangChain vector stores
    - **Tenant isolation**: Each user has separate docs.jsonl file

15. **Multi-Tenant Management** (`coach/tenant.py`, `coach/vector_store_factory.py`):
    - Complete data isolation between users
    - Tenant-specific path management and resource allocation
    - Factory patterns for tenant-aware component creation
    - LRU caching for performance optimization
    - Backwards compatibility with single-tenant mode

### Key Workflows

1. **Authentication & Chat Interface** (`app.py`):
   - User authentication → Tenant setup → User queries → Search planning → Hybrid retrieval → LLM response
   - Real-time progress feedback during processing
   - Session management and user context preservation

2. **Multi-Tenant Data Management** (`pages/`):
   - `1_Knowledge_Base.py`: Direct spreadsheet-like editing **per tenant**
   - `2_Upload_Documents.py`: PDF processing and ingestion **per tenant**
   - `3_Guided_Entry.py`: Conversational data entry **per tenant**
   - All pages require authentication and operate on tenant-specific data

### Important Implementation Details

- **State Management**: Uses Streamlit session state for persistence and user context
- **Multi-Tenant Isolation**: Complete data separation with tenant-specific paths and resources
- **Authentication**: OAuth2 with Google for secure user identification
- **Search Strategy**: Advanced multi-strategy retrieval with LangChain retrievers
- **Data Format**: JSONL with structured fields (category, subcategory, details, source, etc.) **per tenant**
- **Vector Store**: LangChain FAISS integration with ensemble retrievers and automatic persistence **per tenant**
- **Configuration**: Streamlined environment-based configuration with minimal feature flags
- **Error Handling**: Comprehensive exception system with custom error types
- **Type Safety**: Full type annotations and Pydantic models throughout
- **Modular Design**: LangChain-first architecture with clear separation of concerns
- **Observability**: Built-in performance monitoring and cost tracking via callbacks
- **Workflow Orchestration**: Optional LangChain chains for advanced RAG workflows
- **Backwards Compatibility**: Single-tenant mode still supported for development/testing

### Development Notes

- **Architecture**: Uses LangChain ecosystem for maximum compatibility and extensibility
- **Type Safety**: Enhanced with comprehensive type hints and Pydantic models
- **Error Handling**: Robust exception hierarchy with chain execution error handling
- **Configuration**: Centralized and environment-variable driven with streamlined options
- **Extensibility**: LangChain-based modular design allows easy addition of new features
- **Performance**: Built-in monitoring and optimization through LangChain callbacks
- **Maintainability**: Single implementation path eliminates dual system complexity
- **Testing**: No formal testing framework currently implemented
- **Linting**: No linting configuration present
- **User Data**: Stored in `user_data/{user_id}/` directories with complete tenant isolation
- **Fitbit Integration**: Available but not documented in main workflow
- **Cloud Migration**: Phase 3 will add cloud storage and encryption support
- **Multi-Tenant Security**: Comprehensive data isolation with no cross-tenant access possible