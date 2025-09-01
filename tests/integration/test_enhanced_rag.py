#!/usr/bin/env python3
"""Test script for enhanced RAG workflow."""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coach.langchain_vector_store import LangChainVectorStore
from coach.longevity_coach import LongevityCoach
from coach.config import config

def test_enhanced_workflow():
    """Test the enhanced insights generation workflow."""
    
    print("🚀 Testing Enhanced RAG Workflow\n")
    print("="*60)
    
    # Initialize vector store
    print("📚 Initializing vector store...")
    vector_store = LangChainVectorStore(persist_directory=config.VECTOR_STORE_FOLDER)
    
    # Initialize coach
    print(f"🤖 Initializing LongevityCoach with model: {config.DEFAULT_LLM_MODEL}")
    coach = LongevityCoach(
        vector_store=vector_store,
        model_name=config.DEFAULT_LLM_MODEL,
        reasoning_effort=config.DEFAULT_REASONING_EFFORT
    )
    
    # Test query
    test_query = "What supplements should I take for cognitive enhancement and neuroprotection?"
    
    print(f"\n📝 Test Query: {test_query}")
    print("="*60)
    
    # Generate clarifying questions
    print("\n💭 Generating clarifying questions...")
    questions = coach.generate_clarifying_questions(test_query)
    
    if questions:
        print("\nClarifying Questions:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
    
    # Simulate user answers
    user_answers = """
    1. I'm a 45-year-old male professional with high cognitive demands
    2. No current cognitive issues, looking for prevention and optimization
    3. Currently taking vitamin D and omega-3
    4. Budget is flexible for evidence-based interventions
    5. No known allergies or contraindications
    """
    
    print("\n📊 User Context (simulated):")
    print(user_answers)
    
    # Define user data for context
    user_data = {
        "age": "45",
        "sex": "male",
        "occupation": "professional with high cognitive demands",
        "current_supplements": "vitamin D, omega-3",
        "health_goals": "cognitive enhancement and neuroprotection",
        "budget": "flexible",
        "medical_conditions": "none reported",
        "allergies": "none"
    }
    
    # Generate insights with progress tracking
    print("\n🔬 Generating Insights...")
    print("-"*60)
    
    def progress_callback(msg):
        print(f"  {msg}")
    
    insights_response = coach.generate_insights(
        initial_query=test_query,
        clarifying_questions=questions,
        user_answers_str=user_answers,
        progress_callback=progress_callback,
        user_data=user_data
    )
    
    # Display results
    print("\n✨ Generated Insights:")
    print("="*60)
    
    # Display executive summary if available
    if hasattr(insights_response, 'executive_summary') and insights_response.executive_summary:
        print("\n📊 EXECUTIVE SUMMARY:")
        print("-"*60)
        print(insights_response.executive_summary)
        print("-"*60)
    
    # Get insights list
    insights = insights_response.insights if hasattr(insights_response, 'insights') else insights_response
    
    for i, insight in enumerate(insights, 1):
        print(f"\n🎯 Insight #{i}: {insight.insight}")
        print(f"   Importance: {insight.importance} | Confidence: {insight.confidence}")
        print(f"\n   📋 Recommendation:")
        print(f"   {insight.recommendation[:500]}..." if len(insight.recommendation) > 500 else f"   {insight.recommendation}")
        
        if hasattr(insight, 'implementation_protocol') and insight.implementation_protocol:
            print(f"\n   📝 Implementation Protocol:")
            print(f"   {insight.implementation_protocol[:200]}...")
        
        if hasattr(insight, 'monitoring_plan') and insight.monitoring_plan:
            print(f"\n   📊 Monitoring Plan:")
            print(f"   {insight.monitoring_plan[:200]}...")
        
        if hasattr(insight, 'safety_notes') and insight.safety_notes:
            print(f"\n   ⚠️ Safety Notes:")
            print(f"   {insight.safety_notes[:200]}...")
        
        if insight.rationale:
            print(f"\n   🔬 Rationale:")
            # Truncate long rationale for display
            rationale_preview = insight.rationale[:300] + "..." if len(insight.rationale) > 300 else insight.rationale
            print(f"   {rationale_preview}")
        
        print("-"*60)
    
    print(f"\n✅ Test completed successfully! Generated {len(insights)} insights.")
    
    # Check for enhanced features
    print("\n🔍 Checking for Enhanced Features:")
    print("-"*60)
    
    features_found = []
    
    # Check for executive summary
    if hasattr(insights_response, 'executive_summary') and insights_response.executive_summary:
        features_found.append("✓ Executive Summary present")
    
    # Check if insights contain the enhanced structure elements
    for insight in insights:
        # Check for separated recommendation field
        if hasattr(insight, 'recommendation') and insight.recommendation:
            features_found.append("✓ Separate recommendation field")
            break
    
    for insight in insights:
        # Check for implementation protocol
        if hasattr(insight, 'implementation_protocol') and insight.implementation_protocol:
            features_found.append("✓ Implementation protocol included")
            break
    
    for insight in insights:
        # Check for monitoring plan
        if hasattr(insight, 'monitoring_plan') and insight.monitoring_plan:
            features_found.append("✓ Monitoring plan included")
            break
    
    for insight in insights:
        # Check for safety notes
        if hasattr(insight, 'safety_notes') and insight.safety_notes:
            features_found.append("✓ Safety considerations included")
            break
    
    # Check for timeline structure in recommendations
    for insight in insights:
        recommendation_text = insight.recommendation.lower()
        if "immediate" in recommendation_text or "today" in recommendation_text:
            features_found.append("✓ Immediate Actions timeline")
            break
    
    for insight in insights:
        recommendation_text = insight.recommendation.lower()
        if "short-term" in recommendation_text or "week" in recommendation_text:
            features_found.append("✓ Short-term Goals timeline")
            break
    
    for insight in insights:
        recommendation_text = insight.recommendation.lower()
        if "long-term" in recommendation_text or "month" in recommendation_text:
            features_found.append("✓ Long-term Optimization timeline")
            break
    
    # Check for evidence citations
    for insight in insights:
        if insight.rationale and ("level a" in insight.rationale.lower() or "level b" in insight.rationale.lower() or 
                                  "level c" in insight.rationale.lower() or "level d" in insight.rationale.lower()):
            features_found.append("✓ Evidence level citations present")
            break
    
    if features_found:
        print("\nEnhanced features detected:")
        for feature in features_found:
            print(f"  {feature}")
    else:
        print("\n⚠️  No enhanced features detected - prompt may need adjustment")
    
    return insights_response

if __name__ == "__main__":
    try:
        test_enhanced_workflow()
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)