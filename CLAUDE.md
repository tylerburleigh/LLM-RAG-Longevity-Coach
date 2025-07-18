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
Create a `.env` file with required API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here  # Optional, for Gemini models
```

Optional configuration environment variables:
```
VECTOR_STORE_FOLDER=vector_store_data
EMBEDDING_MODEL=text-embedding-3-large
DEFAULT_LLM_MODEL=o3
DEFAULT_TOP_K=5
DOCS_FILE=docs.jsonl
```

## High-Level Architecture

This is a RAG-powered longevity coaching application built with Streamlit that provides personalized health advice using hybrid search and LLM integration.

## Architecture Overview

The application follows a modular architecture with clear separation of concerns:

### Design Principles
- **Separation of Concerns**: Each module has a single responsibility
- **Type Safety**: Comprehensive type hints and Pydantic models throughout
- **Configuration Management**: Centralized, environment-driven configuration
- **Error Handling**: Structured exception hierarchy with informative error messages
- **Extensibility**: Plugin-style architecture for adding new providers and features

### Data Flow
```
User Query → Search Planning → Query Generation → Hybrid Search → Context Retrieval → LLM Processing → Insights Generation
```

### Key Architectural Components
1. **Configuration Layer** (`coach/config.py`): Centralized settings management
2. **Data Layer** (`coach/models.py`, `coach/types.py`): Type-safe data structures
3. **Provider Layer** (`coach/llm_providers.py`): Pluggable LLM provider system
4. **Processing Layer** (`coach/longevity_coach.py`, `coach/search.py`): Core business logic
5. **Storage Layer** (`coach/vector_store.py`): Hybrid search and document storage
6. **Presentation Layer** (`app.py`, `pages/`): Streamlit UI components

### Error Handling Strategy
- Custom exception hierarchy for different error types
- Graceful degradation with fallback mechanisms
- Detailed error logging and user-friendly error messages
- Validation at data boundaries (API inputs, configuration, etc.)

### Extensibility Points
- **New LLM Providers**: Implement `LLMProvider` interface
- **New Search Strategies**: Extend search planning and query generation
- **New Document Types**: Add processors in `coach/document_processor.py`
- **New Prompt Templates**: Add to `coach/prompts/` directory

## Configuration

The application uses environment variables for configuration. All settings have sensible defaults and can be overridden:

### Required Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key_here  # Required for OpenAI models
GOOGLE_API_KEY=your_google_api_key_here  # Optional, for Gemini models
```

### Optional Configuration Variables
```bash
# Vector Store Configuration
VECTOR_STORE_FOLDER=vector_store_data        # Default: "vector_store_data"
FAISS_INDEX_FILENAME=faiss_index.bin         # Default: "faiss_index.bin"
DOCUMENTS_FILENAME=documents.pkl             # Default: "documents.pkl"

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

# Document Processing
DOCS_FILE=docs.jsonl                         # Default: "docs.jsonl"
MAX_DOCUMENT_LENGTH=10000                    # Default: 10000

# Insight Generation
MAX_INSIGHTS=5                               # Default: 5
MAX_CLARIFYING_QUESTIONS=3                   # Default: 3
MAX_FINE_TUNE_SUGGESTIONS=3                  # Default: 3

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
- `FineTuneSuggestion`/`FineTuneSuggestions`: Data collection suggestions
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
- `fine_tune.py`: Fine-tune suggestions
- `document.py`: Document processing and structuring
- `guided_entry.py`: Guided data entry
- `__init__.py`: Backward compatibility imports

### Core Components

1. **Configuration Management** (`coach/config.py`):
   - Centralized configuration with environment variable support
   - Validation and default values for all settings
   - API key management for different providers

2. **Data Models** (`coach/models.py`):
   - Pydantic models for structured data validation
   - Type-safe document, insight, and suggestion models
   - Consistent data structures throughout the application

3. **LLM Provider System** (`coach/llm_providers.py`):
   - Factory pattern for LLM initialization
   - Support for OpenAI (o3, o4-mini) and Google Gemini
   - Extensible provider system for easy model additions

4. **Hybrid Search System** (`coach/vector_store.py`):
   - Combines BM25 (keyword) and FAISS (semantic) search
   - Configurable storage locations and parameters
   - Improved error handling and type safety

5. **Search and Retrieval** (`coach/search.py`):
   - Strategic search planning with LLM assistance
   - Multi-category query generation
   - Context retrieval with deduplication

6. **Document Processing** (`coach/document_processor.py`):
   - PDF text extraction with error handling
   - LLM-powered document structuring
   - Conversion to typed Document models

7. **Prompt Management** (`coach/prompts/`):
   - Organized prompt templates by functionality
   - Modular prompt system for maintainability
   - Version-controlled prompt templates

8. **Longevity Coach** (`coach/longevity_coach.py`):
   - Main orchestration class for insights generation
   - Clarifying questions and fine-tune suggestions
   - Progress tracking and user interaction

9. **Exception Handling** (`coach/exceptions.py`):
   - Custom exception hierarchy for better error handling
   - Structured error reporting and debugging
   - Module-specific exception types

10. **Type Definitions** (`coach/types.py`):
    - Common type aliases and TypedDict classes
    - Enhanced type safety throughout the codebase
    - Consistent type annotations

11. **Knowledge Base Management**:
    - Primary storage in `docs.jsonl` (JSON Lines format)
    - Multiple ingestion methods: PDF upload, guided entry, direct editing
    - Data structure includes metadata fields for categorization

### Key Workflows

1. **Chat Interface** (`app.py`):
   - User queries → Search planning → Hybrid retrieval → LLM response
   - Real-time progress feedback during processing

2. **Data Management** (`pages/`):
   - `1_Knowledge_Base.py`: Direct spreadsheet-like editing
   - `2_Upload_Documents.py`: PDF processing and ingestion
   - `2_Guided_Entry.py` & `3_Guided_Entry.py`: Conversational data entry

### Important Implementation Details

- **State Management**: Uses Streamlit session state for persistence
- **Search Strategy**: Generates multiple search queries for comprehensive retrieval
- **Data Format**: JSONL with structured fields (category, subcategory, details, source, etc.)
- **Vector Store**: Persisted FAISS index with document metadata in pickle format
- **Configuration**: Environment-based configuration with validation
- **Error Handling**: Comprehensive exception system with custom error types
- **Type Safety**: Full type annotations and Pydantic models
- **Modular Design**: Separated concerns with clear module boundaries

### Development Notes

- **Architecture**: Refactored for better maintainability and separation of concerns
- **Type Safety**: Enhanced with comprehensive type hints and Pydantic models
- **Error Handling**: Improved with custom exception hierarchy
- **Configuration**: Centralized and environment-variable driven
- **Extensibility**: Modular design allows easy addition of new features
- **Testing**: No formal testing framework currently implemented
- **Linting**: No linting configuration present
- **User Data**: Stored in `user_data/` directory
- **Fitbit Integration**: Available but not documented in main workflow