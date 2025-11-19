from src.storage import RAGDatabase
db = RAGDatabase()

print('\n[SCHEMA] Role table:')
schema = db.conn.execute('PRAGMA table_info(role)').fetchall()
for col in schema:
    print(f'  {col[1]} ({col[2]})')

print('\n[DATA] Roles:')
roles = db.conn.execute('SELECT * FROM role').fetchall()
for r in roles:
    print(f'  {dict(r)}')

print('\n[DATA] Users (first 3):')
users = db.conn.execute('SELECT * FROM users LIMIT 3').fetchall()
for u in users:
    print(f'  {dict(u)}')

print('\n[DATA] Documents (first 3):')
docs = db.conn.execute('SELECT * FROM documents LIMIT 3').fetchall()
for d in docs:
    d_dict = dict(d)
    print(f'  ID: {d_dict.get("doc_id")}, Title: {d_dict.get("title")}, Classification: {d_dict.get("classification")}, MinLevel: {d_dict.get("min_access_level")}')

print('\n[VECTOR STORE] Documents in collection:')
try:
    collection = db.vector_store.collection
    if collection:
        all_docs = collection.get()
        print(f'  Total: {len(all_docs["ids"])}')
        for i, doc_id in enumerate(all_docs["ids"][:3]):
            metadata = all_docs["metadatas"][i] if all_docs.get("metadatas") else {}
            print(f'  {i+1}. ID={doc_id}, Metadata: {metadata}')
except Exception as e:
    print(f'  Error: {e}')
