from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

def get_response(query, vectorstore, memory):
    print("📌 [Query Received]:", query)

    # Convert FAISS vector store to retriever
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    # Retrieve relevant documents
    docs = retriever.get_relevant_documents(query)

    print("📌 [Retrieved Docs Count]:", len(docs))
    for i, doc in enumerate(docs[:2]):
        print(f"--- Document {i+1} Content (first 300 characters) ---")
        print(doc.page_content[:300])
        print("-" * 50)

    # Return fallback message if no context found
    if not docs:
        return "⚠️ No relevant content found in the document to answer your question."

    # Initialize the LLM
    llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo")

    # Create a QA chain with LLM + retriever + memory
    qa_chain = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, memory=memory)

    # Get response from the chain
    result = qa_chain.run({"question": query})
    print("📌 [Final Answer from GPT-4]:", result)
    return result
