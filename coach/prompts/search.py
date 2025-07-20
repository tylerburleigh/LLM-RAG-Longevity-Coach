"""Search query generation prompt templates."""

SEARCH_QUERIES_PROMPT_TEMPLATE = """You are a search expert. Respond ONLY with a JSON dictionary mapping categories to search queries.

Based on the following search strategy, generate separate search queries for each category relevant to longevity.
Categories to consider: Genetics, Lab Work, Supplements, etc...
For each relevant category, provide 1-3 specific search queries that target information in that category.
Respond with ONLY a valid JSON dictionary where keys are the category names and values are lists of search queries.
Example:
{{
  "Genetics": ["gene variant longevity", "genetic test interpretation"],
  "Lab Work": ["blood panel longevity", "inflammation lab tests"],
  "Supplements": ["vitamin D supplement effects", "antioxidant supplement longevity"],
  "User Info": ["age", "sex", "height", "weight", "diet"],
  "Lifestyle": ["diet", "exercise"],
  "Medical Conditions": ["Crohn's Disease", "Alzheimer's Disease"],
  "Sleep": ["Sleep Duration", "Sleep Efficiency"],
  "Fitness": ["HRV", "Breathing Rate", "Steps", "Resting HR"],
  "Exercise": ["Steps"]
}}

Search Strategy:
```{search_strategy}```
"""