import structlog
import asyncio
import re
from langsmith import traceable
from app.models.candidate import Candidate
from sqlalchemy.orm import Session
from app.types import AppState

logger = structlog.get_logger()

async def match_candidate(candidate: dict, job_descriptions: list, db: Session) -> dict:
    """Helper function to match a single candidate to a job role using deterministic scoring."""
    file_name = candidate.get("file_name")
    candidate_id = candidate.get("candidate_id")
    logger.info(f"[AGENT 4: MATCHER] - Matching candidate: {file_name}")

    try:
        candidate_skills = candidate.get("skills", "")
        candidate_exp = candidate.get("experience", "")
        classification = candidate.get("classification", "")

        if not candidate_skills or candidate_skills == "Not specified":
            candidate["matched_role"] = "None"
            candidate["match_score"] = 0.0
            return candidate

        # Extract years of experience from candidate_exp
        exp_years = 0.0
        exp_match = re.search(r"(\d+\.?\d*)\s*(?:years?|yrs?)", candidate_exp, re.IGNORECASE)
        if exp_match:
            exp_years = float(exp_match.group(1))
        else:
            month_match = re.search(r"(\d+)\s*months?", candidate_exp, re.IGNORECASE)
            if month_match:
                months = int(month_match.group(1))
                exp_years = months / 12.0
            else:
                exp_years = 0.5 if candidate_exp != "Not specified" else 0.0

        # Normalize candidate skills for comparison
        candidate_skills = [skill.strip().lower() for skill in candidate_skills.split(",")]

        best_match = None
        best_score = 0.0

        for jd in job_descriptions:
            role = jd["role"]
            required_skills = [skill.strip().lower() for skill in jd["skills"]]
            min_exp = jd["min_exp"]
            max_exp = jd["max_exp"]

            # Calculate experience match score (0-100)
            exp_match_score = 100.0 if min_exp <= exp_years <= max_exp else 0.0

            # Calculate skills match score (0-100)
            matching_skills = set(candidate_skills).intersection(required_skills)
            skills_match_ratio = len(matching_skills) / len(required_skills) if required_skills else 0.0
            skills_score = skills_match_ratio * 100.0

            # Total match score (70% skills, 30% experience)
            match_score = (0.7 * skills_score) + (0.3 * exp_match_score)

            # Prioritize the role that matches the candidate's classification
            if classification.lower() == role.lower() and match_score > best_score:
                best_score = match_score
                best_match = role

        candidate["matched_role"] = best_match if best_match else "None"
        candidate["match_score"] = best_score

        # Update the database
        db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if db_candidate:
            db_candidate.matched_role = candidate["matched_role"]
            db_candidate.match_score = candidate["match_score"]
            db_candidate.agent_step = "matcher"
            db.flush()

        logger.info(f"[AGENT 4: MATCHER] - Matched {file_name} to {candidate['matched_role']} with score {best_score}%")
        return candidate
    except Exception as e:
        logger.error(f"[AGENT 4: MATCHER] - Failed to match {file_name}: {str(e)}")
        candidate["matched_role"] = "None"
        candidate["match_score"] = 0.0
        return candidate

@traceable(run_type="chain")
async def matcher(state: AppState, config: dict = None) -> AppState:
    logger.info("[AGENT 4: MATCHER] - Starting matching...")

    db = state.get("db")
    if not isinstance(db, Session):
        logger.error("[AGENT 4: MATCHER] - Database session not found in state")
        raise ValueError("Database session not found in state")

    job_roles = state.get("job_roles", [])
    job_skills = state.get("job_skills", [])
    job_descriptions = []
    for role, skills in zip(job_roles, job_skills):
        jd_text = next((jd["text"] for jd in state.get("job_descriptions_raw", []) if jd["role"] == role), "")
        min_exp = 0
        max_exp = 1
        exp_match = re.search(r"(\d+)-(\d+)\s*years?", jd_text, re.IGNORECASE)
        if exp_match:
            min_exp = int(exp_match.group(1))
            max_exp = int(exp_match.group(2))
        job_descriptions.append({
            "role": role,
            "skills": skills,
            "min_exp": min_exp,
            "max_exp": max_exp
        })
    state["job_descriptions"] = job_descriptions

    classified_candidates = state.get("classified_candidates", [])
    if not classified_candidates:
        logger.warning("[AGENT 4: MATCHER] - No classified candidates to match")
        state["matched_candidates"] = []
        return state

    tasks = [match_candidate(candidate, job_descriptions, db) for candidate in classified_candidates]
    matched_candidates = await asyncio.gather(*tasks)

    db.commit()

    state["matched_candidates"] = matched_candidates
    logger.info("[AGENT 4: MATCHER] - Matching complete", matched_count=len(matched_candidates))
    return state