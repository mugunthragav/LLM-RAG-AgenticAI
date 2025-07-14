
---

### Updated `README.md`

```markdown
# Multi-Agent Talent Acquisition System

## Overview

The Multi-Agent Talent Acquisition System is an automated workflow designed to streamline the recruitment process by processing resumes, classifying candidates, matching them to job roles, scoring their qualifications, and scheduling interviews. The system leverages multiple agents that work collaboratively to handle various stages of the recruitment pipeline. It is built using modern Python frameworks and tools to ensure scalability, traceability, and efficiency.

## Key Features

* **Resume Uploading:** Uploads multiple resumes in PDF format (via zip file or individually) for processing.
* **Resume Parsing:** Extracts structured data (e.g., name, email, skills, experience, internships, location, etc.) from resumes using an LLM.
* **Classification:** Classifies candidates into relevant job roles based on their skills and experience.
* **Matching:** Matches candidates to job descriptions with a computed match score.
* **Scoring:** Scores candidates based on skills (60%), experience (20%), and education (20%), calculating a final score out of 100.
* **Scheduling:** Schedules interviews for candidates whose final score exceeds a threshold (50) and sends email notifications to HR.


## Technologies Used

### LangChain

* **Purpose:** Integrates and manages interactions with the Large Language Model (LLM) for resume parsing and classification.
* **Usage:**
  * **Resume Parsing (Agent 2):** Extracts structured data using GPT-4.
  * **Classification (Agent 3):** Classifies candidates into roles using LLM analysis.
* **Why LangChain?** Simplifies LLM integration, enhances prompt engineering, and ensures reliable parsing/classification.

### LangSmith

* **Purpose:** Tracing, debugging, and monitoring LLM-based operations.
* **Usage:**
  * **Traceability:** Logs inputs, outputs, and workflow steps using `@traceable`.
  * **Monitoring:** Provides insights for debugging and optimization.
* **Why LangSmith?** Advanced tracing capabilities aid debugging complex workflows.

### LangGraph

* **Purpose:** Orchestrates the multi-agent workflow as a directed graph.
* **Usage:**
  * **Workflow Orchestration:** Manages the sequence of agents (Uploader → Parser → Classifier → Matcher → Scorer → Scheduler).
  * **State Management:** Maintains shared `AppState` with resumes, scores, etc.
* **Why LangGraph?** Ensures robust and error-tolerant multi-agent orchestration.

### Other Technologies

* **FastAPI:** Web server and API endpoints.
* **SQLAlchemy:** Database interaction.
* **Uvicorn:** ASGI server for FastAPI.
* **Streamlit:** Interactive dashboard for uploading and processing resumes.
* **OpenAI GPT-4:** LLM for resume parsing and classification.
* **SQLite:** Database for storing candidate data.
* **Python Libraries:** `structlog`, `re`, `pymupdf`, `python-docx`, `requests`, etc.

## Project Structure

```
Multi-Agent-Talent-Acquisition/
│
├── app/
│   ├── agents/
│   │   ├── uploader.py
│   │   ├── parser.py
│   │   ├── classifier.py
│   │   ├── matcher.py
│   │   ├── scorer.py
│   │   └── scheduler.py
│   ├── models/
│   │   └── candidate.py
│   ├── types/
│   │   └── __init__.py
│   ├── uploads/
│   └── app.py
├── dashboard/
│   └── streamlit_app.py
├── data/
│   └── jds.csv
├── requirements.txt
└── README.md
```

## Prerequisites

* Python 3.10.0
* Virtual Environment
* LangChain API key
* OpenAI API Key
* Relational Database (SQLite/PostgreSQL)
* SMTP Server for email notifications

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://gitlab.com/rasaai/smart-llm-solutions.git
cd Multi-Agent-Talent-Acquisition
```

### 2. Set Up a Virtual Environment

