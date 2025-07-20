# Tenant-Aware Vector Store Implementation

This document describes the implementation of the Tenant-Aware Vector Store for Phase 2.2 of the multi-tenant cloud migration.

## Overview

The Tenant-Aware Vector Store provides complete data isolation between users by creating separate vector stores and file paths for each tenant. This ensures that user data remains private and secure in a multi-tenant environment.

## Architecture

### Key Components

1. **TenantManager** (`coach/tenant.py`) - Manages tenant-specific paths and resources
2. **TenantAwareLangChainVectorStore** (`coach/langchain_vector_store.py`) - Extends the base vector store with tenant awareness
3. **Vector Store Factory** (`coach/vector_store_factory.py`) - Creates appropriate vector store instances with optional caching
4. **Tenant-Aware Document Processing** (`coach/langchain_document_processor.py`) - Document processing with tenant isolation

### Class Hierarchy

```
LangChainVectorStore
    └── TenantAwareLangChainVectorStore
```

The `TenantAwareLangChainVectorStore` inherits all functionality from the base `LangChainVectorStore` while adding tenant-specific path management.

## Implementation Details

### TenantManager

The `TenantManager` class handles tenant-specific path management:

```python
class TenantManager:
    def __init__(self, user_context: UserContext):
        self.user_context = user_context
        self.tenant_id = user_context.user_id
        self._ensure_tenant_directories()
    
    def get_tenant_path(self, path: str) -> str:
        return os.path.join("user_data", self.tenant_id, path)
    
    def get_vector_store_path(self) -> str:
        return self.get_tenant_path("vector_store")
    
    def get_documents_path(self) -> str:
        return self.get_tenant_path("docs.jsonl")
    
    def get_faiss_index_path(self) -> str:
        return os.path.join(self.get_vector_store_path(), "faiss_index")
```

### Directory Structure

Each tenant gets their own isolated directory structure:

```
user_data/
├── {user_id_1}/
│   ├── docs.jsonl
│   ├── vector_store/
│   │   └── faiss_index/
│   │       ├── index.faiss
│   │       └── index.pkl
│   └── config/
│       └── user_config.json
├── {user_id_2}/
│   ├── docs.jsonl
│   ├── vector_store/
│   │   └── faiss_index/
│   └── config/
└── ...
```

### TenantAwareLangChainVectorStore

The tenant-aware vector store extends the base class:

```python
class TenantAwareLangChainVectorStore(LangChainVectorStore):
    def __init__(
        self,
        tenant_manager: "TenantManager",
        embedding_provider: str = "openai",
        embedding_model: Optional[str] = None,
        **kwargs
    ):
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
```

Key overridden methods:

- `_get_faiss_index_path()` - Returns tenant-specific FAISS index path
- `_load_existing_store()` - Loads from tenant-specific location
- `save()` - Saves to tenant-specific location
- `get_tenant_id()` - Returns the tenant ID for this vector store

### Vector Store Factory

The factory provides multiple functions for creating vector store instances:

```python
def create_vector_store(
    tenant_manager: Optional["TenantManager"] = None,
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    **kwargs
) -> LangChainVectorStore:
    """Factory function to create appropriate vector store instance."""
    
def get_vector_store_for_tenant(
    tenant_manager: "TenantManager", 
    use_cache: bool = True
) -> TenantAwareLangChainVectorStore:
    """Get a vector store instance for a specific tenant."""

@lru_cache(maxsize=5)
def create_cached_vector_store(
    tenant_id: str,
    embedding_provider: str = "openai",
    embedding_model: Optional[str] = None,
    **kwargs
) -> TenantAwareLangChainVectorStore:
    """Create a cached tenant-aware vector store."""
```

## Usage Examples

### Basic Usage

