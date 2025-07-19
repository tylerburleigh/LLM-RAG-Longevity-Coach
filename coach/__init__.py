"""Coach package initialization."""

from .auth import (
    AuthenticationManager,
    AuthenticationException,
    AuthorizationException,
    auth_manager,
    require_authentication,
    require_role,
    with_rate_limiting,
    audit_access,
    protected_page,
)
from .config import config
from .exceptions import CoachException
from .models import UserContext, Document, Insight, Insights, ClarifyingQuestions
from .types import (
    DocumentID,
    Query,
    ImportanceLevel,
    ConfidenceLevel,
    ModelName,
    SearchResult,
    MessageDict,
    InsightDict,
)
from .tenant import TenantManager, get_tenant_manager
from .langchain_vector_store import TenantAwareLangChainVectorStore
from .vector_store_factory import (
    create_vector_store,
    get_vector_store,
    clear_vector_store_cache,
    get_vector_store_cache_stats,
    VectorStoreManager,
)
# Legacy imports for backward compatibility
from .tenant_aware_vector_store import (
    get_cached_vector_store,
    get_cache_stats,
    cleanup_expired_stores,
)

__all__ = [
    # Authentication
    "AuthenticationManager",
    "AuthenticationException",
    "AuthorizationException",
    "auth_manager",
    "require_authentication",
    "require_role",
    "with_rate_limiting",
    "audit_access",
    "protected_page",
    # Configuration
    "config",
    # Exceptions
    "CoachException",
    # Models
    "UserContext",
    "Document",
    "Insight",
    "Insights",
    "ClarifyingQuestions",
    # Types
    "DocumentID",
    "Query",
    "ImportanceLevel",
    "ConfidenceLevel",
    "ModelName",
    "SearchResult",
    "MessageDict",
    "InsightDict",
    # Multi-tenant support
    "TenantManager",
    "get_tenant_manager",
    "TenantAwareLangChainVectorStore",
    "create_vector_store",
    "get_vector_store",
    "clear_vector_store_cache",
    "get_vector_store_cache_stats",
    "VectorStoreManager",
    # Legacy exports for backward compatibility
    "get_cached_vector_store",
    "get_cache_stats",
    "cleanup_expired_stores",
]