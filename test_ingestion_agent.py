"""
Test IngestionAgent - Document Processing with RBAC Classification
"""
import sys
from pathlib import Path

# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import IngestionAgent


def test_ingestion_agent():
    print("\n" + "=" * 80)
    print("TESTING INGESTION AGENT")
    print("=" * 80)
    
    # Initialize services
    print("\n[1/3] Initializing services...")
    configs = load_all_configs('config')
    # Use default provider from config (huggingface with your API key)
    
    services = {
        'llm': LLMService(configs['llm']),
        'db': DatabaseService('data/rag_system.db'),
        'vectordb': VectorDBService('data/chroma_db'),
        'rbac_config': configs['rbac']
    }
    print("[OK] Services ready")
    
    # Setup RBAC
    print("\n[2/3] Setting up RBAC...")
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
    print("[OK] RBAC configured")
    
    # Create agent
    print("\n[3/3] Creating IngestionAgent...")
    agent = IngestionAgent(services, configs.get('agent', {}))
    print("[OK] Agent ready")
    
    # Test 1: Create test document
    print("\n" + "=" * 80)
    print("TEST 1: Ingest Single Document")
    print("=" * 80)
    
    test_file = Path("data/test_sources/test_hr_doc.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("""
EMPLOYEE VACATION POLICY - ACME CORP

All full-time employees receive 15 days of paid vacation per year.
Vacation days accrue at a rate of 1.25 days per month.

Part-time employees receive vacation prorated based on hours worked.

Unused vacation can be carried over up to 5 days maximum.
Vacation requests must be submitted 2 weeks in advance.

Contact HR for questions: hr@acmecorp.com
    """)
    
    print(f"\nTest document: {test_file}")
    print(f"Document size: {test_file.stat().st_size} bytes")
    
    # Ingest document
    print("\n[Starting ingestion...]")
    print("Note: Agent will use write_todos to plan the workflow:")
    print("  1. Read file content")
    print("  2. Chunk document")
    print("  3. Extract metadata")
    print("  4. Classify RBAC (LLM determines this is HR/Company data)")
    print("  5. Generate embeddings")
    print("  6. Store in database\n")
    
    result = agent.ingest_document(
        str(test_file),
        metadata={'source_type': 'hr_policy', 'department': 'hr'}
    )
    
    print(f"\n[Result]: {result}")
    
    # Verify ingestion
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    # Check documents table
    docs = services['db'].query("SELECT * FROM documents ORDER BY created_at DESC LIMIT 1")
    if docs:
        doc = docs[0]
        print(f"\n[OK] Document stored:")
        print(f"  ID: {doc['id']}")
        print(f"  Title: {doc.get('title', 'N/A')}")
        print(f"  Source: {doc.get('source', 'N/A')}")
        print(f"  Status: {doc.get('status', 'N/A')}")
        
        # Check chunks
        chunks = services['db'].query(
            "SELECT COUNT(*) as count FROM embedding_metadata WHERE document_id = ?",
            (doc['id'],)
        )
        print(f"  Chunks: {chunks[0]['count']}")
        
        # Check RBAC permissions
        perms = services['db'].query(
            "SELECT * FROM document_permissions WHERE doc_id = ?",
            (doc['id'],)
        )
        print(f"\n[OK] RBAC Permissions ({len(perms)} roles):")
        for perm in perms[:3]:  # Show first 3
            print(f"  - CDR Code: {perm['cdr_code']}, Sensitivity: {perm.get('sensitivity', 'N/A')}")
        
        # Check vector database
        count = services['vectordb'].count()
        print(f"\n[OK] Vector Database:")
        print(f"  Total embeddings: {count}")
        
    else:
        print("\n✗ No documents found in database")
    
    # Test 2: Ingest directory
    print("\n" + "=" * 80)
    print("TEST 2: Ingest Directory (Multiple Documents)")
    print("=" * 80)
    
    # Create more test documents
    test_dir = Path("data/test_sources/hr")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    docs_to_create = [
        ("handbook.txt", "Employee Handbook - Company policies and procedures"),
        ("benefits.txt", "Benefits Guide - Health insurance, 401k, etc"),
        ("pto.txt", "PTO Policy - Vacation, sick leave, holidays")
    ]
    
    for filename, content in docs_to_create:
        (test_dir / filename).write_text(f"{content}\n\nThis is a test document.")
    
    print(f"\nDirectory: {test_dir}")
    print(f"Documents: {len(docs_to_create)}")
    
    print("\n[Starting batch ingestion...]")
    print("Note: Agent will use write_todos to plan parallel processing\n")
    
    result = agent.ingest_directory(str(test_dir))
    print(f"\n[Result]: {result}")
    
    # Final stats
    print("\n" + "=" * 80)
    print("FINAL STATISTICS")
    print("=" * 80)
    
    total_docs = services['db'].query("SELECT COUNT(*) as count FROM documents")[0]['count']
    total_chunks = services['db'].query("SELECT COUNT(*) as count FROM embedding_metadata")[0]['count']
    total_ops = services['db'].query("SELECT COUNT(*) as count FROM agent_operations WHERE agent_name LIKE '%Ingestion%'")[0]['count']
    
    print(f"\n[OK] Total Documents: {total_docs}")
    print(f"[OK] Total Chunks: {total_chunks}")
    print(f"[OK] Agent Operations: {total_ops}")
    print(f"[OK] Vector Embeddings: {services['vectordb'].count()}")
    
    print("\n" + "=" * 80)
    print("INGESTION AGENT TEST COMPLETE")
    print("=" * 80)
    print("\nDeepAgents Features Used:")
    print("  [OK] write_todos - Task planning and decomposition")
    print("  [OK] read_file - Reading document content")
    print("  [OK] Custom tools - chunk, extract_metadata, classify_rbac, etc.")
    print("\nNext: Run test_retrieval_agent.py")
    print("=" * 80)


if __name__ == "__main__":
    test_ingestion_agent()
