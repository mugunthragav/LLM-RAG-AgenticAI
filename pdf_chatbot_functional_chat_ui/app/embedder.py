from langchain.embeddings import OpenAIEmbeddings
import os

def get_embeddings():
    return OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

from langchain.embeddings.openai import OpenAIEmbeddings

def get_embeddings():
    return OpenAIEmbeddings()
