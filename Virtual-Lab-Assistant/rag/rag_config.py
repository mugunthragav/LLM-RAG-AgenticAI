
import logging
import os
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import faiss

# Load environment variables
load_dotenv()

# Logger Configuration
rag_logger = logging.getLogger("rag_config")
rag_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("logs/rag_config_logs.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
rag_logger.addHandler(file_handler)

# Validate and assign API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")
client = OpenAI(api_key=api_key.strip())

# Define FAISS index path
faiss_index_path = os.path.join(os.path.dirname(__file__), "faiss_index")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Retriever class
class Retriever:
    def __init__(self):
        self.index = None
        self.texts = []
        self._load_index()

    def _load_index(self):
        try:
            if os.path.exists(faiss_index_path):
                self.index = faiss.read_index(os.path.join(faiss_index_path, "index.faiss"))
                with open(os.path.join(faiss_index_path, "texts.txt"), "r", encoding="utf-8") as f:
                    self.texts = f.read().split("\n---\n")[:-1]
                rag_logger.info(f"FAISS index loaded successfully. {len(self.texts)} texts loaded.")
            else:
                raise RuntimeError("FAISS index not found. Run pdf_loader.py first.")
        except Exception as e:
            rag_logger.error(f"FAISS Load Error: {e}")
            raise

    def retrieve(self, query, k=2):
        if not self.index:
            rag_logger.error("FAISS index not loaded.")
            return []
        query_embedding = model.encode([query])
        distances, indices = self.index.search(query_embedding, k)
        rag_logger.info(f"Retrieved indices: {indices[0]} with distances: {distances[0]}")
        valid_indices = [i for i in indices[0] if 0 <= i < len(self.texts)]
        return [self.texts[i] for i in valid_indices]

# Initialize app
app = FastAPI()

# Initialize retriever
try:
    retriever = Retriever()
except Exception as e:
    rag_logger.error(f"Failed to initialize Retriever: {e}")
    raise RuntimeError("Retriever initialization failed. Ensure FAISS index exists.")

@app.get("/rag_query/")
async def rag_query(query: str):
    try:
        docs = retriever.retrieve(query, k=2)
        if not docs:
            rag_logger.info(f"No relevant documents found for query: {query}")
            return {"response": "No relevant document found."}

        context = "\n".join(docs)
        rag_logger.info(f"Retrieved context: {context[:100]}...")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant for fuel cell testing. Use the provided context to answer."},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
            ],
            max_tokens=150,
        )
        reply = response.choices[0].message.content
        rag_logger.info(f"RAG Response: {reply[:100]}...")
        return {"response": reply}
    except Exception as e:
        rag_logger.error(f"RAG Error for query '{query}': {e}")
        return {"response": "No relevant document found."}
