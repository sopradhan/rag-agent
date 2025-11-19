"""
Simple test of ingestion agent - single document
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import IngestionAgent


# Initialize
print("=" * 80)
print("SIMPLE INGESTION TEST")
print("=" * 80)

configs = load_all_configs('config')
services = {
    'llm': LLMService(configs['llm']),
    'db': DatabaseService('data/rag_system.db'),
    'vectordb': VectorDBService('data/chroma_db'),
    'rbac_config': configs['rbac']
}

print("\n[1] Services initialized")

# Setup RBAC
for cdr_code, mapping in configs['rbac'].get('role_mappings', {}).items():
    services['db'].execute("""
        INSERT OR REPLACE INTO role_mappings 
        (company_id, department_id, role_id, cdr_code, company_name, 
         department_name, role_name, access_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        mapping['company_id'], mapping['department_id'], mapping['role_id'],
        cdr_code, mapping['company_name'], mapping['department_name'],
        mapping['role_name'], mapping['access_level']
    ))

print("[2] RBAC configured")

# Create agent
agent = IngestionAgent(services, configs.get('agent', {}))
print("[3] Agent created with 1 tool: ingest_document_from_file(doc_id, file_path)")

# Create test document
test_file = Path("data/test_sources/test_single.txt")
test_file.parent.mkdir(parents=True, exist_ok=True)
test_file.write_text("""COMPANY VACATION POLICY

All employees receive paid vacation:
- Full-time: 15 days per year
- Part-time: Prorated based on hours
- Unused: Can carry over up to 5 days

Vacation requests must be submitted 2 weeks in advance.
Contact HR at hr@company.com for questions.
""")

print(f"\n[4] Test file created: {test_file}")

# Ingest
print("\n" + "=" * 80)
print("INGESTING DOCUMENT")
print("=" * 80)

result = agent.ingest_document(str(test_file))
print(f"\nResult: {result}")

# Check database
print("\n" + "=" * 80)
print("DATABASE STATUS")
print("=" * 80)

docs = services['db'].query("SELECT COUNT(*) as count FROM documents")
doc_count = docs[0]['count'] if docs else 0
print(f"Documents: {doc_count}")

chunks = services['db'].query("SELECT COUNT(*) as count FROM embedding_metadata")
chunk_count = chunks[0]['count'] if chunks else 0
print(f"Chunks: {chunk_count}")

print(f"Embeddings: {services['vectordb'].count()}")

print("\n" + "=" * 80)
if doc_count > 0 and chunk_count > 0:
    print("SUCCESS! Documents ingested with embeddings.")
else:
    print("INCOMPLETE - Documents ingested but embeddings missing.")
print("=" * 80)