```bash
python -m venv vlenvv
source vlenvv/bin/activate  # On Windows: vlenvv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### requirements.txt should include:

```
fastapi
uvicorn
langchain
langsmith
langgraph
sqlalchemy
openai
structlog
streamlit
pymupdf
python-docx
requests
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=<your-openai-api-key>
DATABASE_URL=sqlite:///app.db
SMTP_HOST=<your-smtp-host>
SMTP_PORT=<your-smtp-port>
SMTP_USER=<your-smtp-user>
SMTP_PASSWORD=<your-smtp-password>
```

### 5. Prepare Job Descriptions

Ensure `data/jds.csv` contains job descriptions with roles and required skills:

```
id,role,text
1,Data Scientist,"Data Scientist role for candidates with 0-1 years of experience. Requires skills in Python or R, statistics(Predictive Analysis, Hypothesis testing, PCA, Text Analytics, Univariate and Bivariate analysis), Database Management, Sql, Mysql, Machine learning(Predictive Analysis, Hypothesis testing, PCA, Text Analytics, Univariate and Bivariate analysis), Deep learning, Natural language Processing(TF-IDF, Vectorization, NLTK, Spacy, AI and Data Visualization)"
2,Backend Developer,"Backend Developer role for candidates with 0-1 years of experience. Requires skills in Node.js, Sql, Mysql, MongoDB, Java/J2EE, Springboot."
```

### 6. Set Up the Database

The SQLite database (`app.db`) will be created automatically on the first run. The system now supports duplicate resume submissions, storing each entry with a unique `task_id`.

## Running the System

### 1. Start the FastAPI Server

Run the FastAPI server on port 8000 to avoid conflicts with Streamlit:

```bash
uvicorn app.app:app --host 0.0.0.0 --port 8000
```

### 2. Start the Streamlit Dashboard

In a new terminal, navigate to the `dashboard` directory and run the Streamlit app:

```bash
cd dashboard
streamlit run streamlit_app.py
```

- The Streamlit dashboard will open in your browser (default: `http://localhost:8501`).

### 3. Upload and Process Resumes

- **Via Streamlit Dashboard (Recommended):**
  - Open the Streamlit app in your browser.
  - Upload a zip file containing resumes (PDF format).
  - Click "Process Resumes" to start the workflow.
  - Once processing is complete, HR will receive email notifications for candidates with scores above 50.

- **Via API (Alternative):**
  If you prefer to use the API directly, you can upload resumes using curl or Postman:

  ```bash
  curl -X POST "http://localhost:8000/upload-resumes/" -F "files=@path/to/Resume_01.pdf" -F "files=@path/to/Resume_02.pdf"
  ```

## Workflow Execution

The system processes resumes through the following agents:

* **Uploader (Agent 1):** Saves resumes to the database, supporting duplicate submissions.
* **Parser (Agent 2):** Extracts structured data (name, email, skills, etc.) using GPT-4.
* **Classifier (Agent 3):** Assigns job roles based on skills and experience.
* **Matcher (Agent 4):** Calculates a match score by comparing candidate skills to job requirements.
* **Scorer (Agent 5):** Scores candidates (skills: 60%, experience: 20%, education: 20%) with a final score out of 100.
* **Scheduler (Agent 6):** Schedules interviews for candidates with scores > 50 and sends email notifications to HR.

## Logs Example

After processing resumes, check the FastAPI server logs for details:

```
INFO:app.app:Role: Data Scientist, Extracted Skills: ['Python', 'R', 'statistics', ...], Min Exp: 0, Max Exp: 1
[AGENT 1: UPLOADER] - Upload complete uploaded_count=6
[AGENT 2: PARSER] - Parsing complete parsed_count=6
[AGENT 3: CLASSIFIER] - Classification complete classified_count=6
[AGENT 4: MATCHER] - Matched Resume_01.pdf to Data Analyst with score 45.0%
[AGENT 5: SCORER] - Scored Resume_01.pdf: final_score=52.5
[AGENT 6: SCHEDULER] - Scheduled interview for candidate: Resume_01.pdf, Email status: Sent to HR
[AGENT 6: SCHEDULER] - Scheduling complete scheduled_count=3
```

## Verify Results

* **Database:** Check `app.db` for candidate data, including duplicates with different `task_id`s.
* **Emails:** Confirm HR received emails for candidates with scores above 50.
* **Streamlit Dashboard:** View the processing results, including `task_id` and candidate details.

## Example Workflow Output

```
Uploader: 6 resumes uploaded (supports duplicates)
Parser: Extracts fields (name, email, skills, etc.)
Classifier: Roles assigned (e.g., Data Analyst, Backend Developer)
Matcher: Match scores calculated (e.g., 45%)
Scorer: Final scores computed (e.g., 52.5/100)
Scheduler: 3 candidates scheduled, emails sent to HR
```

## Troubleshooting

* **Port Conflicts:** Ensure FastAPI runs on port 8000 and Streamlit on port 8501.
* **LLM Errors:** Verify OpenAI API key and credits. Check LangSmith logs for debugging.
* **Database Issues:** Confirm `DATABASE_URL` is set correctly. The system now handles duplicate resume submissions.
* **Email Notifications:** Validate SMTP configuration in `.env`. Check logs for email sending errors.
* **Scoring Logic:** Review `scorer.py` if scores seem incorrect. Ensure `jds.csv` skills are extracted properly.

## Future Improvements

* Advanced scoring logic with weighted skills matching.
* HR feedback loop for iterative improvements.
* Scalable batch processing for large resume sets.
* Enhanced UI dashboard with candidate filtering and analytics.
* Support for additional resume formats (e.g., DOCX parsing improvements).
* Migration to a more robust database (e.g., PostgreSQL) for production.
```

---

