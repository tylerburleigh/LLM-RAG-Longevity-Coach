# Tenant-Aware Vector Store Implementation

This document describes the implementation of the Tenant-Aware Vector Store for Phase 2.2 of the multi-tenant cloud migration.

## Overview

The Tenant-Aware Vector Store provides complete data isolation between users by creating separate vector stores and file paths for each tenant. This ensures that user data remains private and secure in a multi-tenant environment.

## Architecture

### Key Components

1. **TenantManager** (`coach/tenant.py`) - Manages tenant-specific paths and resources
2. **TenantAwareLangChainVectorStore** (`coach/tenant_aware_vector_store.py`) - Extends the base vector store with tenant awareness
3. **Resource Pooling** (`coach/resource_pool.py`) - Provides efficient caching and memory management
4. **Vector Store Factory** (`coach/vector_store_factory.py`) - Creates appropriate vector store instances

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
    
    def get_vector_store_path(self) -> str:
        return self.get_tenant_path("vector_store")
    
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
    def __init__(self, tenant_manager: TenantManager, config: Config, **kwargs):
        self.tenant_manager = tenant_manager
        self.config = config
        
        # Use tenant-specific vector store path
        store_folder = tenant_manager.get_vector_store_path()
        
        # Initialize parent class with tenant-specific folder
        super().__init__(store_folder=store_folder, **kwargs)
```

Key overridden methods:

- `_get_faiss_index_path()` - Returns tenant-specific FAISS index path
- `_load_existing_store()` - Loads from tenant-specific location
- `save()` - Saves to tenant-specific location

### Resource Pooling

The `LRUResourcePool` class provides efficient memory management:

#### Features

- **LRU Eviction**: Automatically removes least recently used vector stores
- **TTL Support**: Configurable time-to-live for cached resources
- **Thread Safety**: Safe for concurrent access
- **Statistics**: Detailed metrics for monitoring and debugging

#### Configuration

```python
# Default configuration
max_size = 10        # Maximum cached vector stores
ttl_seconds = 3600   # 1 hour time-to-live
```

#### Usage

```python
from coach.resource_pool import get_vector_store_pool

pool = get_vector_store_pool()
stats = pool.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

### Vector Store Factory

The factory function creates appropriate vector store instances:

```python
def create_vector_store(
    tenant_manager: Optional[TenantManager] = None,
    config_instance: Optional[Config] = None,
    use_cache: bool = True,
    **kwargs
) -> Union[LangChainVectorStore, TenantAwareLangChainVectorStore]:
    if tenant_manager:
        if use_cache:
            return get_cached_vector_store(...)
        else:
            return TenantAwareLangChainVectorStore(...)
    else:
        return LangChainVectorStore(...)  # Backwards compatibility
```

## Usage Examples

### Basic Usage

```python
from coach.models import UserContext
from coach.tenant import TenantManager
from coach.vector_store_factory import create_vector_store
from coach.config import config

# Create user context
user = UserContext(
    user_id="user123",
    email="alice@example.com",
    name="Alice",
    oauth_token="token",
    refresh_token="refresh"
)

# Create tenant manager
tenant_manager = TenantManager(user)

# Create tenant-aware vector store
vector_store = create_vector_store(
    tenant_manager=tenant_manager,
    config_instance=config
)

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

### Cached Access

```python
from coach.tenant import get_tenant_manager

# Get cached tenant manager
tenant_manager = get_tenant_manager(
    user_id="user123",
    email="alice@example.com",
    name="Alice",
    oauth_token="token",
    refresh_token="refresh"
)

# Create vector store (will use cache)
vector_store = create_vector_store(tenant_manager=tenant_manager)
```

### Resource Management

```python
from coach.tenant_aware_vector_store import (
    get_cache_stats,
    cleanup_expired_stores,
    clear_vector_store_cache
)

# Get statistics
stats = get_cache_stats()
print(f"Cache size: {stats['size']}/{stats['max_size']}")
print(f"Hit rate: {stats['hit_rate']:.2%}")

# Clean up expired stores
expired_count = cleanup_expired_stores()
print(f"Cleaned up {expired_count} expired stores")

# Clear specific tenant cache
clear_vector_store_cache(tenant_id="user123")

# Clear all caches
clear_vector_store_cache()
```

## Benefits

### Data Isolation

- **Complete Separation**: Each tenant has completely isolated data
- **Path Security**: Tenant paths prevent cross-tenant access
- **File System Isolation**: Separate directories for each tenant

### Performance

- **Resource Pooling**: Efficient memory usage through LRU caching
- **Lazy Loading**: Vector stores loaded only when needed
- **Configurable TTL**: Automatic cleanup of unused resources

### Scalability

- **Concurrent Users**: Thread-safe resource management
- **Memory Efficiency**: Automatic eviction of unused stores
- **Configurable Limits**: Adjustable cache sizes and TTLs

### Compatibility

- **Backwards Compatible**: Existing code continues to work
- **LangChain Integration**: Full compatibility with LangChain ecosystem
- **Drop-in Replacement**: Factory pattern provides seamless migration

## Configuration

### Environment Variables

```bash
# Resource pool configuration
VECTOR_STORE_POOL_SIZE=10        # Maximum cached stores
VECTOR_STORE_TTL_SECONDS=3600    # Cache TTL in seconds

# Vector store configuration
VECTOR_STORE_FOLDER=vector_store_data  # Default folder (ignored for tenants)
EMBEDDING_MODEL=text-embedding-3-large
DEFAULT_TOP_K=5
```

### Programmatic Configuration

```python
from coach.resource_pool import get_vector_store_pool

# Get pool with custom settings
pool = get_vector_store_pool(
    max_size=20,
    ttl_seconds=7200  # 2 hours
)
```

## Monitoring and Debugging

### Cache Statistics

```python
stats = get_cache_stats()
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Evictions: {stats['evictions']}")
print(f"Current size: {stats['size']}")
print(f"Cached tenants: {stats['keys']}")
```

### Logging

The implementation provides detailed logging:

```python
import logging
logging.getLogger("coach.tenant").setLevel(logging.DEBUG)
logging.getLogger("coach.tenant_aware_vector_store").setLevel(logging.DEBUG)
logging.getLogger("coach.resource_pool").setLevel(logging.DEBUG)
```

## Testing

A comprehensive test script is provided at `examples/test_tenant_vector_store.py`:

```bash
cd /path/to/project
python examples/test_tenant_vector_store.py
```

This script demonstrates:

- Tenant isolation
- Resource pooling
- Cache efficiency
- Performance monitoring

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
tenant_manager = get_tenant_manager(user_id, email, name, oauth_token, refresh_token)

# Create tenant-aware vector store
vector_store = create_vector_store(tenant_manager=tenant_manager)
```

## Security Considerations

### Path Validation

- Tenant paths are validated to prevent directory traversal attacks
- Relative paths only within tenant directories
- No access to parent directories or absolute paths

### Data Isolation

- Complete file system isolation between tenants
- No shared data structures between tenant stores
- Encrypted data at rest (when configured)

### Memory Security

- Resource pooling prevents memory leaks
- Automatic cleanup of unused resources
- Configurable limits prevent resource exhaustion

## Future Enhancements

### Planned Features

1. **Database Backend**: Support for database-backed tenant management
2. **Encryption**: Per-tenant encryption keys
3. **Backup/Restore**: Tenant-specific backup mechanisms
4. **Metrics**: Enhanced monitoring and alerting
5. **Multi-Region**: Support for geographically distributed tenants

### Migration Path

The current implementation provides a solid foundation for these enhancements while maintaining backwards compatibility.