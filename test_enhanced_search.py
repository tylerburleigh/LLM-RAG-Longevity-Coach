#!/usr/bin/env python3
"""Test script for the enhanced search planning system."""

import json
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from coach.search import plan_search, generate_hybrid_queries, build_user_context
from coach.llm_providers import get_llm
from coach.config import config


def test_search_planning():
    """Test the enhanced search planning with various queries."""
    
    # Initialize LLM
    llm = get_llm(config.DEFAULT_LLM_MODEL)
    
    # Test queries
    test_queries = [
        {
            "query": "What should my ApoB levels be?",
            "user_data": None,
            "description": "Specific biomarker query"
        },
        {
            "query": "How can I improve my VO2 max?",
            "user_data": {
                "age": 35,
                "sex": "male",
                "goals": ["improve cardiovascular fitness", "increase endurance"]
            },
            "description": "Lifestyle optimization with user context"
        },
        {
            "query": "Is NMN worth taking for longevity?",
            "user_data": None,
            "description": "Supplement research query"
        },
        {
            "query": "I'm 55 with pre-diabetes, what should I focus on?",
            "user_data": {
                "age": 55,
                "conditions": ["pre-diabetes"],
                "recent_labs": {
                    "HbA1c": "6.2%",
                    "fasting_glucose": "115 mg/dL"
                }
            },
            "description": "Personalized query with health conditions"
        },
        {
            "query": "How do genetics, sleep, and exercise interact for longevity?",
            "user_data": None,
            "description": "Complex multi-domain query"
        }
    ]
    
    print("=" * 80)
    print("TESTING ENHANCED SEARCH PLANNING SYSTEM")
    print("=" * 80)
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📋 Test Case {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        
        if test_case['user_data']:
            context = build_user_context(test_case['user_data'])
            print(f"User Context: {context}")
        
        print("\n🔍 Generating search strategy...")
        
        try:
            # Generate search strategy
            search_strategy = plan_search(
                query=test_case['query'],
                llm=llm,
                user_data=test_case['user_data']
            )
            
            # Display results
            print(f"\n✅ Search Strategy Generated Successfully!")
            print(f"   Query Intent: {search_strategy.query_intent or 'Not specified'}")
            print(f"   Confidence Score: {search_strategy.confidence_score:.2f}")
            print(f"   Categories Found: {len(search_strategy.search_plan)}")
            
            print("\n📊 Category Breakdown:")
            for category in search_strategy.search_plan:
                print(f"\n   🏷️  {category.category} (weight: {category.weight})")
                print(f"      Keywords: {', '.join(category.keywords[:5])}")
                if len(category.keywords) > 5:
                    print(f"                ... and {len(category.keywords) - 5} more")
                print(f"      Semantic: {category.semantic_phrases[0] if category.semantic_phrases else 'None'}")
                if len(category.semantic_phrases) > 1:
                    print(f"                ... and {len(category.semantic_phrases) - 1} more phrases")
                print(f"      Rationale: {category.rationale[:100]}...")
            
            # Generate hybrid queries
            keyword_queries, semantic_queries = generate_hybrid_queries(search_strategy)
            print(f"\n🔗 Hybrid Query Generation:")
            print(f"   Keyword Queries: {len(keyword_queries)}")
            print(f"   Semantic Queries: {len(semantic_queries)}")
            
            # Show sample queries
            if keyword_queries:
                print(f"\n   Sample Keywords: {keyword_queries[0][:50]}...")
            if semantic_queries:
                print(f"   Sample Semantic: {semantic_queries[0][:50]}...")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-" * 80)
    
    print("\n" + "=" * 80)
    print("✅ TESTING COMPLETE")
    print("=" * 80)


def test_json_output():
    """Test that the LLM produces valid JSON."""
    
    llm = get_llm(config.DEFAULT_LLM_MODEL)
    
    # Simple query to test JSON parsing
    query = "How can I optimize my sleep?"
    
    print("\n🧪 Testing JSON Output Format...")
    print(f"Query: '{query}'")
    
    from coach.prompts import PLANNING_PROMPT_TEMPLATE
    from langchain_core.messages import HumanMessage
    
    prompt = PLANNING_PROMPT_TEMPLATE.format(
        query=query,
        user_context="No user context available."
    )
    
    messages = [HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    
    print("\n📄 Raw LLM Response:")
    print("-" * 40)
    print(response.content[:500])
    print("-" * 40)
    
    # Try to parse the JSON
    from coach.search import parse_search_strategy_json
    
    try:
        parsed = parse_search_strategy_json(response.content)
        print("\n✅ JSON parsing successful!")
        print(f"   Categories found: {len(parsed.get('search_plan', []))}")
        for item in parsed.get('search_plan', []):
            print(f"   - {item['category']}")
    except Exception as e:
        print(f"\n❌ JSON parsing failed: {e}")


if __name__ == "__main__":
    # Check if API keys are configured
    if not config.get_api_key("openai") and not config.get_api_key("google"):
        print("❌ Error: No API keys configured. Please set OPENAI_API_KEY or GOOGLE_API_KEY in your .env file")
        sys.exit(1)
    
    # Run tests
    test_json_output()
    print("\n" + "=" * 80)
    test_search_planning()