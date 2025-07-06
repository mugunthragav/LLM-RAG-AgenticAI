from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain

def get_response(query, vectorstore, memory):
    print("📌 [Query Received]:", query)

    # Convert FAISS vector store to retriever
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    # Retrieve relevant documents
    docs = retriever.get_relevant_documents(query)
    print("📌 [Retrieved Docs Count]:", len(docs))

    for i, doc in enumerate(docs[:2]):
        print(f"--- Document {i+1} Content (first 500 characters) ---")
        print(doc.page_content[:500])
        print("-" * 50)

    # Fallback if nothing is retrieved
    if not docs:
        return "⚠️ No relevant content found in the document to answer your question."

    # Load GPT-4 Turbo model
    llm = ChatOpenAI(temperature=0, model_name="gpt-4-turbo")

    # Set up QA chain with retriever and conversation memory
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory
    )

    # Run the query with history
    result = qa_chain.run({
        "question": query,
        "chat_history": memory.chat_memory.messages
    })

    print("📌 [Final Answer from GPT-4]:", result)
    return result
