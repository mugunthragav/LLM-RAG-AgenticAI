import structlog
import uuid
import os
import asyncio
from langsmith import traceable
from app.models.candidate import Candidate
from sqlalchemy.orm import Session
from app.types import AppState

logger = structlog.get_logger()

async def save_resume(resume: dict, upload_dir: str, task_id: str, db: Session) -> dict:
    """Helper function to save a single resume and add it to the database."""
    file_name = resume.get("file_name")
    content = resume.get("content")
    logger.info(f"[AGENT 1: UPLOADER] - Processing: {file_name}")

    try:
        # Normalize file path
        file_name = os.path.normpath(file_name)
        file_path = os.path.join(upload_dir, os.path.basename(file_name))
        logger.debug(f"[AGENT 1: UPLOADER] - Saving to: {file_path}")

        # Save content to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Add to database
        candidate = Candidate(
            task_id=task_id,
            file_name=file_name,
            agent_step="uploader"
        )
        db.add(candidate)
        db.flush()  # Flush to get the candidate ID
        return {"file_name": file_name, "content": content, "candidate_id": candidate.id}
    except Exception as e:
        logger.error(f"[AGENT 1: UPLOADER] - Failed to process {file_name}: {str(e)}")
        return None

@traceable(run_type="chain")
async def uploader(state: AppState, config: dict = None) -> AppState:
    logger.info("[AGENT 1: UPLOADER] - Starting resume upload...")
    # Remove detailed state logging
    # logger.info(f"[AGENT 1: UPLOADER] - State received (type: {type(state)}): {state}")

    # Retrieve db from state
    db = state.get("db")
    if not isinstance(db, Session):
        logger.error("[AGENT 1: UPLOADER] - Database session not found in state")
        raise ValueError("Database session not found in state")

    task_id = state.get("task_id", str(uuid.uuid4()))
    state["task_id"] = task_id

    resumes = state.get("resumes", [])
    if not isinstance(resumes, list):
        logger.error("[AGENT 1: UPLOADER] - Resumes must be a list")
        raise ValueError("Resumes must be a list")

    upload_dir = os.path.join("app", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    logger.debug(f"[AGENT 1: UPLOADER] - Using upload directory: {upload_dir}")

    tasks = [save_resume(resume, upload_dir, task_id, db) for resume in resumes]
    uploaded_resumes = await asyncio.gather(*tasks)

    uploaded_resumes = [resume for resume in uploaded_resumes if resume is not None]
    db.commit()

    state["resumes"] = uploaded_resumes
    logger.info("[AGENT 1: UPLOADER] - Upload complete", uploaded_count=len(uploaded_resumes))
    return state