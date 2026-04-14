import chromadb
client = chromadb.PersistentClient(path=r"c:\Users\clair\Desktop\Final Project\architecture\chroma_db")
collections = client.list_collections()
print("Collections:", [c.name for c in collections])
for c in collections:
    print(f"Collection {c.name} count:", c.count())
