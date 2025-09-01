# coach/search.py
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document

from coach.prompts import PLANNING_PROMPT_TEMPLATE, SIMPLE_PLANNING_PROMPT_TEMPLATE
from coach.types import Query
from coach.models import SearchStrategy, SearchCategory, SearchStrategyResponse
from coach.exceptions import (
    SearchStrategyException,
    RetrievalException,
)
from coach.config import config
from coach.retrievers import create_advanced_retriever
from coach.llm_providers import get_embeddings

logger = logging.getLogger(__name__)


def build_user_context(user_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Build user context string for personalized search planning.
    
    Args:
        user_data: Optional dictionary containing user information
        
    Returns:
        Formatted user context string
    """
    if not user_data:
        return "No user context available."
    
    context_parts = []
    
    # Basic demographics
    if "age" in user_data:
        context_parts.append(f"Age: {user_data['age']}")
    if "sex" in user_data:
        context_parts.append(f"Sex: {user_data['sex']}")
    if "weight" in user_data:
        context_parts.append(f"Weight: {user_data['weight']}")
    if "height" in user_data:
        context_parts.append(f"Height: {user_data['height']}")
    
    # Health conditions
    if "conditions" in user_data and user_data["conditions"]:
        conditions = user_data["conditions"]
        if isinstance(conditions, list):
            context_parts.append(f"Health Conditions: {', '.join(conditions)}")
        else:
            context_parts.append(f"Health Conditions: {conditions}")
    
    # Goals
    if "goals" in user_data and user_data["goals"]:
        goals = user_data["goals"]
        if isinstance(goals, list):
            context_parts.append(f"Health Goals: {', '.join(goals)}")
        else:
            context_parts.append(f"Health Goals: {goals}")
    
    # Recent lab values
    if "recent_labs" in user_data and user_data["recent_labs"]:
        labs = user_data["recent_labs"]
        if isinstance(labs, dict):
            lab_items = [f"{k}: {v}" for k, v in labs.items()]
            context_parts.append(f"Recent Labs: {', '.join(lab_items[:5])}")  # Limit to 5 items
    
    # Medications/Supplements
    if "medications" in user_data and user_data["medications"]:
        meds = user_data["medications"]
        if isinstance(meds, list):
            context_parts.append(f"Current Medications: {', '.join(meds[:5])}")
    
    if "supplements" in user_data and user_data["supplements"]:
        supps = user_data["supplements"]
        if isinstance(supps, list):
            context_parts.append(f"Current Supplements: {', '.join(supps[:5])}")
    
    return "User Context: " + " | ".join(context_parts) if context_parts else "No user context available."


def parse_search_strategy_json(llm_response: str) -> Dict[str, Any]:
    """
    Parse and validate the search strategy JSON output from LLM.
    
    Args:
        llm_response: Raw LLM response containing JSON
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        SearchStrategyException: If parsing fails
    """
    try:
        # Log the raw response for debugging
        logger.debug(f"Raw LLM response length: {len(llm_response)}")
        logger.debug(f"First 200 chars: {llm_response[:200]}")
        
        # Extract JSON from response
        content = llm_response.strip()
        
        # Try to find JSON object directly first
        json_start = content.find('{')
        json_end = content.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            # Extract potential JSON object
            potential_json = content[json_start:json_end + 1]
            
            # Try to parse it
            try:
                strategy_dict = json.loads(potential_json)
                logger.debug("Successfully parsed JSON from extracted object")
                
                # Validate structure
                if "search_plan" in strategy_dict and isinstance(strategy_dict["search_plan"], list):
                    # Validate each category
                    for item in strategy_dict["search_plan"]:
                        required_fields = ["category", "keywords", "semantic_phrases", "rationale"]
                        for field in required_fields:
                            if field not in item:
                                logger.warning(f"Missing field '{field}' in search plan item, adding default")
                                # Add defaults for missing fields
                                if field == "keywords":
                                    item[field] = ["longevity", "health"]
                                elif field == "semantic_phrases":
                                    item[field] = ["health optimization strategies"]
                                elif field == "rationale":
                                    item[field] = "Auto-generated"
                                elif field == "category":
                                    item[field] = "General"
                    
                    return strategy_dict
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse extracted JSON: {e}")
        
        # Fallback: Handle code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
        
        # Clean up common issues
        content = content.strip()
        
        # Remove any non-JSON prefix (sometimes LLMs add explanatory text)
        if content and not content.startswith('{'):
            json_start = content.find('{')
            if json_start != -1:
                content = content[json_start:]
                logger.debug("Removed non-JSON prefix")
        
        # Parse JSON
        strategy_dict = json.loads(content)
        
        # Validate structure
        if "search_plan" not in strategy_dict:
            raise ValueError("Missing 'search_plan' in JSON output")
        
        if not isinstance(strategy_dict["search_plan"], list):
            raise ValueError("'search_plan' must be an array")
        
        # Validate each category
        for item in strategy_dict["search_plan"]:
            required_fields = ["category", "keywords", "semantic_phrases", "rationale"]
            for field in required_fields:
                if field not in item:
                    raise ValueError(f"Missing required field '{field}' in search plan item")
        
        logger.debug("Successfully parsed and validated search strategy")
        return strategy_dict
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse search strategy JSON: {e}")
        logger.debug(f"Raw response: {llm_response[:500]}")
        
        # Try to extract keywords from the response for a better fallback
        fallback_keywords = []
        lower_response = llm_response.lower()
        
        # Common health/longevity keywords to look for
        potential_keywords = [
            "longevity", "healthspan", "aging", "nutrition", "exercise", 
            "sleep", "supplement", "biomarker", "genetics", "lifestyle",
            "prevention", "optimization", "wellness", "fitness", "diet"
        ]
        
        for keyword in potential_keywords:
            if keyword in lower_response:
                fallback_keywords.append(keyword)
        
        # If we found some keywords, use them; otherwise use defaults
        if not fallback_keywords:
            fallback_keywords = ["longevity", "health optimization", "healthspan"]
        
        # Return enhanced fallback strategy
        return {
            "query_intent": "Health and longevity query (fallback mode)",
            "search_plan": [
                {
                    "category": "General",
                    "keywords": fallback_keywords[:5],  # Limit to 5 keywords
                    "semantic_phrases": [
                        "How to improve longevity and healthspan",
                        "Evidence-based health optimization strategies",
                        "Lifestyle factors for healthy aging"
                    ],
                    "rationale": "Fallback strategy generated due to parsing error",
                    "weight": 1.0
                }
            ]
        }


def plan_search(
    query: Query, 
    llm, 
    user_data: Optional[Dict[str, Any]] = None,
    use_simple: bool = False
) -> SearchStrategy:
    """
    Generate an enhanced search strategy based on the user's query.
    
    Args:
        query: The user's input query
        llm: The language model instance to use for planning
        user_data: Optional user context for personalization
        use_simple: Whether to use the simpler prompt template
        
    Returns:
        A SearchStrategy object with category-based search plans
        
    Raises:
        SearchStrategyException: If search planning fails
    """
    try:
        # Build user context
        user_context = build_user_context(user_data)
        
        # Try structured output first (for models that support bind_tools)
        try:
            # Bind SearchStrategyResponse to LLM for structured output
            structured_llm = llm.bind_tools(
                [SearchStrategyResponse], 
                tool_choice="SearchStrategyResponse"
            )
            
            # Select appropriate prompt template
            template = SIMPLE_PLANNING_PROMPT_TEMPLATE if use_simple else PLANNING_PROMPT_TEMPLATE
            
            # Format prompt with instructions for structured output
            structured_prompt = f"""{template.format(
                query=query,
                user_context=user_context
            )}

## Output Instructions:
You will use the SearchStrategyResponse tool to provide your response.
The tool expects:
- search_plan: Array of category-specific search strategies
- query_intent: Optional description of user's goal  
- confidence_score: Your confidence in the strategy (0.0-1.0)

For each category in search_plan, provide:
- category: The category name (e.g., "Genetics", "Lab Work", "Supplements")
- keywords: List of specific technical terms (2-4 words max each)
- semantic_phrases: List of conceptual phrases for semantic search
- rationale: Explanation of why these search terms are important
- weight: Importance weight (0.5-2.0, default 1.0)"""
            
            # Get structured response
            messages = [HumanMessage(content=structured_prompt)]
            response = structured_llm.invoke(messages)
            
            # Extract tool call
            if response.tool_calls:
                tool_call = response.tool_calls[0]
                strategy_response = SearchStrategyResponse.model_validate(tool_call["args"])
                
                # Convert to SearchStrategy
                search_strategy = SearchStrategy(
                    search_plan=strategy_response.search_plan,
                    user_context=user_data,
                    confidence_score=strategy_response.confidence_score,
                    query_intent=strategy_response.query_intent
                )
                
                logger.info(f"Generated search strategy with structured output: {len(strategy_response.search_plan)} categories")
                return search_strategy
                
        except Exception as e:
            logger.debug(f"Structured output failed, falling back to manual parsing: {e}")
            # Fall through to manual parsing below
        
        # Fallback: Manual parsing for models that don't support bind_tools
        # Select appropriate prompt template
        template = SIMPLE_PLANNING_PROMPT_TEMPLATE if use_simple else PLANNING_PROMPT_TEMPLATE
        
        # Format prompt
        prompt = template.format(
            query=query,
            user_context=user_context
        )
        
        # Get LLM response
        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        
        # Handle response content (can be string, list, or complex structure)
        if isinstance(response.content, list):
            # Handle complex response structure from reasoning models
            logger.debug(f"Response is a list with {len(response.content)} parts")
            
            # Look for the actual content in the response
            content = None
            json_parts = []  # Collect potential JSON parts
            
            for i, part in enumerate(response.content):
                logger.debug(f"Part {i} type: {type(part)}")
                
                if isinstance(part, dict):
                    # Log the dict structure for debugging
                    logger.debug(f"Part {i} keys: {part.keys() if isinstance(part, dict) else 'N/A'}")
                    
                    # Check for 'type' and 'text' fields (Responses API format)
                    if part.get('type') == 'text' and 'text' in part:
                        text_content = part['text']
                        if '{' in text_content and '"search_plan"' in text_content:
                            content = text_content
                            logger.debug(f"Found JSON in part {i} with type='text'")
                            break
                        json_parts.append(text_content)
                    # Check for 'text' field directly
                    elif 'text' in part:
                        text_content = part['text']
                        if '{' in text_content and '"search_plan"' in text_content:
                            content = text_content
                            logger.debug(f"Found JSON in part {i} with 'text' field")
                            break
                        json_parts.append(text_content)
                    # Check for 'content' field
                    elif 'content' in part:
                        text_content = part['content']
                        if '{' in text_content and '"search_plan"' in text_content:
                            content = text_content
                            logger.debug(f"Found JSON in part {i} with 'content' field")
                            break
                        json_parts.append(text_content)
                elif isinstance(part, str):
                    if '{' in part and '"search_plan"' in part:
                        content = part
                        logger.debug(f"Found JSON in part {i} as string")
                        break
                    json_parts.append(part)
            
            # If we didn't find JSON in a single part, try concatenating parts
            if content is None and json_parts:
                concatenated = " ".join(json_parts)
                if '{' in concatenated and '"search_plan"' in concatenated:
                    content = concatenated
                    logger.debug("Found JSON after concatenating parts")
                else:
                    # Last resort: concatenate everything
                    content = " ".join(str(part) for part in response.content)
                    logger.debug("Using full concatenation of all parts")
            elif content is None:
                # No parts found, concatenate everything
                content = " ".join(str(part) for part in response.content)
                logger.debug("No JSON parts found, using full concatenation")
        elif isinstance(response.content, str):
            content = response.content
            logger.debug("Response is a string")
        else:
            # Handle other response types
            content = str(response.content)
            logger.debug(f"Response is of type: {type(response.content)}")
        
        # Parse JSON response
        strategy_dict = parse_search_strategy_json(content)
        
        # Convert to SearchStrategy model
        search_categories = []
        for item in strategy_dict.get("search_plan", []):
            category = SearchCategory(
                category=item["category"],
                keywords=item.get("keywords", []),
                semantic_phrases=item.get("semantic_phrases", []),
                rationale=item.get("rationale", ""),
                weight=item.get("weight", 1.0)
            )
            search_categories.append(category)
        
        # Create SearchStrategy
        search_strategy = SearchStrategy(
            search_plan=search_categories,
            user_context=user_data,
            confidence_score=strategy_dict.get("confidence_score", 0.8),
            query_intent=strategy_dict.get("query_intent")
        )
        
        logger.info(f"Generated search strategy with {len(search_categories)} categories")
        return search_strategy
        
    except Exception as e:
        raise SearchStrategyException(f"Failed to plan search strategy: {str(e)}") from e


def generate_hybrid_queries(search_strategy: SearchStrategy) -> Tuple[List[str], List[str]]:
    """
    Generate separate keyword and semantic queries from the search strategy.
    
    Args:
        search_strategy: The structured search strategy
        
    Returns:
        Tuple of (keyword_queries, semantic_queries)
    """
    keyword_queries = []
    semantic_queries = []
    
    for category in search_strategy.search_plan:
        # Weight-adjusted repetition for more important categories
        repeat_count = max(1, int(category.weight))
        
        # Add keywords (for BM25)
        if category.keywords:
            # Combine keywords into search strings
            keyword_query = " ".join(category.keywords[:5])  # Limit to top 5
            for _ in range(repeat_count):
                keyword_queries.append(keyword_query)
            
            # Also add individual high-value keywords
            for keyword in category.keywords[:3]:
                keyword_queries.append(keyword)
        
        # Add semantic phrases (for vector search)
        for phrase in category.semantic_phrases:
            for _ in range(repeat_count):
                semantic_queries.append(phrase)
    
    # Remove duplicates while preserving order
    keyword_queries = list(dict.fromkeys(keyword_queries))
    semantic_queries = list(dict.fromkeys(semantic_queries))
    
    logger.info(f"Generated {len(keyword_queries)} keyword queries and {len(semantic_queries)} semantic queries")
    
    return keyword_queries, semantic_queries


def retrieve_context_enhanced(
    search_strategy: SearchStrategy,
    llm,
    vector_store,
    max_results: Optional[int] = None,
    category_weights: Optional[Dict[str, float]] = None
) -> List[str]:
    """
    Enhanced context retrieval using category-based hybrid search.
    
    Args:
        search_strategy: The structured search strategy
        llm: The language model instance
        vector_store: The vector store instance
        max_results: Maximum number of results to return
        category_weights: Optional custom weights for BM25 vs semantic per category
        
    Returns:
        A list of unique document texts
        
    Raises:
        RetrievalException: If retrieval fails
    """
    try:
        if max_results is None:
            max_results = config.DEFAULT_TOP_K
        
        # Default category weights for BM25 vs semantic search
        default_weights = {
            "Lab Work": (0.7, 0.3),      # More keyword-focused
            "Genetics": (0.7, 0.3),       # Technical terms important
            "Supplements": (0.6, 0.4),    # Mixed approach
            "Medical Conditions": (0.6, 0.4),
            "Lifestyle": (0.3, 0.7),      # More conceptual
            "Mental Health": (0.3, 0.7),   # Conceptual understanding
            "Sleep": (0.4, 0.6),
            "Fitness": (0.4, 0.6),
            "Nutrition": (0.5, 0.5),      # Balanced
            "Prevention": (0.4, 0.6),
            "General": (0.5, 0.5)         # Default balanced
        }
        
        if category_weights:
            default_weights.update(category_weights)
        
        all_documents = []
        seen_content = set()
        
        # Process each category separately for fine-grained control
        for category in search_strategy.search_plan:
            # Get weights for this category
            bm25_weight, semantic_weight = default_weights.get(
                category.category, 
                (0.5, 0.5)
            )
            
            # Adjust weights based on category importance
            bm25_weight *= category.weight
            semantic_weight *= category.weight
            
            # Retrieve using hybrid search with category-specific weights
            if vector_store.ensemble_retriever:
                # Temporarily adjust ensemble weights
                original_weights = vector_store.ensemble_retriever.weights
                vector_store.ensemble_retriever.weights = [semantic_weight, bm25_weight]
                
                # Create combined query
                query = f"{' '.join(category.keywords[:3])} {category.semantic_phrases[0] if category.semantic_phrases else ''}"
                
                # Retrieve documents
                docs = vector_store.ensemble_retriever.invoke(query)
                
                # Restore original weights
                vector_store.ensemble_retriever.weights = original_weights
                
                # Add unique documents
                for doc in docs[:max_results // len(search_strategy.search_plan) + 1]:
                    content = doc.page_content.strip()
                    if content not in seen_content:
                        seen_content.add(content)
                        all_documents.append(content)
        
        # If we don't have enough results, do a general search
        if len(all_documents) < max_results // 2:
            keyword_queries, semantic_queries = generate_hybrid_queries(search_strategy)
            
            # Combine top queries
            combined_query = " ".join(keyword_queries[:2] + semantic_queries[:1])
            
            if vector_store.ensemble_retriever:
                additional_docs = vector_store.ensemble_retriever.invoke(combined_query)
                
                for doc in additional_docs:
                    content = doc.page_content.strip()
                    if content not in seen_content and len(all_documents) < max_results:
                        seen_content.add(content)
                        all_documents.append(content)
        
        logger.info(f"Retrieved {len(all_documents)} unique documents using enhanced category-based search")
        return all_documents[:max_results]
        
    except Exception as e:
        raise RetrievalException(f"Failed to retrieve context: {str(e)}") from e


def retrieve_context(
    search_strategy: SearchStrategy,
    llm,
    vector_store,
    retrieval_strategy: str = "ensemble",
    use_multi_strategy: bool = False,
    **kwargs
) -> List[str]:
    """
    Retrieve context using the enhanced search strategy.
    This is the main entry point that maintains compatibility while using enhanced retrieval.
    
    Args:
        search_strategy: The enhanced search strategy with categories
        llm: The language model instance
        vector_store: The vector store instance
        retrieval_strategy: Advanced retrieval strategy to use
        use_multi_strategy: Whether to use multiple strategies
        **kwargs: Additional parameters for advanced retrieval
        
    Returns:
        A list of unique document texts
        
    Raises:
        RetrievalException: If retrieval fails
    """
    try:
        # Use enhanced retrieval for SearchStrategy objects
        if isinstance(search_strategy, SearchStrategy):
            return retrieve_context_enhanced(
                search_strategy=search_strategy,
                llm=llm,
                vector_store=vector_store,
                max_results=kwargs.get("max_results", config.DEFAULT_TOP_K),
                category_weights=kwargs.get("category_weights")
            )
        
        # Fallback for string strategies (backward compatibility)
        else:
            # Convert string to basic SearchStrategy
            basic_strategy = SearchStrategy(
                search_plan=[
                    SearchCategory(
                        category="General",
                        keywords=str(search_strategy).split()[:10],
                        semantic_phrases=[str(search_strategy)],
                        rationale="Converted from string strategy",
                        weight=1.0
                    )
                ],
                confidence_score=0.5
            )
            
            return retrieve_context_enhanced(
                search_strategy=basic_strategy,
                llm=llm,
                vector_store=vector_store,
                max_results=kwargs.get("max_results", config.DEFAULT_TOP_K)
            )
            
    except Exception as e:
        raise RetrievalException(f"Failed to retrieve context: {str(e)}") from e