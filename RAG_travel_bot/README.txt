

# Travel Advisor Chatbot README

## Overview
This Travel Advisor Chatbot provides travel-related answers using the Bitext Travel LLM Chatbot Training Dataset from Hugging Face (~20-30 MB). It uses Retrieval-Augmented Generation (RAG) with FAISS for context retrieval, Ollama for local embeddings and responses, and Streamlit for a web interface.

- **Data Source**: Bitext Travel LLM Chatbot Training Dataset (Hugging Face).
- **Tools**: Python, Ollama, FAISS, Streamlit.
- **Requirements**: Windows laptop with 8GB+ RAM, internet for initial setup.

---

## Setup Instructions

### Step 1: Initial Setup

1. **Install Python 3.11**:
   - Download from [python.org/downloads](https://www.python.org/downloads/).
   - Install with "Add Python to PATH" checked.
   - Verify: `python --version` in Command Prompt.

2. **Install Ollama**:
   - Download from [ollama.com/download](https://ollama.com/download).
   - Run the `.exe` installer (runs as a background service).
   - Pull models:
     ```cmd
     ollama pull nomic-embed-text
     ollama pull llama3
     ```
   - Verify: `ollama list`.

3. **Create Project Directory**:
   ```cmd
   mkdir <your-path>\travel_bot
   cd <your-path>\travel_bot
   ```

---

### Step 2: Set Up Virtual Environment

1. **Create Virtual Environment**:
   ```cmd
   python -m venv .venv
   ```

2. **Activate Virtual Environment**:
   ```cmd
   .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```cmd
   pip install streamlit langchain-community langchain-ollama ollama faiss-cpu datasets
   ```

---

### Step 3: Preprocess Data and Build FAISS Index

1. **Create Data Directory** (optional):
   ```cmd
   mkdir data
   ```

2. **Run Preprocessing Script**:
   - Ensure `save_index.py` is in the project folder.
   - Execute:
     ```cmd
     python save_index.py
     ```
   - Takes 5-15 minutes; creates `faiss_index` directory.

---

### Step 4: Run the Chatbot

1. **Start the Chatbot**:
   - Ensure `retriever.py` is in the project folder and Ollama is running.
   - Execute:
     ```cmd
     streamlit run retriever.py
     ```
   - Opens in browser at `http://localhost:8501`.

2. **Test**:
   - Ask questions like "What’s the best time to visit Italy?" or "How do I book a hotel in New York?"

---

## Troubleshooting

- **Ollama Not Running**: Check system tray or run `ollama serve`.
- **FAISS Index Missing**: Re-run `python save_index.py`.
- **Slow Performance**: Increase `chunk_size` in `save_index.py` (e.g., to 2000).

---

## Project Structure
```
C:\Users\<YourUsername>\PycharmProjects\travel_bot\
│
├── .venv\         # Virtual environment
├── data\          # Optional
├── faiss_index\   # FAISS index files
├── save_index.py  # Preprocessing script
└── retriever.py        # Chatbot script
```

---

## Hardware Requirements
- **OS**: Windows 10/11
- **RAM**: 8GB+ (4GB may work but slower)
- **CPU**: Multi-core recommended
- **Disk**: ~1GB free

---

## Maintenance
- **Update Dataset**: Re-run `python save_index.py`.
- **Add Data**: Edit `save_index.py` to include custom Q&A.
- **Upgrade Models**: Pull newer Ollama models (e.g., `ollama pull llama3:latest`).

--- 

This README keeps it simple and actionable for a fresh setup. Save it as `README.md` in your project folder. Let me know if you need adjustments!