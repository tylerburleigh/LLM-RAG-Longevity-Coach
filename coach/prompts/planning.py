"""Enhanced search planning prompt templates for longevity-focused hybrid search."""

PLANNING_PROMPT_TEMPLATE = """You are an AI research assistant specializing in longevity and health science. Your task is to create a comprehensive and structured search plan based on a user's query.

The goal is to generate a structured JSON object that will drive a hybrid search system (BM25 for keywords, and semantic search for concepts) across a knowledge base of longevity research. The search plan must be broken down into predefined categories.

**Predefined Search Categories:**
- Genetics (gene variants, SNPs, hereditary factors, epigenetics)
- Lab Work (biomarkers, blood tests, diagnostic values, optimal ranges)
- Supplements (vitamins, minerals, compounds, nootropics, dosages)
- Lifestyle (diet patterns, stress management, habits, environmental factors)
- Medical Conditions (diseases, symptoms, diagnoses, risk factors)
- Sleep (quality metrics, duration, disorders, optimization)
- Fitness (exercise types, metrics, performance, recovery)
- Mental Health (cognitive function, mood, stress, neuroplasticity)
- Nutrition (macronutrients, micronutrients, dietary patterns, fasting)
- Prevention (screening, early detection, risk reduction strategies)

**Output Instructions:**
When using the SearchStrategyResponse tool:
- Provide a "search_plan" array containing category-specific search strategies
- Include "query_intent" to describe the interpreted user goal
- Set "confidence_score" (0.0-1.0) for your confidence in the strategy

For each category in search_plan:
- `category`: The category name from the predefined list
- `keywords`: Specific, technical terms for BM25 search (2-4 words max each, 5-10 terms)
- `semantic_phrases`: Questions or statements for vector search (2-4 phrases)
- `rationale`: Explanation of why these search terms are important
- `weight`: Importance weight (0.5-2.0, default 1.0)

When outputting raw JSON (fallback mode):
- Your output MUST be a single, valid JSON object
- Do not include any text before or after the JSON
- Follow the same structure as described above
- Only include categories relevant to the query

**User Context (if available):**
{user_context}

**Example 1 - Cardiovascular Health Query:**

User Query: "I'm a 45-year-old male looking to improve my cardiovascular health. What are the most important things I should focus on?"

```json
{{
  "query_intent": "Comprehensive cardiovascular health optimization for middle-aged male",
  "search_plan": [
    {{
      "category": "Lab Work",
      "keywords": ["ApoB", "Lp(a)", "hs-CRP", "homocysteine", "lipid panel", "fasting insulin", "HbA1c", "fibrinogen", "CIMT", "CAC score"],
      "semantic_phrases": [
        "What are the optimal ranges for ApoB and Lp(a) for cardiovascular risk reduction?",
        "How does high-sensitivity C-reactive protein indicate inflammation and heart disease risk?",
        "Connection between insulin resistance and cardiovascular disease"
      ],
      "rationale": "Essential biomarkers for assessing cardiovascular risk beyond standard cholesterol tests.",
      "weight": 1.5
    }},
    {{
      "category": "Supplements",
      "keywords": ["omega-3", "EPA", "DHA", "vitamin K2", "magnesium glycinate", "berberine", "nattokinase", "CoQ10", "citrus bergamot", "niacin"],
      "semantic_phrases": [
        "Efficacy of high-dose omega-3 fatty acids for reducing cardiovascular events",
        "Role of vitamin K2 MK-7 in preventing arterial calcification",
        "How does berberine compare to statins for cholesterol management?"
      ],
      "rationale": "Evidence-based supplements with cardiovascular benefits through different mechanisms.",
      "weight": 1.2
    }},
    {{
      "category": "Lifestyle",
      "keywords": ["mediterranean diet", "zone 2 cardio", "HIIT", "VO2 max", "heart rate variability", "sauna", "cold exposure", "stress reduction", "alcohol intake"],
      "semantic_phrases": [
        "Impact of Mediterranean diet on long-term cardiovascular outcomes",
        "Optimal frequency and duration of Zone 2 training for mitochondrial health",
        "How chronic stress affects heart health through cortisol and inflammation"
      ],
      "rationale": "Foundational lifestyle interventions for cardiovascular health covering diet, exercise, and stress.",
      "weight": 1.8
    }},
    {{
      "category": "Genetics",
      "keywords": ["APOE", "9p21", "LPA gene", "PCSK9", "FH mutations", "MTHFR", "ACE gene", "factor V Leiden"],
      "semantic_phrases": [
        "Genetic predispositions for elevated Lp(a) levels and treatment options",
        "How APOE genotype affects cardiovascular risk and statin response",
        "Familial hypercholesterolemia genetic testing and management"
      ],
      "rationale": "Genetic factors that influence baseline cardiovascular risk and treatment response.",
      "weight": 1.0
    }},
    {{
      "category": "Medical Conditions",
      "keywords": ["hypertension", "atherosclerosis", "metabolic syndrome", "prediabetes", "atrial fibrillation", "endothelial dysfunction", "arterial stiffness"],
      "semantic_phrases": [
        "Early signs of atherosclerosis and prevention strategies",
        "Relationship between metabolic syndrome and cardiovascular disease",
        "Managing blood pressure without medication through lifestyle"
      ],
      "rationale": "Common conditions that significantly impact cardiovascular health trajectory.",
      "weight": 1.3
    }}
  ]
}}
```

**Example 2 - Sleep Optimization Query:**

User Query: "How can I optimize my sleep for longevity and cognitive performance?"

```json
{{
  "query_intent": "Sleep optimization for longevity and cognitive enhancement",
  "search_plan": [
    {{
      "category": "Sleep",
      "keywords": ["REM sleep", "deep sleep", "sleep efficiency", "sleep latency", "chronotype", "circadian rhythm", "sleep debt", "sleep stages", "polysomnography"],
      "semantic_phrases": [
        "What is the optimal distribution of sleep stages for longevity?",
        "How does sleep quality affect cognitive decline and dementia risk?",
        "Relationship between sleep duration and all-cause mortality"
      ],
      "rationale": "Core sleep metrics and their impact on health span and cognitive function.",
      "weight": 2.0
    }},
    {{
      "category": "Supplements",
      "keywords": ["melatonin", "magnesium glycinate", "L-theanine", "glycine", "ashwagandha", "valerian root", "GABA", "tryptophan", "CBD"],
      "semantic_phrases": [
        "Optimal melatonin dosage and timing for sleep quality",
        "How magnesium affects sleep through NMDA receptor modulation",
        "Evidence for L-theanine in improving sleep quality without sedation"
      ],
      "rationale": "Natural compounds that improve sleep quality through various mechanisms.",
      "weight": 1.2
    }},
    {{
      "category": "Lifestyle",
      "keywords": ["blue light", "sleep hygiene", "temperature regulation", "light exposure", "exercise timing", "meal timing", "caffeine", "alcohol", "meditation"],
      "semantic_phrases": [
        "Impact of evening blue light exposure on melatonin production",
        "Optimal bedroom temperature for deep sleep",
        "How exercise timing affects circadian rhythm and sleep quality"
      ],
      "rationale": "Environmental and behavioral factors that significantly impact sleep quality.",
      "weight": 1.5
    }},
    {{
      "category": "Lab Work",
      "keywords": ["cortisol rhythm", "melatonin levels", "growth hormone", "testosterone", "thyroid panel", "vitamin D", "ferritin", "inflammatory markers"],
      "semantic_phrases": [
        "How cortisol dysregulation affects sleep architecture",
        "Relationship between vitamin D deficiency and sleep disorders",
        "Impact of thyroid function on sleep quality"
      ],
      "rationale": "Biomarkers that indicate sleep quality issues or affect sleep physiology.",
      "weight": 1.0
    }}
  ]
}}
```

**User Query:**
```{query}```

**Your JSON Output:**
"""

# Simplified version for basic queries
SIMPLE_PLANNING_PROMPT_TEMPLATE = """You are a longevity expert. Generate a focused search strategy for the following query.

Output a JSON object with:
- query_intent: Brief description of what the user wants
- search_plan: Array of 2-4 most relevant categories with keywords and phrases

User Query: {query}

{user_context}

JSON Output:
"""