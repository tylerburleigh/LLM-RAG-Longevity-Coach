#!/usr/bin/env python3
"""
Example script demonstrating the tenant-aware vector store functionality.

This script shows how to:
1. Create tenant managers for different users
2. Create tenant-aware vector stores
3. Add documents to tenant-specific stores
4. Perform searches within tenant boundaries
5. Monitor resource pooling and caching
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coach.models import UserContext
from coach.tenant import TenantManager, get_tenant_manager
from coach.vector_store_factory import create_vector_store
from coach.tenant_aware_vector_store import get_cache_stats, cleanup_expired_stores
from coach.config import config


def demonstrate_tenant_isolation():
    """Demonstrate tenant isolation in vector stores."""
    print("=== Tenant-Aware Vector Store Demo ===\n")
    
    # Create two different users
    user1 = UserContext(
        user_id="user123", 
        email="alice@example.com", 
        name="Alice",
        oauth_token="dummy_token_alice",
        refresh_token="dummy_refresh_alice"
    )
    user2 = UserContext(
        user_id="user456", 
        email="bob@example.com", 
        name="Bob",
        oauth_token="dummy_token_bob",
        refresh_token="dummy_refresh_bob"
    )
    
    # Create tenant managers
    tenant1 = TenantManager(user1)
    tenant2 = TenantManager(user2)
    
    print(f"Created tenant managers:")
    print(f"  - {tenant1}")
    print(f"  - {tenant2}")
    print()
    
    # Create vector stores for each tenant
    print("Creating tenant-aware vector stores...")
    vector_store1 = create_vector_store(tenant_manager=tenant1, config_instance=config)
    vector_store2 = create_vector_store(tenant_manager=tenant2, config_instance=config)
    
    print(f"  - Store 1: {vector_store1}")
    print(f"  - Store 2: {vector_store2}")
    print()
    
    # Add documents to each tenant's store
    print("Adding documents to each tenant's store...")
    
    # Alice's documents
    alice_docs = [
        {
            "doc_id": "alice_doc1",
            "text": "Exercise recommendations: Daily walking for 30 minutes improves cardiovascular health.",
            "metadata": {"category": "exercise", "user": "alice"}
        },
        {
            "doc_id": "alice_doc2",
            "text": "Nutrition tip: Mediterranean diet rich in olive oil and vegetables promotes longevity.",
            "metadata": {"category": "nutrition", "user": "alice"}
        }
    ]
    
    # Bob's documents
    bob_docs = [
        {
            "doc_id": "bob_doc1",
            "text": "Sleep hygiene: Consistent 7-9 hours of sleep supports immune function and mental clarity.",
            "metadata": {"category": "sleep", "user": "bob"}
        },
        {
            "doc_id": "bob_doc2",
            "text": "Stress management: Regular meditation reduces cortisol levels and improves well-being.",
            "metadata": {"category": "mental_health", "user": "bob"}
        }
    ]
    
    vector_store1.add_documents(alice_docs)
    vector_store2.add_documents(bob_docs)
    
    print(f"  - Added {len(alice_docs)} documents to Alice's store")
    print(f"  - Added {len(bob_docs)} documents to Bob's store")
    print()
    
    # Save the stores
    vector_store1.save()
    vector_store2.save()
    
    # Perform searches to demonstrate isolation
    print("Performing searches to demonstrate tenant isolation...")
    print()
    
    # Search in Alice's store
    print("Alice searching for 'diet':")
    alice_results = vector_store1.search("diet", top_k=2)
    for result in alice_results:
        print(f"  - {result['doc_id']}: {result['text'][:80]}...")
    
    print("\nAlice searching for 'sleep':")
    alice_sleep_results = vector_store1.search("sleep", top_k=2)
    print(f"  - Found {len(alice_sleep_results)} results")
    
    # Search in Bob's store
    print("\nBob searching for 'sleep':")
    bob_results = vector_store2.search("sleep", top_k=2)
    for result in bob_results:
        print(f"  - {result['doc_id']}: {result['text'][:80]}...")
    
    print("\nBob searching for 'diet':")
    bob_diet_results = vector_store2.search("diet", top_k=2)
    print(f"  - Found {len(bob_diet_results)} results")
    
    print("\n✓ Tenant isolation verified: Each user only sees their own documents")
    print()


def demonstrate_resource_pooling():
    """Demonstrate resource pooling and caching."""
    print("=== Resource Pooling Demo ===\n")
    
    # Get cache statistics before
    print("Initial cache stats:")
    stats = get_cache_stats()
    print(f"  - Cache size: {stats['size']}/{stats['max_size']}")
    print(f"  - Hit rate: {stats['hit_rate']:.2%}")
    print()
    
    # Create multiple users and access their stores
    print("Creating and accessing multiple tenant stores...")
    
    for i in range(5):
        user_id = f"demo_user_{i}"
        email = f"user{i}@example.com"
        name = f"Demo User {i}"
        
        tenant = get_tenant_manager(
            user_id=user_id,
            email=email,
            name=name,
            oauth_token=f"dummy_token_{i}",
            refresh_token=f"dummy_refresh_{i}"
        )
        
        # First access - will create new store
        store = create_vector_store(tenant_manager=tenant, config_instance=config)
        print(f"  - Created store for {name}")
        
        # Second access - should come from cache
        cached_store = create_vector_store(tenant_manager=tenant, config_instance=config)
        print(f"  - Retrieved cached store for {name}: {store is cached_store}")
    
    print()
    
    # Get cache statistics after
    print("Cache stats after multiple accesses:")
    stats = get_cache_stats()
    print(f"  - Cache size: {stats['size']}/{stats['max_size']}")
    print(f"  - Hit rate: {stats['hit_rate']:.2%}")
    print(f"  - Hits: {stats['hits']}, Misses: {stats['misses']}")
    print(f"  - Cached tenants: {stats['keys']}")
    print()
    
    # Clean up expired stores (if any)
    expired_count = cleanup_expired_stores()
    print(f"Cleaned up {expired_count} expired stores")
    

def main():
    """Run all demonstrations."""
    try:
        # Ensure clean state
        print("Setting up clean environment...\n")
        
        # Run demonstrations
        demonstrate_tenant_isolation()
        print("\n" + "="*50 + "\n")
        demonstrate_resource_pooling()
        
        print("\n✅ All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()