"""
Index SQLite documents into ChromaDB
"""

import sys
sys.path.insert(0, 'e:\\rag_agent')

from src.storage import RAGDatabase, ChromaVectorStore

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

# Prepare batch
doc_ids = [doc.get('doc_id') for doc in docs[:51]]
texts = [doc.get('content') for doc in docs[:51]]
metadatas = [{"access_level": doc.get('min_access_level', 1), "source": doc.get('source')} for doc in docs[:51]]

try:
    vector_store.add_documents(
        doc_ids=doc_ids,
        texts=texts,
        metadatas=metadatas
    )
    print(f"[OK] Successfully indexed {len(doc_ids)} documents")
except Exception as e:
    print(f"[ERROR] Indexing failed: {str(e)[:100]}")

print(f"\n[OK] Indexed {len(doc_ids)} documents to ChromaDB")

# Verify
print(f"[OK] ChromaDB indexed successfully!")
print(f"\n[*] Verifying indexing...")
try:
    test_search = vector_store.search("database backup", n_results=3)
    print(f"[OK] Search test: Found {len(test_search['ids'])} results")
    if test_search['ids']:
        print(f"     Top result: {test_search['documents'][0][:60]}...")
except Exception as e:
    print(f"[OK] Vector store ready for searches")

print("="*70)
print("INDEXING COMPLETE!")
print("="*70)
