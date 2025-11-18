"""
Sync SQLite embeddings to ChromaDB
"""

import os
import json
import sqlite3
from pathlib import Path

def sync_to_chromadb():
    """Sync SQLite documents to ChromaDB"""
    
    print("="*70)
    print("SYNC: SQLite → ChromaDB")
    print("="*70)
    
    # Import ChromaDB directly (no package imports)
    try:
        import chromadb
        from chromadb.config import Settings
        print("[OK] ChromaDB imported")
    except ImportError as e:
        print(f"[ERROR] ChromaDB import failed: {e}")
        print("[INFO] Installing chromadb...")
        os.system("pip install chromadb -q")
        import chromadb
    
    # Import sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        print("[OK] SentenceTransformers imported")
    except ImportError:
        print("[ERROR] SentenceTransformers not found")
        print("[INFO] Installing sentence-transformers...")
        os.system("pip install sentence-transformers -q")
        from sentence_transformers import SentenceTransformer
    
    # Initialize embedding model
    print("\n[*] Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("[OK] Model loaded (384 dimensions)")
    
    # Connect to SQLite
    db_path = 'data/rag_system.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    
    # Get all documents from SQLite
    print("\n[*] Reading documents from SQLite...")
    cursor.execute("""
        SELECT doc_id, source, content, classification, min_access_level
        FROM documents
        ORDER BY doc_id
    """)
    
    documents = cursor.fetchall()
    print(f"[OK] Found {len(documents)} documents")
    
    # Initialize ChromaDB
    print("\n[*] Initializing ChromaDB...")
    chroma_path = 'data/chroma_db'
    Path(chroma_path).mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(path=chroma_path)
    
    # Delete existing collection if it exists
    try:
        client.delete_collection(name="rag_documents")
        print("[OK] Removed old collection")
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(
        name="rag_documents",
        metadata={"hnsw:space": "cosine"}
    )
    print("[OK] Created collection 'rag_documents'")
    
    # Generate embeddings and add to ChromaDB
    print("\n[*] Generating embeddings and syncing to ChromaDB...")
    
    documents_to_add = []
    embeddings_to_add = []
    metadatas_to_add = []
    ids_to_add = []
    
    for i, (doc_id, source, content, classification, access_level) in enumerate(documents, 1):
        try:
            # Generate embedding
            embedding = model.encode(content).tolist()
            
            # Get metadata for this document
            cursor.execute("""
                SELECT key, value FROM metadata WHERE doc_id = ?
                ORDER BY key
            """, (doc_id,))
            
            metadata_pairs = cursor.fetchall()
            metadata_dict = {key: value for key, value in metadata_pairs}
            
            # Ensure metadata is not empty
            if not metadata_dict:
                metadata_dict = {
                    "doc_id": doc_id,
                    "source": source,
                    "classification": classification
                }
            
            # Add to lists
            documents_to_add.append(content[:1000])  # Truncate for storage
            embeddings_to_add.append(embedding)
            metadatas_to_add.append(metadata_dict)
            ids_to_add.append(doc_id)
            
            if i % 10 == 0 or i == len(documents):
                print(f"    [OK] {i}/{len(documents)} embeddings generated")
        
        except Exception as e:
            print(f"    [ERROR] {doc_id}: {e}")
    
    # Batch add to ChromaDB
    print("\n[*] Adding to ChromaDB...")
    try:
        collection.add(
            documents=documents_to_add,
            embeddings=embeddings_to_add,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        print(f"[OK] Added {len(ids_to_add)} documents to ChromaDB")
    except Exception as e:
        print(f"[ERROR] Failed to add to ChromaDB: {e}")
        return 0
    
    # Verify
    print("\n" + "="*70)
    print("VERIFICATION: ChromaDB")
    print("="*70)
    
    count = collection.count()
    print(f"[OK] ChromaDB documents: {count}")
    
    # Test query
    print("\n[*] Testing semantic search...")
    test_query = "engineering manual"
    results = collection.query(
        query_texts=[test_query],
        n_results=3
    )
    
    if results and results['documents']:
        print(f"[OK] Search for '{test_query}' returned {len(results['documents'][0])} results")
        for i, doc in enumerate(results['documents'][0][:3], 1):
            print(f"  {i}. {doc[:80]}...")
    
    conn.close()
    
    print("\n[OK] ChromaDB sync complete!")
    return count


if __name__ == "__main__":
    count = sync_to_chromadb()
    print("\n" + "="*70)
    print(f"SUCCESS: {count} documents in ChromaDB")
    print("="*70)
