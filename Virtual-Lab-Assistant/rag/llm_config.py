from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from openai import OpenAI
import logging
import os
import difflib
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Logger Configuration
llm_logger = logging.getLogger("llm_config")
llm_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("logs/llm_config_logs.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
llm_logger.addHandler(file_handler)

# Validate and assign OpenAI key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")
Api_key = api_key.strip()
client = OpenAI(api_key=Api_key)
llm_logger.info("OpenAI API key loaded successfully.")

# Database credentials
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_NAME = os.getenv("DB_NAME")
DB_PASS = os.getenv("DB_PASS")

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASS, database=DB_NAME
        )
    except mysql.connector.Error as e:
        llm_logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed.")

class QueryRequest(BaseModel):
    intent: str
    query: str

class GPTQueryRequest(BaseModel):
    query: str

# Intent to DB mapping
table_map = {
    "check_parameter_limits": ("parameter_limits", "parameter_name", "min_value", "max_value", "unit"),
    "get_safety_guidelines": ("lab_safety_guidelines", "question", "response"),
    "get_emergency_procedure": ("emergency_procedures", "scenario", "action"),
    "check_performance_metrics": ("performance_metrics", "parameter_name", "min_value", "max_value", "unit"),
    "available_labs": ("lab_availability", "lab_name", "status"),
    "lab_equipment": ("lab_equipment", "name", "location"),
    "experiment_help": ("experiment_procedures", "experiment_name", "step"),
}


FUZZY_CUTOFF = 0.6

def query_database(query, params=()):
    try:
        with get_db_connection() as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
    except mysql.connector.Error as e:
        llm_logger.error(f"Database query error: {e}")
        return []
    
@app.post("/fetch_dynamic_response/")
def fetch_dynamic_response(request: QueryRequest):
    if request.intent not in table_map:
        llm_logger.warning(f"Invalid intent: {request.intent}")
        return {"response": "I don't have information for that intent."}

    table_info = table_map[request.intent]
    table_name, column_name = table_info[:2]
    normalized_query = request.query.strip().lower()
    llm_logger.info(f"Normalized query: {normalized_query}")

    common_words = ['is', 'a', 'good', 'safe', 'within', 'the', 'for', 'check', 'if', 'okay', 'what', 'range', 'can', 'you']
    query_terms = re.sub(r'\d+\.?\d*\s*[wWvV%°c]?', '', normalized_query)
    query_terms = ' '.join(w for w in query_terms.split() if w not in common_words).strip()
    query_keywords = [k for k in query_terms.split() if len(k) > 2]
    llm_logger.info(f"Query keywords: {query_keywords}")

    match = None

    # Try keyword-based partial match
    for keyword in query_keywords:
        match = query_database(f"SELECT * FROM {table_name} WHERE LOWER({column_name}) LIKE %s", ('%' + keyword + '%',))
        if match:
            break

    # Try fuzzy match if no exact match
    if not match:
        results = query_database(f"SELECT {column_name} FROM {table_name}")
        options = [row[column_name].lower() for row in results if row[column_name]]
        for keyword in query_keywords:
            closest = difflib.get_close_matches(keyword, options, n=1, cutoff=FUZZY_CUTOFF)
            if closest:
                match = query_database(f"SELECT * FROM {table_name} WHERE {column_name} = %s", (closest[0],))
                if match:
                    break

    # Intent-specific logic
    if request.intent in ["check_parameter_limits", "check_performance_metrics"]:
        if match:
            row = match[0]
            param_value = extract_parameter_value(request.query)
            if param_value is not None:
                min_val = float(row["min_value"])
                max_val = float(row["max_value"])
                if min_val <= param_value <= max_val:
                    return {"response": f"Yes, {param_value} {row.get('unit', '')} is within the safe range for {row[column_name]} ({min_val} to {max_val} {row.get('unit', '')})."}
                return {"response": f"No, {param_value} {row.get('unit', '')} is outside the safe range for {row[column_name]} ({min_val} to {max_val} {row.get('unit', '')})."}
            return {"response": f"The safe range for {row[column_name]} is {row['min_value']} to {row['max_value']} {row.get('unit', '')}."}

    elif request.intent == "available_labs":
        all_labs = query_database(f"SELECT {column_name}, status FROM {table_name}")
        
        # Check if any lab name is mentioned in the query
        for row in all_labs:
            lab_name = row[column_name].lower()
            if lab_name in normalized_query:
                return {"response": f"{row[column_name]} is currently {row['status']}."}

        # Try fuzzy match for lab name
        lab_names = [row[column_name].lower() for row in all_labs]
        closest = difflib.get_close_matches(normalized_query, lab_names, n=1, cutoff=0.6)
        if closest:
            for row in all_labs:
                if row[column_name].lower() == closest[0]:
                    return {"response": f"{row[column_name]} is currently {row['status']}."}

        # Else return list of available labs
        available = [row[column_name] for row in all_labs if row["status"].lower() == "available"]
        return {"response": "Available labs: " + ", ".join(available) if available else "No labs currently available."}

    elif request.intent == "lab_equipment":
        if match:
            row = match[0]
            return {"response": f"The {row[column_name]} is located at: {row.get('location', 'Location not available')}"}

    elif request.intent == "experiment_help":
        if match:
            row = match[0]
            steps = query_database(f"SELECT step FROM {table_name} WHERE {column_name} = %s ORDER BY id ASC", (row[column_name],))
            if steps:
                return {"response": f"Here are the steps for {row[column_name]}:\n" + "\n".join(f"- {s['step']}" for s in steps)}
            return {"response": f"No experiment steps found for {row[column_name]}."}

    elif match:
        row = match[0]
        return {"response": row.get("response", row.get("action", "No valid response found."))}

    return {"response": "I couldn't find a matching entry in the database. Trying a best guess from LLM..."}


@app.post("/fetch_gpt_response/")
def fetch_gpt_response(request: GPTQueryRequest):
    try:
        llm_logger.info(f"Calling GPT for query: {request.query}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant for fuel cell testing."},
                {"role": "user", "content": request.query}
            ]
        )
        reply = response.choices[0].message.content
        llm_logger.info(f"GPT Response: {reply[:100]}...")
        return {"response": reply}
    except Exception as e:
        llm_logger.error(f"OpenAI API error for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail="LLM API failed.")
