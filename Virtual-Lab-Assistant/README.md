# Virtual Lab Assistant

The **Virtual Lab Assistant** is a conversational AI system that assists users with fuel cell testing and related queries. It combines Rasa for dialogue management, FastAPI for backend APIs, MySQL for dynamic responses, and GPT-4 for advanced knowledge. It also includes Retrieval-Augmented Generation (RAG) using FAISS for document-based responses.

---

##  Features

*  **Static Responses**: Fuel cell FAQs using `domain.yml`
*  **Dynamic Responses**: Pulled from MySQL tables via FastAPI
*  **RAG Responses**: PDF chunked, indexed, and queried with FAISS + GPT-4
*  **LLM Fallback**: GPT-4 used when DB & RAG fail
*  **Authentication**: Token-based user authentication with FastAPI

---

##  Prerequisites

* **Python 3.10.0**
* **MySQL Server**

  * With a database named `Virtual_Lab_Assistant`
  * Ensure you run `init.sql` to populate tables
* **FAISS Index**

  * Generated from a fuel cell PDF using `pdf_loader.py`
* **OpenAI API Key**

  * Required for GPT-4 responses (RAG & fallback)
* **Postman**

  * For testing authentication, chat, and RAG endpoints

---

##  Project Structure

* **`actions.py`**: Custom Rasa actions to handle static, dynamic, RAG, and GPT-based queries.
* **`nlu.yml`**: Intent examples for Rasa's NLU training.
* **`rules.yml`**: Rule-based mappings from intents to actions.
* **`stories.yml`**: Conversation flows for training dialogue policies.
* **`config.yml`**: Pipeline configuration for Rasa NLU and policies.
* **`llm_config.py`**: FastAPI app to handle MySQL-backed dynamic queries and LLM fallback.
* **`rag/pdf_loader.py`**: Script to load and chunk the fuel cell PDF and generate FAISS index.
* **`rag/rag_config.py`**: FastAPI app to serve RAG-based responses using Sentence Transformers + GPT-4.
* **`init.sql`**: MySQL schema and seed data.
* **`requirements.txt`**: All Python dependencies.
* **`Dockerfile.*`**: Dockerfiles for Rasa, Auth, LLM, and RAG services.
* **`docker-compose.yml`**: Multi-container orchestration for the full app.

---

##  Environment Variables

Create a `.env` file in the project root directory.

### ✅ For Local Setup:

```env
OPENAI_API_KEY=your-openai-key
SECRET_KEY=your-random-generated-secret-key
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=db password
DB_NAME=db name
RASA_URL=http://localhost:5005/webhooks/rest/webhook
```

### ✅ For Docker Setup:

```env
OPENAI_API_KEY=your-openai-key
SECRET_KEY=your-random-generated-secret-key
DB_HOST=mysql
DB_PORT=3306
DB_USER=root
DB_PASS=db password
DB_NAME=db name
RASA_URL=http://rasa:5005/webhooks/rest/webhook
```

> 🔐 To generate a secure secret key:

```bash
import secrets
print(secrets.token_hex(32))
```

---

##  Local Development Setup (Without Docker)

### 1. Clone Repository

```bash
git clone https://github.com/mugunthragav/LLM-RAG-AgenticAI.git
cd Virtual-Lab-Assistant
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create MySQL Database & Tables

```sql
CREATE DATABASE Virtual_Lab_Assistant;
-- Run the `init.sql` script to populate tables
```

### 4. Generate FAISS Index

```bash
cd rag
python pdf_loader.py
```

### 5. Train and Run Rasa

```bash
rasa train
rasa run actions --port 5055
rasa run --enable-api
```

### 6. Start FastAPI Services

```bash
uvicorn auth:app --port 8000
uvicorn rag.llm_config:app --port 8001
uvicorn rag.rag_config:app --port 8002
```

---

##  Docker Setup (Recommended)

### 1. Build Base Image

```bash
docker build -f Dockerfile.base -t virtual-lab-base:latest .
```

### 2. Run Docker Compose

```bash
docker-compose up --build
```

### 3. Access Services

| Component    | URL                                                                      |
| ------------ | ------------------------------------------------------------------------ |
| Auth API     | [http://localhost:8000](http://localhost:8000)                           |
| Rasa Webhook | [http://localhost:8000/rasa/webhook](http://localhost:8000/rasa/webhook) |
| Auth Docs    | [http://localhost:8000/docs](http://localhost:8000/docs)                 |
| LLM Docs     | [http://localhost:8001/docs](http://localhost:8001/docs)                 |
| RAG Docs     | [http://localhost:8002/docs](http://localhost:8002/docs)                 |

---

##  Authentication (FastAPI)

### 1. Login API

```http
POST http://localhost:8000/token
{
  "username": "USERNAME",
  "password": "PASSWORD"
}
```

**✅ Sample Response:**

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

### 2. Rasa Chat API

```http
POST http://localhost:8000/rasa/webhook
Authorization: Bearer <token>
{
  "message": "what is a fuel leak procedure?"
}
```

**✅ Sample Response:**

```json
[
  {
    "recipient_id": "your-mail-id"",
    "text": "Shut off the hydrogen supply, evacuate the area, and notify emergency services."
  }
]
```

---

##  Postman Test Examples

### 1. Login

POST `http://localhost:8000/token`

**Response:**

```json
{
  "access_token": "<JWT_token>",
  "token_type": "bearer"
}
```

### 2. Chat with Bot

POST `http://localhost:8000/rasa/webhook`

**Request Body:**

```json
{
  "sender": "user",
  "message": "hello"
}
```

**Response:**

```json
[
  {
    "recipient_id": "user",
    "text": "Hello! How can I assist you with fuel cell testing today?"
  }
]
```

### 3. RAG Query

GET `http://localhost:8001/rag_query/?query=What+is+MCFC`

**Response:**

```json
{
  "answer": "MCFC stands for Molten Carbonate Fuel Cell..."
}
```

### 4. DB Query

POST `http://localhost:8000/fetch_dynamic_response/`

**Request Body:**

```json
{
  "intent": "get_emergency_procedure",
  "query": "what should I do in case of a fuel leak?"
}
```

**Response:**

```json
{
  "response": "Shut off the hydrogen supply, evacuate the area, and notify emergency services."
}
```

---

## 🛠 Troubleshooting

| Problem                   | Solution                                                 |
| ------------------------- | -------------------------------------------------------- |
| MySQL error               | Ensure `init.sql` is executed or mounted                 |
| Action server not working | Check `endpoints.yml` uses `http://actions:5055/webhook` |
| Token errors              | Ensure `Authorization: Bearer <token>` used              |
| RAG not responding        | Ensure FAISS index exists from `pdf_loader.py`           |

---

##  Resources

* Rasa: [https://rasa.com/docs](https://rasa.com/docs)
* FastAPI: [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com)
* FAISS: [https://github.com/facebookresearch/faiss](https://github.com/facebookresearch/faiss)

---


