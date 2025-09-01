# Plan: Merge RAG Template Features into Active Workflow

## Current Situation

The codebase has two parallel prompt systems:
1. **Active System**: Uses `INSIGHTS_PROMPT_TEMPLATE` in `coach/prompts/insights.py`
2. **Dormant System**: Has sophisticated `COMPLETE_RAG_PROMPT_TEMPLATE` in `coach/prompts/rag.py` (unused)

The dormant RAG template has superior structure but is trapped behind disabled chains infrastructure (`USE_LANGCHAIN_CHAINS=false`).

## Objective

Enhance the active insights generation workflow with the best features from the unused RAG template, while maintaining the simpler direct architecture.

## Implementation Plan

### Phase 1: Enhance Active Prompt Template

**File to modify**: `coach/prompts/insights.py`

Incorporate these features from `COMPLETE_RAG_PROMPT_TEMPLATE`:

1. **Structured Response Format**:
   - Executive Summary section
   - Category-based analysis (dynamic based on search strategy)
   - Safety Considerations section
   - Implementation Strategy (Immediate/Short-term/Long-term)
   - Monitoring & Adjustment section
   - Evidence & Citations section

2. **Enhanced Context Integration**:
   - Better use of search strategy to guide response
   - Explicit category weighting in analysis
   - User context personalization

3. **Quality Requirements**:
   - Evidence-based recommendations only
   - Specific dosages and metrics when available
   - Acknowledgment of limitations
   - Contradiction handling

### Phase 2: Update Prompt Formatting Logic

**File to modify**: `coach/longevity_coach.py`

1. Import helper functions from `coach/prompts/rag.py`:
   - `format_search_strategy()`
   - `format_user_context()` 
   - `generate_category_sections()`

2. Update `generate_insights()` method to:
   - Format search strategy properly
   - Generate dynamic category sections
   - Pass formatted context to enhanced prompt

### Phase 3: Clean Up Unused Infrastructure

**Files to remove/simplify**:

1. **Remove dormant chains code**:
   - Delete chain initialization in `LongevityCoach.__init__()`
   - Remove `CHAINS_AVAILABLE` flag and import attempts
   - Clean up `self.chains` and `self.rag_workflow` attributes

2. **Simplify configuration**:
   - Remove `USE_LANGCHAIN_CHAINS` from `coach/config.py`
   - Remove chains parameter from `LongevityCoach` constructor

3. **Archive or remove**:
   - Consider moving `coach/chains.py` to an archive folder
   - Keep `coach/prompts/rag.py` temporarily for reference during migration

### Phase 4: Testing & Validation

1. **Functional Testing**:
   - Verify insights generation with enhanced prompt
   - Test category-based analysis works correctly
   - Ensure search strategy integration functions

2. **Output Quality**:
   - Compare outputs before/after enhancement
   - Verify structured sections are populated
   - Check evidence citations work properly

3. **Performance**:
   - Ensure no performance degradation
   - Verify token usage is reasonable

## Implementation Steps

### Step 1: Create Enhanced Insights Prompt
```python
# Merge best features from COMPLETE_RAG_PROMPT_TEMPLATE into INSIGHTS_PROMPT_TEMPLATE
# Add structured sections while keeping the working Pydantic model integration
```

### Step 2: Update Prompt Invocation
```python
# In coach/longevity_coach.py:
from coach.prompts.rag import (
    format_search_strategy,
    format_user_context, 
    generate_category_sections
)

# Update generate_insights() to use enhanced formatting
```

### Step 3: Test Enhanced Workflow
```bash
# Test with various queries
# Verify structured output
# Check category-based analysis
```

### Step 4: Remove Unused Code
```bash
# Remove chains initialization
# Clean up configuration
# Archive unused files
```

## Benefits

1. **Immediate Value**: Better structured, more comprehensive insights
2. **Simpler Architecture**: No complex chains infrastructure
3. **Maintainable**: Single code path, easier to debug
4. **Extensible**: Enhanced prompt structure supports future improvements

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Incremental changes with testing at each step |
| Token usage increase | Monitor and optimize prompt length |
| Output format changes | Maintain backward compatibility where possible |
| Lost chain capabilities | Document advanced features for potential future use |

## Success Criteria

- [ ] Enhanced prompt generates structured responses with all sections
- [ ] Category-based analysis reflects search strategy priorities  
- [ ] Evidence citations link to source context
- [ ] Safety considerations included when relevant
- [ ] Implementation strategy provides actionable steps
- [ ] No regression in response quality or performance
- [ ] Unused code removed, reducing maintenance burden

## Timeline

- **Phase 1**: 2-3 hours (Enhance prompt template)
- **Phase 2**: 1-2 hours (Update formatting logic)
- **Phase 3**: 1 hour (Clean up unused code)
- **Phase 4**: 2-3 hours (Testing and validation)

**Total estimate**: 6-9 hours of development work

## Next Steps

1. Review and approve this plan
2. Create backup of current working system
3. Begin Phase 1 implementation
4. Iterate based on testing results