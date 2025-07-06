import streamlit as st
import os
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile

# App modules
from app.pdf_extractor import extract_text_from_pdf
from app.text_preprocessor import preprocess_text
from app.chunker import chunk_text
from app.embedder import get_embeddings
from app.vector_store import create_vector_store
from app.response import get_response

from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# App config
st.set_page_config(page_title="🧠 AI Tutor Chatbot", layout="wide", page_icon="🤖")
st.title("🤖 EduGenie : AI Tutor Chatbot + PDF Q&A")

st.sidebar.title("🧾 Upload PDF (Optional)")
uploaded_file = st.sidebar.file_uploader("Upload course material (PDF)", type=["pdf"])

# Shared memory for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# If PDF uploaded: process it
if uploaded_file:
    with st.spinner("Processing PDF..."):
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            pdf_path = tmp_file.name

        raw_text = extract_text_from_pdf(pdf_path)
        cleaned_text = preprocess_text(raw_text)
        chunks = chunk_text(cleaned_text)

        embeddings = get_embeddings()
        vector_store = create_vector_store(chunks, embeddings)

        st.session_state.vector_store = vector_store
        st.success("✅ PDF uploaded and ready for Q&A!")

st.markdown("### 💬 Ask Your AI Tutor")
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_input("Ask a question (about the PDF or anything else):")
    submitted = st.form_submit_button("Send")

    if submitted and user_input:
        with st.spinner("Thinking..."):
            if st.session_state.vector_store:
                # Use RAG with vector store
                response = get_response(user_input, st.session_state.vector_store, st.session_state.memory)
            else:
                # Use plain LLM (ChatGPT-like response)
                llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
                response = llm.predict(user_input)

            st.session_state.chat_history.append((user_input, response))

# Show chat history
if st.session_state.chat_history:
    st.markdown("### 🧠 Chat History")
    for q, a in st.session_state.chat_history[::-1]:
        st.markdown(f"**👤 You:** {q}")
        st.markdown(f"**🤖 EduGenie:** {a}")
else:
    st.info("Ask your AI tutor anything")

