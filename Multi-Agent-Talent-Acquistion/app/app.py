import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from langchain_openai import ChatOpenAI  
from app.types import AppState
from sqlalchemy.orm import Session
from app.models.candidate import Candidate, Base
from app.database import engine, SessionLocal, get_db
from app.workflow import run_workflow_with_visualization
import logging
import io
import uuid
from dotenv import load_dotenv
import re
from docx import Document
import csv
import pymupdf
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable not set")
    raise ValueError("OPENAI_API_KEY environment variable must be set")

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Initialize the OpenAI GPT-4 model
try:
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        openai_api_key=OPENAI_API_KEY,
        temperature=0
    )
    logger.info("OpenAI GPT-4 model initialized successfully via LangChain")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI GPT-4 model: {str(e)}")
    llm = None

# Function to extract skills from job description text
def extract_skills(text):
    # Match the skills section after "Requires skills in"
    skills_section = re.search(r'Requires skills in (.*?)(?:\s*\.|$)', text, re.IGNORECASE | re.DOTALL)
    if not skills_section:
        return []
    
    skills_text = skills_section.group(1).strip()
    if not skills_text:
        return []
    
    # Replace " or " and " and " with commas for consistent splitting
    skills_text = skills_text.replace(" or ", ", ").replace(" and ", ", ").replace("HTML/CSS", "HTML, CSS")
    
    # Handle nested parentheses by extracting them separately
    final_skills = []
    current_skill = ""
    inside_parens = False
    for char in skills_text:
        if char == '(':
            inside_parens = True
            if current_skill.strip():
                final_skills.append(current_skill.strip())
            current_skill = ""
        elif char == ')':
            inside_parens = False
            if current_skill.strip():
                # Split contents inside parentheses by commas
                sub_skills = [s.strip() for s in current_skill.split(",") if s.strip()]
                final_skills.extend(sub_skills)
            current_skill = ""
        elif char == ',' and not inside_parens:
            if current_skill.strip():
                final_skills.append(current_skill.strip())
            current_skill = ""
        else:
            current_skill += char
    
    # Add the last skill if exists
    if current_skill.strip():
        final_skills.append(current_skill.strip())
    
    # Clean up skills (remove duplicates and empty strings)
    final_skills = list(dict.fromkeys([skill for skill in final_skills if skill]))
    return final_skills

# Load job descriptions from data/jds.csv with updated min_exp and max_exp extraction
jds_path = "data/jds.csv"
try:
    jds_df = pd.read_csv(jds_path, quoting=csv.QUOTE_ALL, on_bad_lines="warn")
    logger.info(f"Columns in jds.csv: {list(jds_df.columns)}")
    logger.info(f"Loaded DataFrame:\n{jds_df}")
    if "role" not in jds_df.columns or "text" not in jds_df.columns:
        raise KeyError("Required columns 'role' and 'text' not found in jds.csv")

    job_descriptions_raw = jds_df.to_dict("records")
    job_roles = []
    job_skills = []

    for jd in job_descriptions_raw:
        role = jd["role"]
        text = jd["text"]
        # Extract skills using the new function
        skills = extract_skills(text)
        if not skills:
            logger.warning(f"No skills found in text: {text}")
        jd["skills"] = skills

        # Extract min_exp and max_exp
        exp_match = re.search(r"(\d+)-(\d+)\s*years?", text, re.IGNORECASE)
        if exp_match:
            jd["min_exp"] = int(exp_match.group(1))
            jd["max_exp"] = int(exp_match.group(2))
        else:
            jd["min_exp"] = 0
            jd["max_exp"] = 1  # Default for most roles, overridden for UI/UX Designer
            if "UI/UX Designer" in jd["role"]:
                jd["max_exp"] = 3

        job_roles.append(role)
        job_skills.append(jd["skills"])
        logger.info(f"Role: {role}, Extracted Skills: {jd['skills']}, Min Exp: {jd['min_exp']}, Max Exp: {jd['max_exp']}")

except FileNotFoundError:
    logger.error(f"jds.csv not found at path: {jds_path}")
    raise
except pd.errors.ParserError as e:
    logger.error(f"Error parsing jds.csv: {str(e)}")
    jds_df = pd.DataFrame(columns=["id", "role", "text"])
    job_roles = []
    job_skills = []
    job_descriptions_raw = []
