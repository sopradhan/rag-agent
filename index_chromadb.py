"""
Index all SQLite documents into ChromaDB
"""
from src.storage import RAGDatabase, ChromaVectorStore
import chromadb

print("="*70)
print("INDEXING: Migrating documents to ChromaDB")
print("="*70)

# Get documents from SQLite
db = RAGDatabase()
docs = db.get_all_documents()
print(f"\n[OK] Found {len(docs)} documents in SQLite")

# Initialize vector store
vector_store = ChromaVectorStore()

# Index all documents
print(f"\n[*] Indexing documents into ChromaDB...")
count = 0
for doc_id, content, source, access_level in docs:
    try:
        vector_store.add_document(
            doc_id=doc_id,
            text=content,
            source=source,
            metadata={"access_level": access_level}
        )
        count += 1
        if count % 10 == 0:
            print(f"  [{count}/{len(docs)}] Indexed...")
    except Exception as e:
        print(f"  Error indexing {doc_id}: {str(e)[:50]}")
        pass

print(f"\n[OK] Indexed {count} documents to ChromaDB")

# Verify
client = chromadb.PersistentClient(path='data/chroma_db')
collection = client.get_collection(name='rag_embeddings')
print(f"[OK] ChromaDB now contains: {collection.count()} documents")

print("\n" + "="*70)
print("INDEXING COMPLETE!")
print("="*70)
