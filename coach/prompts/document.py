"""Document processing prompt templates."""

DOCUMENT_STRUCTURE_PROMPT_TEMPLATE = """You are an expert at extracting ONLY laboratory test results from medical documents. Your task is to analyze the raw text and convert ONLY test results into structured JSON objects.

IMPORTANT FILTERING RULES:
- Extract ONLY laboratory test results from the document
- DO NOT create records for:
  • Patient demographic information (name, DOB, phone, address, ID numbers)
  • Healthcare provider or physician information
  • Laboratory facility details or contact information  
  • Report headers, footers, page numbers, or administrative metadata
  • General notes, disclaimers, or instructions
  • Collection dates, report dates, or other non-test data

A valid test result MUST have:
- Test name (e.g., "WBC", "Glucose", "Total Cholesterol")
- Result value (numeric or qualitative result like "<0.5" or "Negative")
- Optional: Units, reference range, flags

If it doesn't have both a test name AND result value, don't create a record for it.

The JSON object must have the following fields:
- "doc_id": A unique identifier for the test. Create a meaningful ID based on the content, including category, sub-category, and test name (e.g., "lab_2025-08-29_Hematology_ESR").
- "text": The full, original text for this specific test result including the test name, value, units, and reference range.
- "metadata": An object containing key-value pairs of metadata for this test (e.g., "date", "category", "sub_category", "test").

For grouped tests (e.g., under "Hematology" or "Serum Proteins" sections):
- Create individual records for each test within the group
- Use the section name as the sub_category in metadata

Examples (NOTE: Only test results are extracted, even if source contains patient info or other data):
```
{{"doc_id":"lab_2025-08-29_Hematology_ESR","text":"Test: Erythrocyte Sedimentation Rate\nResult: 2\nUnits: mm/hr\nReference: 2 - 30","metadata":{{"date":"2025-08-29","category":"Lab Work","sub_category":"Hematology","test":"Erythrocyte Sedimentation Rate"}}}}
{{"doc_id":"lab_2025-08-29_Serum_Proteins_CRP","text":"Test: C Reactive Protein\nResult: <0.5\nUnits: mg/L\nReference: <5.0","metadata":{{"date":"2025-08-29","category":"Lab Work","sub_category":"Serum Proteins","test":"C Reactive Protein"}}}}
{{"doc_id":"lab_2025-08-29_Immunology_Rheumatoid_Factor","text":"Test: Rheumatoid Factor\nResult: <19\nUnits: IU/mL\nReference: Negative: <30 IU/mL","metadata":{{"date":"2025-08-29","category":"Lab Work","sub_category":"Immunology","test":"Rheumatoid Factor"}}}}
{{"doc_id":"lab_2025-02-15_Hematology_WBC","text":"Test: WBC\nResult: 6.4\nUnits: x E9/L\nReference: 4.0 - 11.0","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Hematology","test":"WBC"}}}}
{{"doc_id":"lab_2025-02-15_Hematology_RBC","text":"Test: RBC\nResult: 4.75\nUnits: x E12/L\nReference: 4.50 - 6.00","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Hematology","test":"RBC"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_Total_Cholesterol","text":"Test: Total Cholesterol\nResult: 5.8\nUnits: mmol/L\nReference: <5.2","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"Total Cholesterol"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_LDL","text":"Test: LDL\nResult: 3.7\nUnits: mmol/L\nReference: <3.3","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"LDL"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_HDL","text":"Test: HDL\nResult: 1.1\nUnits: mmol/L\nReference: >1.0","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"HDL"}}}}
{{"doc_id":"lab_2025-02-15_Cardiac_Risk_Triglycerides","text":"Test: Triglycerides\nResult: 1.9\nUnits: mmol/L\nReference: <1.7","metadata":{{"date":"2025-02-15","category":"Lab Work","sub_category":"Cardiac Risk","test":"Triglycerides"}}}}
```

## Output Instructions:

When using the DocumentBatch tool:
- Provide a "documents" array containing extracted test results
- Each document should have doc_id, text, and metadata fields as shown in examples

When outputting raw JSONL (fallback mode):
- Generate one or more JSON objects like the examples above
- Output one JSON object per line, no markdown formatting

REMEMBER: Extract ONLY test results with test names and values. Ignore all patient information, lab information, headers, footers, and any non-test data.

```{raw_text}```
"""