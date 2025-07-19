#!/usr/bin/env python3
"""
Test script for tenant-aware vector store implementation.
This script tests the implementation without requiring external dependencies.
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock external dependencies
sys.modules['streamlit'] = MagicMock()
sys.modules['langchain_community.vectorstores'] = MagicMock()
sys.modules['langchain_core.documents'] = MagicMock()
sys.modules['langchain_core.embeddings'] = MagicMock()
sys.modules['langchain_community.retrievers'] = MagicMock()
sys.modules['langchain.retrievers'] = MagicMock()
sys.modules['coach.llm_providers'] = MagicMock()
sys.modules['coach.embeddings'] = MagicMock()

def test_tenant_aware_vector_store():
    """Test the tenant-aware vector store implementation."""
    print("Testing Tenant-Aware Vector Store Implementation...")
    
    try:
        # Import the modules we need
        from coach.models import UserContext
        from coach.tenant import TenantManager
        from coach.vector_store_factory import create_vector_store, VectorStoreManager
        
        print("✓ All imports successful")
        
        # Test 1: Create a tenant manager
        user_context = UserContext(
            user_id="test_user_123",
            email="test@example.com", 
            name="Test User"
        )
        tenant_manager = TenantManager(user_context)
        print(f"✓ TenantManager created for tenant: {tenant_manager.tenant_id}")
        
        # Test 2: Test tenant paths
        vector_store_path = tenant_manager.get_vector_store_path()
        faiss_index_path = tenant_manager.get_faiss_index_path()
        documents_path = tenant_manager.get_documents_path()
        
        print(f"✓ Vector store path: {vector_store_path}")
        print(f"✓ FAISS index path: {faiss_index_path}")
        print(f"✓ Documents path: {documents_path}")
        
        # Test 3: Create vector store factory
        manager = VectorStoreManager(max_cache_size=5)
        print("✓ VectorStoreManager created")
        
        # Test 4: Test factory function
        with patch('coach.langchain_vector_store.get_embeddings'):
            with patch('coach.langchain_vector_store.EmbeddingManager'):
                # Test standard vector store creation
                standard_store = create_vector_store()
                print(f"✓ Standard vector store created: {type(standard_store).__name__}")
                
                # Test tenant-aware vector store creation
                tenant_store = create_vector_store(tenant_manager=tenant_manager)
                print(f"✓ Tenant-aware vector store created: {type(tenant_store).__name__}")
                
                # Verify tenant ID
                if hasattr(tenant_store, 'get_tenant_id'):
                    tenant_id = tenant_store.get_tenant_id()
                    print(f"✓ Tenant ID verified: {tenant_id}")
                    assert tenant_id == "test_user_123", f"Expected 'test_user_123', got '{tenant_id}'"
        
        # Test 5: Test cache functionality
        cache_stats = manager.get_cache_stats()
        print(f"✓ Cache stats: {cache_stats}")
        
        print("\n🎉 All tests passed! Tenant-aware vector store implementation is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tenant_isolation():
    """Test that different tenants have isolated paths."""
    print("\nTesting Tenant Isolation...")
    
    try:
        from coach.models import UserContext
        from coach.tenant import TenantManager
        
        # Create two different tenants
        tenant1 = TenantManager(UserContext(
            user_id="user_1",
            email="user1@example.com",
            name="User One"
        ))
        
        tenant2 = TenantManager(UserContext(
            user_id="user_2", 
            email="user2@example.com",
            name="User Two"
        ))
        
        # Verify they have different paths
        path1 = tenant1.get_vector_store_path()
        path2 = tenant2.get_vector_store_path()
        
        assert path1 != path2, "Tenants should have different vector store paths"
        assert "user_1" in path1, "Tenant 1 path should contain user_1"
        assert "user_2" in path2, "Tenant 2 path should contain user_2"
        
        print(f"✓ Tenant 1 path: {path1}")
        print(f"✓ Tenant 2 path: {path2}")
        print("✓ Tenant isolation verified")
        
        return True
        
    except Exception as e:
        print(f"❌ Tenant isolation test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TENANT-AWARE VECTOR STORE IMPLEMENTATION TEST")
    print("=" * 60)
    
    test1_passed = test_tenant_aware_vector_store()
    test2_passed = test_tenant_isolation()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED! Implementation is ready.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please review the implementation.")
        sys.exit(1)