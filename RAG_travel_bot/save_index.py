# save_index.py
from datasets import load_dataset
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import time

# Silence warnings
import logging

logging.getLogger("langchain.text_splitter").setLevel(logging.ERROR)

# Load Ollama embeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Define FAISS index path
faiss_index_path = "faiss_index"


# Load Bitext Travel dataset from Hugging Face
def load_bitext_travel_data():
    print("Loading Bitext Travel dataset from Hugging Face...")
    dataset = load_dataset("bitext/Bitext-travel-llm-chatbot-training-dataset", split="train")
    # Convert to text: "Q: {instruction} A: {response}"
    text_data = "\n".join([f"Q: {item['instruction']} A: {item['response']}" for item in dataset])
    return text_data


TRAVEL_DATA = load_bitext_travel_data()


# Build and save FAISS index
def create_faiss_index():
    start_time = time.time()

    print("Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_text(TRAVEL_DATA)
    print(f"Created {len(texts)} chunks.")

    print("Generating embeddings and building FAISS index...")
    vectorstore = FAISS.from_texts(texts, embeddings)

    print("Saving FAISS index...")
    vectorstore.save_local(faiss_index_path)

    end_time = time.time()
    print(f"FAISS index saved to {faiss_index_path}. Took {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    # Delete old index if exists
    if os.path.exists(faiss_index_path):
        import shutil

        shutil.rmtree(faiss_index_path)
    create_faiss_index()