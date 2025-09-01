#!/usr/bin/env python3
"""Simple test for the enhanced search system."""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from coach.search import plan_search, generate_hybrid_queries
from coach.llm_providers import get_llm
from coach.config import config


def main():
    """Run a simple test of the enhanced search system."""
    
    # Initialize LLM
    llm = get_llm(config.DEFAULT_LLM_MODEL)
    
    # Simple test query
    query = "What supplements help with sleep?"
    
    print("=" * 60)
    print("TESTING ENHANCED SEARCH SYSTEM")
    print("=" * 60)
    print(f"\n📝 Query: '{query}'")
    print("\n🔍 Generating search strategy...")
    
    try:
        # Generate search strategy using simple prompt
        search_strategy = plan_search(
            query=query,
            llm=llm,
            user_data=None,
            use_simple=True  # Use simpler prompt for faster response
        )
        
        print("\n✅ Search Strategy Generated!")
        print(f"   Intent: {search_strategy.query_intent or 'Not specified'}")
        print(f"   Categories: {len(search_strategy.search_plan)}")
        
        # Show categories
        for cat in search_strategy.search_plan:
            print(f"\n   📂 {cat.category}")
            print(f"      Keywords: {len(cat.keywords)} terms")
            if cat.keywords:
                print(f"      Sample: {', '.join(cat.keywords[:3])}")
            print(f"      Weight: {cat.weight}")
        
        # Generate queries
        keyword_queries, semantic_queries = generate_hybrid_queries(search_strategy)
        print(f"\n🔗 Generated Queries:")
        print(f"   Keywords: {len(keyword_queries)}")
        print(f"   Semantic: {len(semantic_queries)}")
        
        print("\n✅ TEST PASSED - System is working!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Check API keys
    if not config.get_api_key("openai") and not config.get_api_key("google"):
        print("❌ Error: No API keys configured")
        sys.exit(1)
    
    main()