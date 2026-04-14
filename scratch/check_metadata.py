from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import os

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
CHROMA_PATH = r"c:/Users/clair/Desktop/Final Project/architecture/chroma_db"
embeddings = OpenAIEmbeddings()
vector_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

try:
    results = vector_db.similarity_search("RPG", k=1)
    if results:
        print(f"METADATA_START")
        print(results[0].metadata)
        print(f"METADATA_END")
    else:
        print("No results found")
except Exception as e:
    print(f"Error: {e}")
