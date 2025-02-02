# coach/utils.py
import json

def load_docs_from_jsonl(file_path):
    docs = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs

def update_vector_store_from_docs(vector_store, docs):
    existing_ids = {doc["doc_id"] for doc in vector_store.documents}
    for doc in docs:
        if doc["doc_id"] not in existing_ids:
            vector_store.add_document(doc["doc_id"], doc["text"], doc.get("metadata"))
        else:
            #print(f"Document {doc['doc_id']} already exists. Skipping.")
            continue
