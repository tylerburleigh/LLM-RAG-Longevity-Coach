# coach/tenant.py
"""Tenant management for multi-tenant architecture."""

import os
import logging
from typing import Optional

# Import UserContext from models to avoid duplication
from coach.models import UserContext

logger = logging.getLogger(__name__)


class TenantManager:
    """Manages tenant-specific paths and resources."""
    
    def __init__(self, user_context: UserContext):
        """
        Initialize tenant manager.
        
        Args:
            user_context: The authenticated user context
        """
        self.user_context = user_context
        self.tenant_id = user_context.user_id
        self._ensure_tenant_directories()
    
    def _ensure_tenant_directories(self):
        """Ensure all tenant-specific directories exist."""
        directories = [
            self.get_tenant_path(""),
            self.get_vector_store_path(),
            self.get_config_path(),
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created tenant directory: {directory}")
    
    def get_tenant_path(self, path: str) -> str:
        """
        Get tenant-specific path.
        
        Args:
            path: Relative path within tenant directory
            
        Returns:
            Full path with tenant prefix
        """
        return os.path.join("user_data", self.tenant_id, path)
    
    def get_vector_store_path(self) -> str:
        """Get path for tenant's vector store."""
        return self.get_tenant_path("vector_store")
    
    def get_documents_path(self) -> str:
        """Get path for tenant's documents file."""
        return self.get_tenant_path("docs.jsonl")
    
    def get_config_path(self) -> str:
        """Get path for tenant's configuration directory."""
        return self.get_tenant_path("config")
    
    def get_faiss_index_path(self) -> str:
        """Get path for tenant's FAISS index."""
        return os.path.join(self.get_vector_store_path(), "faiss_index")
    
    def get_user_config_path(self) -> str:
        """Get path for user configuration file."""
        return os.path.join(self.get_config_path(), "user_config.json")
    
    def __repr__(self):
        return f"TenantManager(tenant_id={self.tenant_id})"


def get_tenant_manager(user_context: UserContext) -> TenantManager:
    """
    Get a tenant manager for the given user context.
    
    Args:
        user_context: User context with authentication details
        
    Returns:
        TenantManager instance
    """
    return TenantManager(user_context)