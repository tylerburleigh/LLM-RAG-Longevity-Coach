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
]