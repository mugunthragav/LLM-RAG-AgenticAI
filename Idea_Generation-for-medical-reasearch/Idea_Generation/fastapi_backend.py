from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from futurehouse_client import FutureHouseClient, JobNames
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os, asyncio, time, hashlib

# Load environment variables
load_dotenv()
FUTUREHOUSE_API_KEY = os.getenv("FUTUREHOUSE_API_KEY")
if not FUTUREHOUSE_API_KEY:
    raise ValueError("FUTUREHOUSE_API_KEY not set in .env file.")

# Initialize FastAPI app
app = FastAPI(
    title="Clinical Research Chatbot Backend",
    version="2.0",
    description="Optimized backend using FutureHouse API"
)

# Enable CORS for frontend communication from any origin (safe for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider specifying exact origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize FutureHouse client
fh_client = FutureHouseClient(api_key=FUTUREHOUSE_API_KEY)

# In-memory cache
response_cache = {}

MAX_PROMPT_LENGTH = 400

class ResearchQuery(BaseModel):
    query: str

def truncate_prompt(text: str, max_length: int = MAX_PROMPT_LENGTH) -> str:
    return text.strip()[:max_length] + "..." if len(text) > max_length else text.strip()

def get_query_hash(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

async def call_futurehouse_with_retry(task_data, retries=3, delay=2):
    for attempt in range(retries):
        try:
            start = time.time()
            task_results = await fh_client.arun_tasks_until_done([task_data])
            duration = time.time() - start
            print(f"[✅] API call completed in {duration:.2f}s")
            return task_results
        except Exception as e:
            if "429" in str(e):
                wait_time = delay * (attempt + 1)
                print(f"[⚠️] Rate limited. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"[❌] API call failed: {e}")
                raise HTTPException(status_code=500, detail="FutureHouse API call failed.")
    raise HTTPException(status_code=429, detail="Too many requests. Try again later.")

@app.post("/api/research_summary")
async def get_research_summary_endpoint(rq: ResearchQuery):
    original_query = rq.query
    if not original_query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    trimmed_query = truncate_prompt(original_query)
    query_hash = get_query_hash(trimmed_query)

    if query_hash in response_cache:
        print("[CACHE HIT]")
        return {"status": "success", "summary": response_cache[query_hash], "cached": True}

    print("[CACHE MISS] Processing new query...")

    task_data = {
        "name": JobNames.CROW,
        "query": trimmed_query
    }

    total_start = time.time()
    task_results = await call_futurehouse_with_retry(task_data)
    total_duration = time.time() - total_start
    print(f"[📊] Total backend processing time: {total_duration:.2f}s")

    if task_results and task_results[0].has_successful_answer:
        summary = task_results[0].answer
        response_cache[query_hash] = summary
        return {"status": "success", "summary": summary, "cached": False}
    else:
        return {
            "status": "no_answer",
            "summary": "No definitive answer found. Try rephrasing your query.",
            "cached": False
        }

@app.get("/")
async def root():
    return {"message": "Clinical Research Chatbot API is running"}
