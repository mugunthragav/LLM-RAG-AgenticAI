from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings

def create_vector_store(chunks, embedding_model):
    print("📌 [Vector Store] Creating FAISS index...")
    vector_store = FAISS.from_texts(chunks, embedding_model)
    print("✅ [Vector Store] FAISS index created.")
    return vector_store
