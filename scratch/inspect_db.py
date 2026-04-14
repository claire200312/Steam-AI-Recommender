
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import os

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
CHROMA_PATH = "c:/Users/clair/Desktop/Final Project/architecture/chroma_db"
embeddings = OpenAIEmbeddings()
vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

results = vector_db.similarity_search("RPG", k=5)
for i, res in enumerate(results):
    print(f"Result {i+1}:")
    print(f"Metadata: {res.metadata}")
    print("-" * 20)