except KeyError as e:
    logger.error(f"Column error in jds.csv: {str(e)}")
    raise

@app.post("/upload-resumes/")
async def upload_resumes(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """Endpoint to upload and process resumes."""
    # Generate a task ID for this request
    task_id = str(uuid.uuid4())

    try:
        # Step 1: Extract content from uploaded files using pymupdf directly
        state = AppState(
            task_id=task_id,
            resumes=[],
            job_roles=job_roles,
            job_skills=job_skills,
            job_descriptions_raw=job_descriptions_raw,
            llm=llm,
            db=db
        )

        for file in files:
            content = await file.read()
            file_like = io.BytesIO(content)

            try:
                if file.filename.lower().endswith('.pdf'):
                    doc = pymupdf.open(stream=content, filetype="pdf")
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    doc.close()
                elif file.filename.lower().endswith('.docx'):
                    doc = Document(file_like)
                    text = "\n".join([para.text for para in doc.paragraphs])
                else:
                    logger.error(f"Unsupported file format: {file.filename}")
                    continue

                state["resumes"].append({"file_name": file.filename, "content": text})
            except Exception as e:
                logger.error(f"Failed to extract content from {file.filename}: {str(e)}")
                continue

        if not state["resumes"]:
            raise HTTPException(status_code=400, detail="No valid resumes uploaded")

        # Step 2: Run the LangGraph workflow
        final_state = await run_workflow_with_visualization(state, llm, db)

        # Step 3: Process the final results
        scheduled_resumes = final_state.get("scheduled_resumes", [])
        resumes_data = []
        processed_candidates = []

        for candidate in scheduled_resumes:
            resumes_data.append({
                "file_name": candidate["file_name"],
                "name": candidate["name"],
                "skills": candidate["skills"],
                "experience": candidate["experience"],
                "passout_year": candidate["passedout_year"]
            })

            processed_candidates.append({
                "year": candidate["passedout_year"],
                "internships": candidate["internships"] or "None",
                "sex": candidate["sex"] or "None",
                "classification": candidate["classification"],
                "matched_role": candidate["matched_role"],
                "match_score": candidate["match_score"],
                "score": candidate["final_score"],
                "email_sent": candidate.get("email_status", "None"),
                "rejection_reason": candidate.get("rejection_reason", "None")
            })

        # Include intermediate states in the response for debugging
        response = {
            "task_id": task_id,
            "resumes": resumes_data,
            "processed": processed_candidates,
            "intermediate_states": {
                "parsed_resumes": final_state.get("parsed_resumes", []),
                "classified_candidates": final_state.get("classified_candidates", []),
                "matched_candidates": final_state.get("matched_candidates", []),
                "scored_resumes": final_state.get("scored_resumes", [])
            }
        }

        return response

    except Exception as e:
        logger.error(f"Error in upload_resumes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/candidates/")
async def get_candidates(task_id: str, db: Session = Depends(get_db)):
    """Endpoint to retrieve processed candidates by task_id."""
    try:
        candidates = db.query(Candidate).filter(Candidate.task_id == task_id).all()
        if not candidates:
            raise HTTPException(status_code=404, detail=f"No candidates found for task_id: {task_id}")

        resumes_data = []
        processed_candidates = []
        for candidate in candidates:
            resumes_data.append({
                "file_name": candidate.file_name,
                "name": candidate.name,
                "skills": candidate.skills,
                "experience": candidate.experience,
                "passout_year": candidate.passedout_year
            })
            processed_candidates.append({
                "year": candidate.passedout_year,
                "internships": candidate.internships or "None",
                "sex": candidate.sex or "None",
                "classification": candidate.classification,
                "matched_role": candidate.matched_role,
                "match_score": candidate.match_score,
                "score": candidate.final_score,
                "email_sent": "Sent to HR" if candidate.email_sent else "None",
                "rejection_reason": candidate.rejection_reason or "None"
            })

        return {
            "task_id": task_id,
            "resumes": resumes_data,
            "processed": processed_candidates
        }

    except Exception as e:
        logger.error(f"Error in get_candidates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")