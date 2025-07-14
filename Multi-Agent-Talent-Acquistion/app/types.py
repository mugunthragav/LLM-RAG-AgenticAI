from typing import TypedDict, List, Any, Optional
from sqlalchemy.orm import Session

class AppState(TypedDict):
    task_id: str
    resumes: List[dict]
    job_roles: List[str]
    job_skills: List[List[str]]
    job_descriptions_raw: List[dict]
    llm: Any
    db: Session  # Added db to state
    parsed_resumes: Optional[List[dict]]
    classified_candidates: Optional[List[dict]]
    matched_candidates: Optional[List[dict]]
    scored_resumes: Optional[List[dict]]
    scheduled_resumes: Optional[List[dict]]
    job_descriptions: Optional[List[dict]]