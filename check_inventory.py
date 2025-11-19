"""
Debug: Check what's actually in the database and vector storage
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.services import DatabaseService, VectorDBService
from core.config import load_all_configs

print("\n" + "=" * 100)
print("DATABASE INVENTORY CHECK")
print("=" * 100)

# Initialize services
configs = load_all_configs('config')
db = DatabaseService('data/rag_system.db')
vectordb = VectorDBService('data/chroma_db')

# Check documents table
print("\n[1] Documents in Database:")
docs = db.query("SELECT COUNT(*) as count FROM documents")
print(f"    Total documents: {docs[0]['count']}")

doc_list = db.query("SELECT document_id, document_name, document_type FROM documents LIMIT 10")
for doc in doc_list:
    print(f"      - {doc['document_id']}: {doc['document_name']} ({doc['document_type']})")

# Check chunks
print("\n[2] Chunks in Database:")
chunks = db.query("SELECT COUNT(*) as count FROM chunks")
print(f"    Total chunks: {chunks[0]['count']}")

chunk_list = db.query("""
    SELECT chunk_id, document_id, chunk_sequence, chunk_text 
    FROM chunks 
    LIMIT 5
""")
for chunk in chunk_list:
    text_preview = chunk['chunk_text'][:100] if chunk['chunk_text'] else 'N/A'
    print(f"      - {chunk['chunk_id']}: {text_preview}...")

# Check embedding metadata
print("\n[3] Embedding Metadata in Database:")
embed = db.query("SELECT COUNT(*) as count FROM embedding_metadata")
print(f"    Total embeddings: {embed[0]['count']}")

embed_list = db.query("""
    SELECT chunk_id, embedding_model, dimension, created_at
    FROM embedding_metadata
    LIMIT 5
""")
for e in embed_list:
    print(f"      - {e['chunk_id']}: {e['embedding_model']} ({e['dimension']} dims)")

# Check ChromaDB vectors
print("\n[4] Vectors in ChromaDB:")
vector_count = vectordb.count()
print(f"    Total vectors in collection: {vector_count}")

# Try a sample search
print("\n[5] Test Vector Search:")
try:
    results = vectordb.search("What is the vacation policy?", k=3)
    print(f"    Search returned {len(results)} results")
    for i, result in enumerate(results, 1):
        print(f"      [{i}] ID: {result.get('id', 'N/A')}")
        print(f"          Distance: {result.get('distance', 'N/A')}")
        if 'metadata' in result:
            meta = result['metadata']
            if isinstance(meta, dict):
                for key, value in meta.items():
                    print(f"          {key}: {value}")
except Exception as e:
    print(f"    Error: {e}")

# Check RBAC setup
print("\n[6] RBAC Configuration:")
roles = db.query("SELECT COUNT(*) as count FROM role_mappings")
print(f"    Total roles defined: {roles[0]['count']}")

role_list = db.query("SELECT cdr_code, role_name, access_level FROM role_mappings LIMIT 5")
for role in role_list:
    print(f"      - {role['cdr_code']}: {role['role_name']} ({role['access_level']})")

# Check document permissions
print("\n[7] Document Permissions:")
perms = db.query("SELECT COUNT(*) as count FROM document_permissions")
print(f"    Total permission entries: {perms[0]['count']}")

perm_list = db.query("""
    SELECT document_id, cdr_code 
    FROM document_permissions 
    LIMIT 10
""")
for perm in perm_list:
    print(f"      - Doc {perm['document_id']}: CDR {perm['cdr_code']}")

print("\n" + "=" * 100)
print("END OF INVENTORY CHECK")
print("=" * 100)
