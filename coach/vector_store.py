import os, pickle
import faiss
import numpy as np
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# text-embedding-3-small has 1536 dimensions
# text-embedding-3-large has 3072 dimensions
# text-embedding-ada-002 has 1536 dimensions
EMBEDDING_MODEL = "text-embedding-3-large"  # or "text-embedding-3-small"
VECTOR_DIM = 3072  # Make sure this matches your embedding model's output dimension

class PersistentVectorStore:
    def __init__(self, store_folder="vector_store_data", index_filename="faiss_index.bin", docs_filename="documents.pkl"):
        """
        Initializes the vector store by optionally specifying a folder in which to save the index and documents.
        If the folder does not exist, it will be created.
        """
        self.store_folder = store_folder
        if not os.path.exists(store_folder):
            os.makedirs(store_folder)
            print(f"Created folder: {store_folder}")
        
        self.index_path = os.path.join(store_folder, index_filename)
        self.docs_path = os.path.join(store_folder, docs_filename)
        self.dimension = VECTOR_DIM
        
        if os.path.exists(self.index_path) and os.path.exists(self.docs_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.docs_path, "rb") as f:
                self.documents = pickle.load(f)
            print(f"Loaded existing vector store with {len(self.documents)} documents.")
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            self.documents = []
            print("Initialized new vector store.")

    def get_embedding(self, text):
        """Get embedding for text using OpenAI's API"""
        response = client.embeddings.create(
            input=[text],
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding

    def add_document(self, doc_id, text, metadata=None):
        """Add a document to the vector store"""
        print(f"Adding document with ID: {doc_id}")
        embedding = self.get_embedding(text)
        embedding_np = np.array(embedding, dtype=np.float32).reshape(1, -1)
        assert embedding_np.shape[1] == self.dimension, f"Embedding dimension {embedding_np.shape[1]} does not match index dimension {self.dimension}"
        self.index.add(embedding_np)
        self.documents.append({"doc_id": doc_id, "text": text, "metadata": metadata})
        print(f"Successfully added document. Total documents: {len(self.documents)}")

    def save(self):
        """Save the vector store (both index and documents) to the specified folder."""
        faiss.write_index(self.index, self.index_path)
        with open(self.docs_path, "wb") as f:
            pickle.dump(self.documents, f)
        print(f"Saved vector store with {len(self.documents)} documents in folder {self.store_folder}.")

    def search(self, query, top_k=5, nprobe=20):
        """
        Search for similar documents.
        nprobe: Number of clusters to search (higher = more accurate but slower)
        top_k: Number of top documents to retrieve (increase if not retrieving enough content)
        """
        self.index.nprobe = nprobe  # Set number of clusters to search
        query_embedding = self.get_embedding(query)
        query_np = np.expand_dims(query_embedding, axis=0)
        distances, indices = self.index.search(query_np, top_k)
        results = []
        for idx in indices[0]:
            if idx < len(self.documents):
                results.append(self.documents[idx])
        return results