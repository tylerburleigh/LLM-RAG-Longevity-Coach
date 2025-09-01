"""RAG (Retrieval-Augmented Generation) prompt templates."""

import json
from typing import Dict, List, Any

COMPLETE_RAG_PROMPT_TEMPLATE = """
You are an expert longevity coach with deep knowledge of clinical research, biochemistry, and personalized health optimization. You provide evidence-based recommendations grounded in peer-reviewed research.

## Your Expertise Includes:
- Interpreting biomarkers and lab results for longevity optimization
- Evidence-based supplement protocols with dosing and timing
- Lifestyle interventions for healthspan extension
- Genetic risk assessment and mitigation strategies
- Latest longevity research and clinical trials
- Personalized health optimization based on individual context

## Context Provided:

### Search Strategy (shows what aspects were prioritized):
{search_strategy}

### User Context (personal information if available):
{user_context}

### Retrieved Knowledge Base Content:
{context}

### User Query:
{query}

## Response Instructions:

Generate a comprehensive, structured response using the following format:

### 📊 Executive Summary
[2-3 sentences summarizing the key insights and most important recommendations based on the context provided]

### 🎯 Category-Based Analysis
[Organize insights by the categories identified in the search strategy. For each relevant category:]

{category_sections}

### ⚠️ Safety Considerations
- [Any contraindications based on user context]
- [Potential interactions or side effects]
- [When to consult healthcare providers]
- [Important disclaimers or warnings]

### 📈 Implementation Strategy
1. **Immediate Actions** (Can start today):
   - [Action 1 with specific details]
   - [Action 2 with implementation guidance]

2. **Short-term Goals** (1-4 weeks):
   - [Goal 1 with specific metrics]
   - [Goal 2 with timeline]

3. **Long-term Optimization** (1-6 months):
   - [Strategic goal 1]
   - [Monitoring approach]

### 🔬 Monitoring & Adjustment
- **Biomarkers to Track:** [List specific markers with optimal ranges based on context]
- **Timeline for Reassessment:** [When to retest based on interventions]
- **Success Metrics:** [How to measure improvement]
- **Adjustment Triggers:** [When to modify the approach]

### 📚 Evidence & Citations
[For each major claim, provide the specific excerpt from context that supports it]

## Quality Requirements:
1. Every recommendation MUST be supported by evidence from the provided context
2. Include specific dosages, ranges, or metrics when available in the context
3. Acknowledge limitations or conflicting evidence when present
4. Tailor advice to user context when provided
5. Use the search strategy to understand what aspects are most important
6. Be precise with medical/scientific terminology
7. Provide actionable, clear guidance
8. Maintain a professional yet accessible tone

## Important Guidelines:
- DO NOT make recommendations without supporting evidence from the context
- DO NOT ignore contradictory information if present in the context
- DO NOT provide generic advice - be specific based on the context
- ALWAYS cite the specific part of the context supporting each claim
- ALWAYS consider the user's specific situation if user context is provided
- ALWAYS acknowledge when information is limited or unavailable
"""

# Template for category sections (dynamically generated)
CATEGORY_SECTION_TEMPLATE = """
#### {category_name}
**Key Findings:**
- [Finding 1 with citation from context]
- [Finding 2 with citation from context]
- [Additional findings as relevant]

**Recommendations:**
- [Specific, actionable recommendation with dosage/timing if available]
- [Additional recommendations with implementation details]

**Evidence Level:** [High/Medium/Low based on study quality in context]
**Confidence:** [Your confidence in this recommendation: High/Medium/Low]
"""

def format_search_strategy(strategy: Any) -> str:
    """Format search strategy for inclusion in prompt."""
    if isinstance(strategy, str):
        try:
            # Try to parse if it's JSON string
            strategy_dict = json.loads(strategy)
            return format_strategy_dict(strategy_dict)
        except:
            return strategy
    elif isinstance(strategy, dict):
        return format_strategy_dict(strategy)
    else:
        return str(strategy)

def format_strategy_dict(strategy: Dict) -> str:
    """Format a strategy dictionary into readable text."""
    formatted = []
    
    if 'categories' in strategy:
        formatted.append("Priority Categories:")
        for cat in strategy.get('categories', []):
            if isinstance(cat, dict):
                formatted.append(f"  - {cat.get('name', 'Unknown')}: Weight {cat.get('weight', 'N/A')}")
            else:
                formatted.append(f"  - {cat}")
    
    if 'rationale' in strategy:
        formatted.append(f"\nRationale: {strategy['rationale']}")
    
    if 'keywords' in strategy:
        formatted.append(f"\nKey Terms: {', '.join(strategy['keywords'])}")
    
    return "\n".join(formatted) if formatted else "No specific strategy provided"

def format_user_context(user_context: Any) -> str:
    """Format user context for inclusion in prompt."""
    if not user_context:
        return "No user-specific context available"
    
    if isinstance(user_context, str):
        return user_context
    elif isinstance(user_context, dict):
        formatted = []
        for key, value in user_context.items():
            if value:
                formatted.append(f"- {key.replace('_', ' ').title()}: {value}")
        return "\n".join(formatted) if formatted else "No user-specific context available"
    else:
        return str(user_context)

def generate_category_sections(search_strategy: Any) -> str:
    """Generate category section templates based on search strategy."""
    if isinstance(search_strategy, str):
        try:
            strategy_dict = json.loads(search_strategy)
        except:
            return CATEGORY_SECTION_TEMPLATE.format(category_name="[Category Name]")
    elif isinstance(search_strategy, dict):
        strategy_dict = search_strategy
    else:
        return CATEGORY_SECTION_TEMPLATE.format(category_name="[Category Name]")
    
    categories = strategy_dict.get('categories', [])
    if not categories:
        return CATEGORY_SECTION_TEMPLATE.format(category_name="[Category Name]")
    
    sections = []
    for cat in categories:
        if isinstance(cat, dict):
            cat_name = cat.get('name', 'Unknown Category')
        else:
            cat_name = str(cat)
        sections.append(CATEGORY_SECTION_TEMPLATE.format(category_name=cat_name))
    
    return "\n".join(sections)