from sqlalchemy import Column, Integer, String, Float, Boolean
from app.database import Base

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, index=True)
    file_name = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    skills = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    education = Column(String, nullable=True)
    certifications = Column(String, nullable=True)
    passedout_year = Column(String, nullable=True)
    cgpa = Column(String, nullable=True)
    percentage_10th = Column(String, nullable=True)
    percentage_12th = Column(String, nullable=True)
    sex = Column(String, nullable=True)
    location = Column(String, nullable=True)
    internships = Column(String, nullable=True)
    classification = Column(String, nullable=True)
    matched_role = Column(String, nullable=True)
    match_score = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)  # Added missing field
    email_sent = Column(Boolean, nullable=True)
    agent_step = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)  # Added for better error reporting