import structlog
import asyncio
from langsmith import traceable
from app.types import AppState
from app.models.candidate import Candidate
from sqlalchemy.orm import Session
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
import re
import json

logger = structlog.get_logger()

async def parse_single_resume(resume: dict, llm_chain: RunnableSequence, db: Session) -> dict:
    """Helper function to parse a single resume and update the database."""
    file_name = resume.get("file_name")
    content = resume.get("content", "")
    candidate_id = resume.get("candidate_id")
    logger.info(f"[AGENT 2: PARSER] - Processing resume: {file_name}")

    if not content or not candidate_id:
        logger.warning(f"[AGENT 2: PARSER] - Skipping resume {file_name}: missing content or candidate_id")
        return None

    try:
        # Parse the resume using the LLM
        result = await llm_chain.ainvoke({"resume_text": content})
        parsed_data = result.content  # Gemini returns the raw JSON string

        # Clean and parse the JSON output
        parsed_data = re.sub(r"```json\n|\n```", "", parsed_data).strip()
        parsed_info = json.loads(parsed_data)

        # Update the candidate in the database
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.name = parsed_info.get("name", "")
            candidate.email = parsed_info.get("email", "")
            candidate.phone = parsed_info.get("phone", "")
            candidate.skills = parsed_info.get("skills", "")
            candidate.experience = parsed_info.get("experience", "")
            candidate.education = parsed_info.get("education", "")
            candidate.certifications = parsed_info.get("certifications", "")
            candidate.passedout_year = parsed_info.get("passedout_year", "")
            candidate.cgpa = parsed_info.get("cgpa", "")
            candidate.percentage_10th = parsed_info.get("percentage_10th", "")
            candidate.percentage_12th = parsed_info.get("percentage_12th", "")
            candidate.sex = parsed_info.get("sex", "")
            candidate.location = parsed_info.get("location", "")
            candidate.internships = parsed_info.get("internships", "")
            candidate.agent_step = "resume_parser"
            db.flush()

        parsed_resume = {
            "file_name": file_name,
            "candidate_id": candidate_id,
            "name": parsed_info.get("name", ""),
            "email": parsed_info.get("email", ""),
            "phone": parsed_info.get("phone", ""),
            "skills": parsed_info.get("skills", ""),
            "experience": parsed_info.get("experience", ""),
            "education": parsed_info.get("education", ""),
            "certifications": parsed_info.get("certifications", ""),
            "passedout_year": parsed_info.get("passedout_year", ""),
            "cgpa": parsed_info.get("cgpa", ""),
            "percentage_10th": parsed_info.get("percentage_10th", ""),
            "percentage_12th": parsed_info.get("percentage_12th", ""),
            "sex": parsed_info.get("sex", ""),
            "location": parsed_info.get("location", ""),
            "internships": parsed_info.get("internships", ""),
            "classification": None,
            "matched_role": None,
            "match_score": None,
            "score": None,
            "final_score": None,
            "email_sent": None
        }

        logger.info(f"[AGENT 2: PARSER] - Successfully parsed resume: {file_name}", parsed_data=parsed_resume)
        return parsed_resume
    except Exception as e:
        logger.error(f"[AGENT 2: PARSER] - Failed to parse resume: {file_name}", error=str(e))
        return None

@traceable
async def resume_parser(state: AppState, config: dict = None) -> AppState:
    logger.info("[AGENT 2: PARSER] - Starting parsing...")
    # Remove detailed state logging
    # logger.info(f"[AGENT 2: PARSER] - State received (type: {type(state)}): {state}")

    db = state.get("db")
    if not isinstance(db, Session):
        logger.error("[AGENT 2: PARSER] - Database session not found in state")
        raise ValueError("Database session not found in state")

    llm = state.get("llm")
    if not llm:
        logger.error("[AGENT 2: PARSER] - No LLM instance found in state")
        raise ValueError("LLM instance not found in state")

    resumes = state.get("resumes", [])
    if not resumes:
        logger.warning("[AGENT 2: PARSER] - No resumes to parse")
        state["parsed_resumes"] = []
        return state

    prompt_template = PromptTemplate(
        input_variables=["resume_text"],
        template=(
            "Extract the following information from the resume in a structured JSON format:\n"
            "- name: The candidate's full name.\n"
            "- email: The candidate's email address.\n"
            "- phone: The candidate's phone number.\n"
            "- skills: A comma-separated list of skills (e.g., 'Python, Java, SQL').\n"
            "- experience: The candidate's experience (e.g., '5 years', '1 year as Developer').\n"
            "- education: The candidate's highest degree with college and year (e.g., 'B.Tech, XYZ College, 2020').\n"
            "- certifications: Any certifications (e.g., 'Python for Data Science (Elysium Academy)').\n"
            "- passedout_year: The graduation year of the highest degree (e.g., '2020').\n"
            "- cgpa: The CGPA or percentage of the highest degree (e.g., '8.5 (CGPA)').\n"
            "- percentage_10th: The 10th grade percentage (e.g., '85').\n"
            "- percentage_12th: The 12th grade percentage (e.g., '90').\n"
            "- sex: The candidate's sex if mentioned (e.g., 'Male', 'Female').\n"
            "- location: The candidate's city and country (e.g., 'Chennai, India').\n"
            "- internships: Internship details (e.g., 'AI Intern at XYZ Corp (2018-2019)').\n"
            "Return the extracted information as a JSON object. If a field cannot be found, return an empty string for that field.\n\n"
            "Resume:\n{resume_text}\n\n"
            "Output in JSON format:"
        )
    )

    llm_chain = prompt_template | llm
    tasks = [parse_single_resume(resume, llm_chain, db) for resume in resumes]
    parsed_resumes = await asyncio.gather(*tasks)

    parsed_resumes = [resume for resume in parsed_resumes if resume is not None]
    db.commit()

    state["parsed_resumes"] = parsed_resumes
    logger.info("[AGENT 2: PARSER] - Parsing complete", parsed_count=len(parsed_resumes))
    return state