"""Document processing prompt templates."""

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