```python
from coach.models import UserContext
from coach.tenant import TenantManager, get_tenant_manager
from coach.vector_store_factory import create_vector_store

# Create user context
user_context = UserContext(
    user_id="user123",
    email="alice@example.com",
    name="Alice",
    oauth_token="token",
    refresh_token="refresh"
)

# Create tenant manager
tenant_manager = TenantManager(user_context)
# Or use the helper function
tenant_manager = get_tenant_manager(user_context)

# Create tenant-aware vector store
vector_store = create_vector_store(tenant_manager=tenant_manager)

# Add documents (isolated to this tenant)
docs = [
    {
        "doc_id": "doc1",
        "text": "Sample document content",
        "metadata": {"category": "health"}
    }
]
vector_store.add_documents(docs)

# Search (only returns this tenant's documents)
results = vector_store.search("health advice", top_k=5)
```

### Using the Tenant-Specific Factory

```python
from coach.vector_store_factory import get_vector_store_for_tenant

# Create vector store with caching (default)
vector_store = get_vector_store_for_tenant(tenant_manager)

# Create vector store without caching
vector_store = get_vector_store_for_tenant(tenant_manager, use_cache=False)
```

### Cache Management

```python
from coach.vector_store_factory import clear_vector_store_cache, get_cache_info

# Get cache statistics
cache_info = get_cache_info()
print(f"Cache hits: {cache_info['hits']}")
print(f"Cache misses: {cache_info['misses']}")
print(f"Cache size: {cache_info['currsize']}/{cache_info['maxsize']}")

# Clear the cache
clear_vector_store_cache()
```

### Document Processing

```python
from coach.langchain_document_processor import TenantAwareDocumentProcessor, get_document_processor

# Create tenant-aware document processor
processor = TenantAwareDocumentProcessor(tenant_manager)

# Or use the factory function
processor = get_document_processor(tenant_manager=tenant_manager)

# Process PDF with tenant isolation
with open("document.pdf", "rb") as pdf_file:
    documents = processor.extract_text_from_pdf_stream(
        pdf_stream=pdf_file,
        filename="document.pdf"
    )
    
# Save to tenant-specific location
processor.save_documents(documents)
```

### Utilities for Tenant Data

```python
from coach.utils import (
    load_tenant_docs_from_jsonl,
    save_tenant_docs_to_jsonl,
    append_tenant_doc_to_jsonl,
    initialize_tenant_coach
)

# Load tenant documents
docs = load_tenant_docs_from_jsonl(tenant_manager)

# Save tenant documents
save_tenant_docs_to_jsonl(tenant_manager, docs)

# Add single document
new_doc = {"doc_id": "new1", "text": "New content", "metadata": {}}
append_tenant_doc_to_jsonl(tenant_manager, new_doc)

# Initialize complete tenant coach with vector store
coach = initialize_tenant_coach(tenant_manager)
```

## Benefits

### Data Isolation

- **Complete Separation**: Each tenant has completely isolated data
- **Path Security**: Tenant paths prevent cross-tenant access
- **File System Isolation**: Separate directories for each tenant
- **No Data Leakage**: Vector stores are completely separate per tenant

### Performance

- **LRU Caching**: Efficient memory usage through optional caching
- **Lazy Loading**: Vector stores loaded only when needed
- **Hybrid Search**: Full semantic and keyword search capabilities per tenant

### Scalability

- **Concurrent Users**: Thread-safe resource management
- **Memory Efficiency**: Optional caching with automatic cleanup
- **Configurable Limits**: Adjustable cache sizes

### Compatibility

- **Backwards Compatible**: Existing code continues to work
- **LangChain Integration**: Full compatibility with LangChain ecosystem
- **Drop-in Replacement**: Factory pattern provides seamless migration

## Configuration

### Environment Variables

```bash
# Vector store configuration
VECTOR_STORE_FOLDER=vector_store_data  # Default folder (ignored for tenants)
EMBEDDING_MODEL=text-embedding-3-large
DEFAULT_TOP_K=5

# Cache configuration (optional)
VECTOR_STORE_CACHE_SIZE=5  # Maximum cached stores
```

### Directory Configuration

The tenant manager automatically creates the required directory structure:

