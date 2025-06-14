# coach/prompts.py

PLANNING_PROMPT_TEMPLATE = """You are a longevity expert helping to plan an information search strategy.

Given the following user query, identify the key information we need to search for to provide a comprehensive answer.
Break down the types of information needed and explain why each is relevant.

User Query: ```{query}```

Output your search strategy, including:
1. Key topics to search for
2. Specific data points that would be valuable
3. How this information will help answer the query
"""

SEARCH_QUERIES_PROMPT_TEMPLATE = """You are a search expert. Respond ONLY with a JSON dictionary mapping categories to search queries.

Based on the following search strategy, generate separate search queries for each category relevant to longevity.
Categories to consider: Genetics, Lab Work, Supplements, etc...
For each category, provide 1-3 specific search queries that target information in that category.
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

RESPONSE_PROMPT_TEMPLATE = """
You are a knowledgeable longevity coach who uses comprehensive context to deliver actionable advice.

Using the following context documents, generate a thorough answer to the user's query with the following requirements:
- Reference and integrate insights from as many of the context documents as possible.
- Do not suggest any lab tests or interventions that already appear in the context.
- If you detect that the provided context is sparse or missing relevant details, indicate what additional documents or information would be helpful.
- Where possible, synthesize the known information into clear and actionable advice.
- If the user's query is about a specific supplement, supplement dose, or supplement effect, make sure to include information about the supplement, dose, and effect in the response.

Context:
```{context_str}```

User Query:
```{query}```
"""

DOCUMENT_STRUCTURE_PROMPT_TEMPLATE = """You are an expert at data extraction and structuring. Your task is to analyze the raw text provided below and convert it into one or more structured JSON object(s).

The JSON object must have the following fields:
- "doc_id": A unique identifier for the document. Create a meaningful ID based on the content, including category, sub-category, and a key identifier (e.g., "lab_2025-02-15_Cardiac_Risk_Total_Cholesterol").
- "text": The full, original text that you are analyzing.
- "metadata": An object containing key-value pairs of important metadata extracted from the text (e.g., "date", "category", "test", "supplement").

Examples:
```
{{"doc_id":"history_2025-02-15_family_HeartDisease","text":"Date: 2025-02-15\nCategory: History\nSub Category: Family History\nFamily History: Father diagnosed with coronary artery disease in his early 50s; paternal grandfather died of a heart attack at age 60.","metadata":{{"date":"2025-02-15","category":"History","sub_category":"Family History"}}}}
{{"doc_id":"lab_2025-02-15_Hematology_WBC","text":"Date: 2025-02-15\nCategory: Lab Work\nSub Category: Hematology\nTest: WBC\nResult: 6.4\nUnits: x E9/L\nReference: 4.0 - 11.0","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Hematology","test":"WBC"}}}}
{{"doc_id":"lab_2025-02-15_Hematology_RBC","text":"Date: 2025-02-15\nCategory: Lab Work\nSub Category: Hematology\nTest: RBC\nResult: 4.75\nUnits: x E12/L\nReference: 4.50 - 6.00","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Hematology","test":"RBC"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_Total_Cholesterol","text":"Date: 2025-02-15\nCategory: Lab Work\nSub Category: Cardiac Risk\nTest: Total Cholesterol\nResult: 5.8\nUnits: mmol/L\nReference: <5.2","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"Total Cholesterol"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_LDL","text":"Date: 2025-02-15\nCategory: Lab Work\nSub Category: Cardiac Risk\nTest: LDL\nResult: 3.7\nUnits: mmol/L\nReference: <3.3","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"LDL"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_HDL","text":"Date: 2025-02-15\nCategory: Lab Work\nSub Category: Cardiac Risk\nTest: HDL\nResult: 1.1\nUnits: mmol/L\nReference: >1.0","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"HDL"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_Triglycerides","text":"Date: 2025-02-15\nCategory: Lab Work\nSub Category: Cardiac Risk\nTest: Triglycerides\nResult: 1.9\nUnits: mmol/L\nReference: <1.7","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"Triglycerides"}}}}
{{"doc_id":"noteworthy_APO-E3/E4_rs429358(C;T)_and_rs7412(C;C)","text":"Gene: APO-E3/E4\nrsID: rs429358(C;T) & rs7412(C;C)\nGenotype: APOE3/E4\nKey Facts: 2-3x increased risk for coronary artery disease and Alzheimer's; Elevated LDL levels may be observed; Lifestyle changes (low saturated fat, regular exercise) recommended.","metadata":{{"category":"Genetics","sub_category":"Noteworthy Variant"}}}}
{{"doc_id":"noteworthy_ACE_rs4343","text":"Gene: ACE\nrsID: rs4343\nGenotype: (G;G)\nKey Facts: Associated with higher ACE enzyme levels; Increased risk of hypertension and cardiovascular complications; Reducing total and saturated fat intake may help mitigate risk.","metadata":{{"category":"Genetics","sub_category":"Noteworthy Variant"}}}}
{{"doc_id":"supplement_Niacin","text":"Supplement: Niacin\nDose: 500 mg\nEffects:\n - Cardiovascular: Can raise HDL (good cholesterol) and lower triglycerides, potentially beneficial in certain heart-risk profiles. [Confidence: High]\n - Side Effects: Flushing is common with higher niacin doses; extended-release forms or aspirin pre-dosing can help reduce flushing. [Confidence: Medium]\n - Glucose Metabolism: At higher doses, niacin may worsen glycemic control in some individuals. [Confidence: Medium]","metadata":{{"supplement":"Niacin","dose":500,"units":"mg"}}}}
```

Analyze the following text and generate one or more JSON objects like the examples above which contain the essential information. Respond with ONLY the JSON object(s).

```{raw_text}```
"""

GUIDED_ENTRY_PROMPT_TEMPLATE = """You are a data entry assistant. Your job is to convert a user's natural language description into a single, structured JSON object that can be added to a knowledge base.

The JSON object must have the following fields:
- "doc_id": A unique and descriptive identifier based on the content (e.g., "lab_2023-10-26_Lipids_Total_Cholesterol").
- "text": A comprehensive, human-readable summary of the information provided.
- "metadata": A JSON object containing key-value pairs of the most important structured data (e.g., "date", "test", "value", "units").

Here are some examples of the final JSON format:
```
{{"doc_id":"lab_2025-02-15_Hematology_WBC","text":"Date: 2025-02-15\nCategory: Lab Work\nSub Category: Hematology\nTest: WBC\nResult: 6.4\nUnits: x E9/L\nReference: 4.0 - 11.0","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Hematology","test":"WBC"}}}}
{{"doc_id":"supplement_Niacin","text":"Supplement: Niacin\nDose: 500 mg\nEffects:\n - Cardiovascular: Can raise HDL (good cholesterol) and lower triglycerides...","metadata":{{"supplement":"Niacin","dose":500,"units":"mg"}}}}
```

Now, analyze the user's request below and generate a single, complete JSON object. If the user's request is a follow-up to a previous attempt, use the conversation history to refine the JSON object. Respond with ONLY the single JSON object.

Conversation History (for context):
```{history}```

User's Request:
```{user_input}```
""" 