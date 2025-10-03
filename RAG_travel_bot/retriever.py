# main.py
import ollama
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
import streamlit as st
import os

# Load Ollama embeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Define FAISS index path
faiss_index_path = "faiss_index"


def initialize_vector_store():
    if os.path.exists(faiss_index_path):
        vectorstore = FAISS.load_local(faiss_index_path, embeddings, allow_dangerous_deserialization=True)
        st.write("FAISS index loaded successfully.")
        return vectorstore
    else:
        st.error("FAISS index not found. Please run save_index.py first.")
        return None


def get_rag_response(query, vector_store, conversation_history=""):
    if vector_store is None:
        return "Sorry, the travel knowledge base isn’t ready yet."

    # Retrieve more context chunks for broader coverage
    docs = vector_store.similarity_search(query, k=4)  # Increased from 2 to 4
    context = "\n".join([doc.page_content for doc in docs])

    # Include conversation history in the prompt to maintain context
    prompt = f"""You are a helpful travel advisor. Use the following context and conversation history to answer the question. If the context lacks sufficient detail, say so and provide a general response.
    Conversation History: {conversation_history}
    Context: {context}
    Question: {query}
    Answer in a friendly, informative tone."""

    response = ollama.chat(model="llama3", messages=[{"role": "user", "content": prompt}])
    return response['message']['content']


def main():
    st.title("Travel Advisor Chatbot")
    st.write("Ask me anything about travel destinations!")

    if 'vector_store' not in st.session_state:
        with st.spinner("Loading travel knowledge base..."):
            st.session_state.vector_store = initialize_vector_store()

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Where would you like to travel?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Build conversation history from previous messages
                conversation_history = "\n".join(
                    [f"{m['role']}: {m['content']}" for m in st.session_state.messages[:-1]]
                )
                response = get_rag_response(prompt, st.session_state.vector_store, conversation_history)
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()