```python
tenant_manager = TenantManager(user_context)
# Automatically creates:
# - user_data/{user_id}/
# - user_data/{user_id}/vector_store/
# - user_data/{user_id}/config/
```

## Integration Points

### Main Application

```python
# In app.py or main application file
from coach.auth import get_current_user
from coach.tenant import get_tenant_manager
from coach.vector_store_factory import get_vector_store_for_tenant

def get_user_vector_store():
    user_context = get_current_user()  # From authentication system
    tenant_manager = get_tenant_manager(user_context)
    return get_vector_store_for_tenant(tenant_manager)
```

### Page Components

```python
# In pages/1_Knowledge_Base.py
@require_authentication
def show_knowledge_base():
    user_context = session_manager.get_user_context()
    tenant_manager = TenantManager(user_context)
    
    # Load user-specific documents
    documents = load_tenant_docs_from_jsonl(tenant_manager)
    
    # Display tenant-specific data...
```

## Migration from Single-Tenant

Existing code can be migrated gradually:

### Before (Single-Tenant)

```python
from coach.vector_store_factory import create_vector_store

vector_store = create_vector_store()
```

### After (Multi-Tenant)

```python
from coach.vector_store_factory import create_vector_store
from coach.tenant import get_tenant_manager

# Get tenant manager from authenticated user
tenant_manager = get_tenant_manager(user_context)

# Create tenant-aware vector store
vector_store = create_vector_store(tenant_manager=tenant_manager)
```

## Security Considerations

### Path Validation

- Tenant paths are automatically scoped to prevent directory traversal
- All paths are relative within tenant directories
- No access to parent directories or other tenant data

### Data Isolation

- Complete file system isolation between tenants
- No shared data structures between tenant stores
- Separate FAISS indexes and document storage

### Memory Security

- Optional caching prevents memory leaks
- Automatic cleanup of unused resources
- Type-safe implementations with proper error handling

## Monitoring and Debugging

### Logging

The implementation provides detailed logging at the DEBUG level:

```python
import logging
logging.getLogger("coach.tenant").setLevel(logging.DEBUG)
logging.getLogger("coach.langchain_vector_store").setLevel(logging.DEBUG)
logging.getLogger("coach.vector_store_factory").setLevel(logging.DEBUG)
```

### Cache Monitoring

```python
from coach.vector_store_factory import get_cache_info

cache_info = get_cache_info()
print(f"Cache efficiency: {cache_info['hits']}/{cache_info['hits'] + cache_info['misses']}")
```

## Testing

To test the tenant isolation:

```python
# Create two different tenants
user1 = UserContext(user_id="user1", email="user1@test.com", name="User 1", oauth_token="token1", refresh_token="refresh1")
user2 = UserContext(user_id="user2", email="user2@test.com", name="User 2", oauth_token="token2", refresh_token="refresh2")

tenant1 = TenantManager(user1)
tenant2 = TenantManager(user2)

store1 = create_vector_store(tenant_manager=tenant1)
store2 = create_vector_store(tenant_manager=tenant2)

# Add different documents to each
store1.add_documents([{"doc_id": "doc1", "text": "User 1 data", "metadata": {}}])
store2.add_documents([{"doc_id": "doc2", "text": "User 2 data", "metadata": {}}])

# Verify isolation
results1 = store1.search("data", top_k=10)
results2 = store2.search("data", top_k=10)

# Each should only return their own data
assert len(results1) == 1 and "User 1" in results1[0]["text"]
assert len(results2) == 1 and "User 2" in results2[0]["text"]
```

## Future Enhancements

### Planned Features

1. **Cloud Storage Integration**: Phase 3 will add cloud storage backends
2. **Encryption**: Per-tenant encryption keys and secure storage
3. **Backup/Restore**: Tenant-specific backup mechanisms
4. **Enhanced Monitoring**: Detailed metrics and alerting
5. **Performance Optimization**: Advanced caching strategies

### Migration Path

The current implementation provides a solid foundation for these enhancements while maintaining backwards compatibility and clean separation of concerns.