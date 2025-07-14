import structlog
import asyncio
from langsmith import traceable
from app.models.candidate import Candidate
from sqlalchemy.orm import Session
from app.types import AppState
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
HR_EMAIL = os.getenv("HR_EMAIL", "preethipa.chinnadurai@rasaailabs.com")

logger = structlog.get_logger()

async def send_email_smtp(candidate: dict) -> str:
    """Send an email to HR with candidate details for further action."""
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, HR_EMAIL]):
        logger.error("SMTP configuration incomplete. Please set SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and HR_EMAIL in the .env file.")
        return "Error: SMTP configuration incomplete"

    try:
        candidate_name = candidate.get("name", "Unknown")
        candidate_email = candidate.get("email", "Not provided")
        candidate_phone = candidate.get("phone", "Not provided")
        location = candidate.get("location", "Not provided")
        degree = candidate.get("education", "Not provided")
        role = candidate.get("matched_role", "None")
        final_score = candidate.get("final_score", 0.0)
        experience = candidate.get("experience", "Not provided") or "None"
        sex = candidate.get("sex", "Not provided")
        internships = candidate.get("internships", "Not provided") or "None"
        cgpa = candidate.get("cgpa", "Not provided")
        percentage_10th = candidate.get("percentage_10th", "Not provided")
        percentage_12th = candidate.get("percentage_12th", "Not provided")

        # Format the final score to one decimal place
        formatted_score = round(float(final_score), 1)

        msg = MIMEText(
            f"Dear HR Team,\n\n"
            f"A candidate has been matched for the role of {role} with a score of {formatted_score}%:\n"
            f"- Candidate Name: {candidate_name}\n"
            f"- Candidate Email: {candidate_email}\n"
            f"- Candidate Phone: {candidate_phone}\n"
            f"- Location: {location}\n"
            f"- Degree: {degree}\n"
            f"- Experience: {experience}\n"
            f"- Sex: {sex}\n"
            f"- Internships: {internships}\n"
            f"- CGPA: {cgpa}\n"
            f"- 10th Percentage: {percentage_10th}\n"
            f"- 12th Percentage: {percentage_12th}\n\n"
            f"Please take the next steps, such as scheduling a call with the candidate.\n\n"
            f"Best Regards,\nRasa.ai Labs Talent Acquisition System"
        )
        msg["Subject"] = f"New Candidate Match: {candidate_name} for {role}"
        msg["From"] = SMTP_USER
        msg["To"] = HR_EMAIL

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, HR_EMAIL, msg.as_string())
        logger.info(f"Email sent successfully for candidate: {candidate_name}")
        return "Sent to HR"
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"

async def schedule_candidate(candidate: dict, db: Session, threshold: float) -> dict:
    """Helper function to schedule a single candidate."""
    file_name = candidate.get("file_name")
    candidate_id = candidate.get("candidate_id")
    logger.info(f"[AGENT 6: SCHEDULER] - Scheduling candidate: {file_name}")

    try:
        final_score = float(candidate.get("final_score", 0) or 0)
        logger.debug(f"Candidate {file_name} final score: {final_score}")

        if final_score < threshold:
            candidate["rejection_reason"] = f"Score below threshold ({threshold})"
            candidate["email_sent"] = False
            candidate["email_status"] = f"Not sent: Score below threshold ({threshold}), final_score={final_score}"
        elif not candidate.get("email"):
            logger.warning(f"[AGENT 6: SCHEDULER] - No email found for candidate: {file_name}")
            candidate["rejection_reason"] = "No email provided"
            candidate["email_sent"] = False
            candidate["email_status"] = "Not sent: No email provided"
        else:
            email_status = await send_email_smtp(candidate)
            candidate["email_sent"] = email_status == "Sent to HR"
            candidate["email_status"] = email_status

        # Update the database
        db_candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if db_candidate:
            db_candidate.email_sent = candidate["email_sent"]
            db_candidate.rejection_reason = candidate.get("rejection_reason")
            db_candidate.agent_step = "scheduler"
            db.flush()

        logger.info(f"[AGENT 6: SCHEDULER] - Scheduled interview for candidate: {file_name}, Email status: {candidate['email_status']}")
        return candidate
    except Exception as e:
        logger.error(f"[AGENT 6: SCHEDULER] - Failed to schedule {file_name}: {str(e)}", exc_info=True)
        candidate["rejection_reason"] = str(e)
        candidate["email_sent"] = False
        candidate["email_status"] = f"Error: {str(e)}"
        return candidate

@traceable(run_type="chain")
async def scheduler(state: AppState, config: dict = None) -> AppState:
    logger.info("[AGENT 6: SCHEDULER] - Starting scheduling...")

    db = state.get("db")
    if not isinstance(db, Session):
        logger.error("[AGENT 6: SCHEDULER] - Database session not found in state")
        raise ValueError("Database session not found in state")

    scored_resumes = state.get("scored_resumes", [])
    if not scored_resumes:
        logger.warning("[AGENT 6: SCHEDULER] - No scored resumes to schedule")
        state["scheduled_resumes"] = []
        return state

    # Use a uniform threshold of 50 for all roles (lowered to allow more candidates)
    THRESHOLD = 50

    # Process candidates with deduplication
    processed_candidates = set()
    scheduled_resumes = []
    for candidate in scored_resumes:
        candidate_id = candidate.get("candidate_id")
        if candidate_id in processed_candidates:
            continue
        scheduled_candidate = await schedule_candidate(candidate, db, THRESHOLD)
        scheduled_resumes.append(scheduled_candidate)
        processed_candidates.add(candidate_id)

    db.commit()

    state["scheduled_resumes"] = scheduled_resumes
    scheduled_count = sum(1 for candidate in scheduled_resumes if candidate.get("email_sent", False))
    logger.info("[AGENT 6: SCHEDULER] - Scheduling complete", scheduled_count=scheduled_count)
    return state