#!/usr/bin/env python3
"""
Simple validation script for tenant-aware vector store implementation.

This script validates the core components without requiring streamlit
or other heavy dependencies.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_core_components():
    """Test core tenant-aware components."""
    print("Testing core tenant-aware components...")
    
    try:
        # Test basic imports
        from coach.tenant import TenantManager
        from coach.resource_pool import LRUResourcePool, get_vector_store_pool
        print("✅ Core imports successful")
        
        # Test UserContext import
        try:
            from coach.models import UserContext
            print("✅ UserContext import successful")
        except ImportError as e:
            # Create minimal UserContext if models.py has dependencies
            class UserContext:
                def __init__(self, user_id, email, name, oauth_token="", refresh_token=""):
                    self.user_id = user_id
                    self.email = email
                    self.name = name
                    self.oauth_token = oauth_token
                    self.refresh_token = refresh_token
            print("⚠️  Using minimal UserContext (models.py has dependencies)")
        
        # Test TenantManager
        user = UserContext(
            user_id="test123",
            email="test@example.com",
            name="Test User",
            oauth_token="dummy",
            refresh_token="dummy"
        )
        
        tenant = TenantManager(user)
        print(f"✅ TenantManager created: {tenant}")
        
        # Test path generation
        vector_path = tenant.get_vector_store_path()
        faiss_path = tenant.get_faiss_index_path()
        docs_path = tenant.get_documents_path()
        
        print(f"✅ Vector store path: {vector_path}")
        print(f"✅ FAISS index path: {faiss_path}")
        print(f"✅ Documents path: {docs_path}")
        
        # Verify path isolation
        assert "test123" in vector_path, "Tenant ID not in vector path"
        assert "user_data" in vector_path, "user_data not in vector path"
        print("✅ Path isolation verified")
        
        # Test resource pool
        pool = get_vector_store_pool(max_size=5, ttl_seconds=600)
        stats = pool.get_stats()
        
        print(f"✅ Resource pool created")
        print(f"   - Max size: {stats['max_size']}")
        print(f"   - Current size: {stats['size']}")
        print(f"   - TTL: {stats['ttl_seconds']} seconds")
        
        # Test pool operations
        test_data = "sample_vector_store"
        pool.put("tenant1", test_data)
        retrieved = pool.get("tenant1")
        
        assert retrieved == test_data, "Pool put/get failed"
        print("✅ Resource pool operations working")
        
        # Test LRU eviction
        for i in range(10):  # Exceed max_size of 5
            pool.put(f"tenant_{i}", f"data_{i}")
        
        final_stats = pool.get_stats()
        assert final_stats['size'] <= 5, "LRU eviction not working"
        print("✅ LRU eviction working correctly")
        
        print("\n🎉 All core components validated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_patterns():
    """Test factory and import patterns."""
    print("\nTesting factory patterns...")
    
    try:
        # Test individual component imports
        from coach.tenant_aware_vector_store import get_cached_vector_store
        from coach.vector_store_factory import create_vector_store
        print("✅ Factory imports successful")
        
        # Test that we can import without circular dependencies
        print("✅ No circular import issues detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Factory pattern test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Tenant-Aware Vector Store Implementation Validation")
    print("=" * 60)
    
    success = True
    
    # Test core components
    success &= test_core_components()
    
    # Test factory patterns  
    success &= test_factory_patterns()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL VALIDATION TESTS PASSED!")
        print("\nThe tenant-aware vector store implementation is ready for use.")
    else:
        print("❌ SOME VALIDATION TESTS FAILED!")
        print("\nPlease check the errors above and fix any issues.")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())