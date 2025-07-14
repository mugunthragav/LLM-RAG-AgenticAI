import structlog
import asyncio
from langsmith import traceable
from app.models.candidate import Candidate
from langchain.prompts import PromptTemplate
from sqlalchemy.orm import Session
from app.types import AppState
from typing import Any

logger = structlog.get_logger()

async def classify_candidate(candidate: dict, llm: Any, db: Session) -> dict:
    """Helper function to classify a single candidate."""
    file_name = candidate.get("file_name")
    candidate_id = candidate.get("candidate_id")
    logger.info(f"[AGENT 3: CLASSIFIER] - Classifying candidate: {file_name}")

    try:
        resume_summary = (
            f"Name: {candidate['name'] or 'Unknown'}\n"
            f"Skills: {candidate['skills'] or 'None'}\n"
            f"Experience: {candidate['experience'] or 'None'}\n"
            f"Education: {candidate['education'] or 'None'}\n"
            f"Certifications: {candidate['certifications'] or 'None'}\n"
            f"Internships: {candidate['internships'] or 'None'}"
        )

        prompt_template = PromptTemplate(
            input_variables=["resume_summary"],
            template=(
                "You are an expert in talent acquisition. Based on the candidate's resume summary below, classify the candidate into one of the following job roles:\n"
                "- Data Scientist: Requires skills in Python, R, statistics, machine learning, deep learning, NLP, AI, or data visualization.\n"
                "- Backend Developer: Requires skills in Node.js, MongoDB, Java, JavaScript, or Spring Boot.\n"
                "- Frontend Developer: Requires skills in React, JavaScript, HTML, CSS, or Angular.\n"
                "- Machine Learning Engineer: Requires skills in supervised learning, unsupervised learning, reinforcement learning, TensorFlow, or PyTorch.\n"
                "- UI/UX Designer: Requires skills in HTML, CSS, Adobe XD, Figma, wireframing, or Sketch.\n"
                "- Data Analyst: Requires skills in SQL, Tableau, R, Python, statistical programming, Excel, machine learning, or data visualization.\n"
                "- Unclassified: If no role matches.\n\n"
                "Return ONLY the job role as a string. Do not include any additional text or explanations.\n\n"
                "Resume summary:\n{resume_summary}\n\n"
                "Job role:"
            )
        )

        prompt = prompt_template.format(resume_summary=resume_summary)
        response = await llm.ainvoke(prompt)
        job_role = response.content.strip()

        # Update the database
        db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if db_candidate:
            db_candidate.classification = job_role
            db_candidate.agent_step = "classifier"
            db.flush()

        candidate_data = candidate.copy()
        candidate_data["classification"] = job_role
        logger.info(f"[AGENT 3: CLASSIFIER] - Classified candidate: {file_name} as {job_role}")
        return candidate_data
    except Exception as e:
        logger.error(f"[AGENT 3: CLASSIFIER] - Failed to classify candidate: {file_name}", error=str(e))
        candidate["classification"] = "Unclassified"
        return candidate

@traceable(run_type="chain")
async def classifier(state: AppState, config: dict = None) -> AppState:
    logger.info("[AGENT 3: CLASSIFIER] - Starting classification...")
    # Remove detailed state logging
    # logger.info(f"[AGENT 3: CLASSIFIER] - State received (type: {type(state)}): {state}")

    db = state.get("db")
    if not isinstance(db, Session):
        logger.error("[AGENT 3: CLASSIFIER] - Database session not found in state")
        raise ValueError("Database session not found in state")

    llm = state.get("llm")
    if not llm:
        logger.error("[AGENT 3: CLASSIFIER] - No LLM instance found in state")
        raise ValueError("LLM instance not found in state")

    parsed_resumes = state.get("parsed_resumes", [])
    if not isinstance(parsed_resumes, list):
        logger.error("[AGENT 3: CLASSIFIER] - Parsed resumes must be a list")
        raise ValueError("Parsed resumes must be a list")

    tasks = [classify_candidate(resume, llm, db) for resume in parsed_resumes]
    classified_candidates = await asyncio.gather(*tasks)

    db.commit()

    state["classified_candidates"] = classified_candidates
    logger.info("[AGENT 3: CLASSIFIER] - Classification complete", classified_count=len(classified_candidates))
    return state