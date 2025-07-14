import structlog
import asyncio
import re
from langsmith import traceable
from app.models.candidate import Candidate
from sqlalchemy.orm import Session
from app.types import AppState

logger = structlog.get_logger()

async def score_candidate(candidate: dict, db: Session, state: AppState) -> dict:
    """Helper function to score a single candidate."""
    file_name = candidate.get("file_name")
    candidate_id = candidate.get("candidate_id")
    logger.info(f"[AGENT 5: SCORER] - Scoring candidate: {file_name}")

    try:
        # Extract relevant data
        candidate_skills = [skill.strip().lower() for skill in candidate.get("skills", "").split(",")]
        candidate_exp = candidate.get("experience", "")
        matched_role = candidate.get("matched_role", "None")
        education = candidate.get("education", "")
        cgpa = candidate.get("cgpa", "")
        percentage_10th = candidate.get("percentage_10th", "")
        percentage_12th = candidate.get("percentage_12th", "")

        # Parse experience in years (including internships)
        exp_years = 0.0
        internships = candidate.get("internships", "")
        combined_exp = f"{candidate_exp} {internships}".strip()

        # Extract years and months from both experience and internships
        exp_matches = re.findall(r"(\d+\.?\d*)\s*(?:years?|yrs?)", combined_exp, re.IGNORECASE)
        month_matches = re.findall(r"(\d+)\s*months?", combined_exp, re.IGNORECASE)

        for years in exp_matches:
            exp_years += float(years)
        for months in month_matches:
            exp_years += int(months) / 12.0

        # If no matches but experience/internship exists, assume a minimal duration
        if exp_years == 0 and (candidate_exp or internships):
            exp_years = 0.5  # Assume 6 months if experience is mentioned but not quantified
        logger.debug(f"Parsed experience: {exp_years} years")

        # Get job description details for the matched role
        job_descriptions = state.get("job_descriptions", [])
        jd = next((jd for jd in job_descriptions if jd["role"] == matched_role), None)
        if not jd:
            logger.warning(f"No job description found for role: {matched_role}")
            candidate["score"] = 0.0
            candidate["final_score"] = 0.0
            return candidate

        min_exp = jd["min_exp"]
        max_exp = jd["max_exp"]
        required_skills = [skill.strip().lower() for skill in jd["skills"]]

        # Experience score (20 points)
        if exp_years == 0:
            exp_score = 10  # Base score for no experience
        elif min_exp <= exp_years <= max_exp:
            exp_score = 20  # Full points if within range
        else:
            exp_score = 15  # Partial points if outside range
        logger.debug(f"Experience score: {exp_score}/20")

        # Skills match score (60 points) - Increased weight
        matching_skills = 0
        for req_skill in required_skills:
            for cand_skill in candidate_skills:
                # Flexible matching: check if required skill is a substring of candidate skill or vice versa
                if req_skill in cand_skill or cand_skill in req_skill:
                    matching_skills += 1
                    break
                # Handle specific cases like "R or Python" and "Microsoft Excel"
                if "or" in req_skill and any(s in cand_skill for s in req_skill.split(" or ")):
                    matching_skills += 1
                    break
                if req_skill == "microsoft excel" and "excel" in cand_skill:
                    matching_skills += 1
                    break
        skills_match_ratio = matching_skills / len(required_skills) if required_skills else 0.0
        skills_score = skills_match_ratio * 60
        logger.debug(f"Skills match ratio: {skills_match_ratio}, Score: {skills_score}/60")

        # Education score (20 points) - Relaxed criteria
        education_score = 0
        try:
            cgpa_value = float(re.search(r"\d+\.?\d*", cgpa).group()) if cgpa and re.search(r"\d+\.?\d*", cgpa) else 0.0
            percentage_10th_value = float(percentage_10th) if percentage_10th else 0.0
            percentage_12th_value = float(percentage_12th) if percentage_12th else 0.0
        except (ValueError, TypeError):
            cgpa_value = 0.0
            percentage_10th_value = 0.0
            percentage_12th_value = 0.0

        # Award points for higher education first
        if cgpa_value > 0:
            education_score += 10 if cgpa_value >= 60 else 5  # Relaxed to 60% for "average" marks
        elif education:  # If no CGPA but education exists (e.g., degree mentioned)
            education_score += 8  # Base score for having a degree

        # Add points for 10th and 12th if available
        if percentage_10th_value >= 60:
            education_score += 5
        if percentage_12th_value >= 60:
            education_score += 5
        logger.debug(f"Education - CGPA: {cgpa_value}%, 10th: {percentage_10th_value}%, 12th: {percentage_12th_value}%, Score: {education_score}/20")

        # Total score
        total_score = exp_score + skills_score + education_score
        candidate["score"] = skills_score  # Legacy field
        candidate["final_score"] = total_score

        # Update the database
        db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if db_candidate:
            db_candidate.score = candidate["score"]
            db_candidate.final_score = candidate["final_score"]
            db_candidate.agent_step = "scorer"
            db.flush()

        logger.info(f"[AGENT 5: SCORER] - Scored {file_name}: final_score={total_score}")
        return candidate
    except Exception as e:
        logger.error(f"[AGENT 5: SCORER] - Failed to score {file_name}: {str(e)}", exc_info=True)
        candidate["score"] = 0.0
        candidate["final_score"] = 0.0
        return candidate

@traceable(run_type="chain")
async def scorer(state: AppState, config: dict = None) -> AppState:
    logger.info("[AGENT 5: SCORER] - Starting scoring...")
    logger.info(f"[AGENT 5: SCORER] - State received (type: {type(state)}): {state}")

    db = state.get("db")
    if not isinstance(db, Session):
        logger.error("[AGENT 5: SCORER] - Database session not found in state")
        raise ValueError("Database session not found in state")

    matched_candidates = state.get("matched_candidates", [])
    if not matched_candidates:
        logger.warning("[AGENT 5: SCORER] - No matched candidates to score")
        state["scored_resumes"] = []
        return state

    # Process candidates without tracing to avoid langsmith issues
    scored_resumes = []
    for candidate in matched_candidates:
        scored_candidate = await score_candidate(candidate, db, state)  # Pass state to score_candidate
        scored_resumes.append(scored_candidate)

    db.commit()

    state["scored_resumes"] = scored_resumes
    logger.info("[AGENT 5: SCORER] - Scoring complete", scored_count=len(scored_resumes))
    return state