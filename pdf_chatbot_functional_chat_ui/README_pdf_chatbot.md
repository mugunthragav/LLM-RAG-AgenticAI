# 📄 AI PDF Chatbot with GPT-4 + RAG

This is an interactive PDF chatbot powered by **GPT-4 Turbo** and **Retrieval-Augmented Generation (RAG)**. Users can upload any PDF document (like a research paper or textbook) and ask questions about its content through a chat interface.

---

## ✨ Features

✅ Upload any PDF (supports scanned or digital text PDFs)  
✅ Automatically extract and chunk text using **PyMuPDF**  
✅ Embed chunks using **OpenAI Embeddings**  
✅ Store and retrieve chunks using **FAISS vector store**  
✅ Answer questions based on document content using **GPT-4 Turbo**  
✅ Chat interface with real-time Q&A and memory  
✅ Context-aware conversation using **LangChain’s memory**  

---

## 📦 Installation

### 1. Clone or extract the project

If downloaded as a ZIP:
```bash
unzip pdf_chatbot_functional_chat_ui.zip
cd pdf_chatbot_functional_chat_ui
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Set Up API Keys

Create a `.env` file (already included in project) and add your OpenAI key:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🚀 Run the App

```bash
streamlit run streamlit_app.py
```

Then open your browser and go to:  
👉 `http://localhost:8501`

---

## 💬 How It Works

1. **Upload a PDF**.
2. The system will:
   - Extract text
   - Preprocess and chunk it
   - Embed each chunk
   - Store them in FAISS
3. Ask your questions like:
   - “What is this paper about?”
   - “Who are the authors?”
   - “What methods are used?”
4. GPT-4 will answer using **context from the document**.

---

## 🛠 Built With

- [Streamlit](https://streamlit.io/)
- [LangChain](https://www.langchain.com/)
- [OpenAI API](https://platform.openai.com/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF)

---

## 📌 Limitations

- Requires an internet connection (calls OpenAI API)
- Works best with **text-based PDFs** (OCR not yet supported)
- Doesn’t support multi-PDF uploads (yet)

---

## 📚 Future Features (Planned)

- 📘 Flashcard and quiz generation from PDFs  
- 🧠 Dashboard with learning progress and summaries  
- 🔔 Deadline reminder and assignment tracking  
- 🗣️ Voice input and response  
- 🖼️ Visual chat UI (Messenger-style)

---

## 👨‍💻 Author

Made with ❤️ using GPT-4 + LangChain + Streamlit