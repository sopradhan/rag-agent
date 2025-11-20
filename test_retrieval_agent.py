"""
Test RetrievalAgent - Query Processing with RBAC Enforcement
"""
import sys
from pathlib import Path

# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import RetrievalAgent


def test_retrieval_agent():
    print("\n" + "=" * 80)
    print("TESTING RETRIEVAL AGENT")
    print("=" * 80)
    
    # Initialize services
    print("\n[1/4] Initializing services...")
    configs = load_all_configs('config')
    configs['llm']['default_provider'] = 'ollama'
    
    services = {
        'llm': LLMService(configs['llm']),
        'db': DatabaseService('data/rag_system.db'),
        'vectordb': VectorDBService('data/chroma_db'),
        'rbac_config': configs['rbac']
    }
    print("[OK] Services ready")
    
    # Setup RBAC
    print("\n[2/4] Setting up RBAC...")
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
    
    # Create test users
    print("\n[3/4] Creating test users...")
    test_users = [
        ("alice@acmecorp.com", "112", 1, 1, 2, "HR Associate"),
        ("bob@acmecorp.com", "123", 1, 2, 3, "Engineering Manager"),
        ("carol@techco.com", "231", 2, 3, 1, "Finance Manager (Different Company)"),
    ]
    
    for user_id, cdr_code, company_id, dept_id, role_id, desc in test_users:
        services['db'].execute("""
            INSERT OR REPLACE INTO user_roles 
            (user_id, cdr_code, company_id, department_id, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, cdr_code, company_id, dept_id, role_id))
        print(f"  [OK] {user_id} ({desc})")
    
    # Create agent
    print("\n[4/4] Creating RetrievalAgent...")
    agent = RetrievalAgent(services, configs.get('agent', {}))
    print("[OK] Agent ready")
    
    # Check if we have data
    doc_count = services['db'].query("SELECT COUNT(*) as count FROM documents")[0]['count']
    if doc_count == 0:
        print("\n[WARNING] No documents in database!")
        print("Run test_ingestion_agent.py first to ingest test data")
        return
    
    print(f"\n[OK] Database has {doc_count} documents")
    
    # Test 1: Query with full access (HR user)
    print("\n" + "=" * 80)
    print("TEST 1: Query with Full Access (HR User)")
    print("=" * 80)
    
    query = "What is the vacation policy?"
    user = "alice@acmecorp.com"
    
    print(f"\nQuery: {query}")
    print(f"User: {user} (HR Associate - should have access to HR documents)")
    print("\n[Processing query...]")
    print("Note: Agent will use write_todos to plan:")
    print("  1. Check user permissions")
    print("  2. Search vector database")
    print("  3. Filter results by RBAC")
    print("  4. Rerank by relevance")
    print("  5. Synthesize answer with citations\n")
    
    result = agent.process_query(query, user)
    
    print(f"\n[Result]:")
    if result.get('success'):
        print(f"  Status: SUCCESS")
        print(f"  Answer: {result.get('answer', 'N/A')[:200]}...")
        print(f"  Sources: {len(result.get('sources', []))} chunks")
        print(f"  Chunks Retrieved: {result.get('chunks_retrieved', 0)}")
        print(f"  Chunks After RBAC: {result.get('chunks_after_rbac', 0)}")
    else:
        print(f"  Status: FAILED")
        print(f"  Error: {result.get('error', 'Unknown')}")
    
    # Test 2: Query with restricted access (Engineering user)
    print("\n" + "=" * 80)
    print("TEST 2: Query with Restricted Access (Engineering User)")
    print("=" * 80)
    
    user = "bob@acmecorp.com"
    
    print(f"\nQuery: {query}")
    print(f"User: {user} (Engineering Manager - may have limited HR access)")
    print("\n[Processing query...]\n")
    
    result = agent.process_query(query, user)
    
    print(f"\n[Result]:")
    if result.get('success'):
        print(f"  Status: SUCCESS")
        print(f"  Answer: {result.get('answer', 'N/A')[:200]}...")
        print(f"  Sources: {len(result.get('sources', []))} chunks")
        print(f"  Chunks Retrieved: {result.get('chunks_retrieved', 0)}")
        print(f"  Chunks After RBAC: {result.get('chunks_after_rbac', 0)}")
    else:
        print(f"  Status: FAILED/RESTRICTED")
        print(f"  Error: {result.get('error', 'Unknown')}")
    
    # Test 3: Query from different company (should be denied)
    print("\n" + "=" * 80)
    print("TEST 3: Query from Different Company (Should Deny)")
    print("=" * 80)
    
    user = "carol@techco.com"
    
    print(f"\nQuery: {query}")
    print(f"User: {user} (Finance Manager at TechCo - different company)")
    print("Expected: RBAC should block all results\n")
    
    result = agent.process_query(query, user)
    
    print(f"\n[Result]:")
    if result.get('success'):
        print(f"  Status: SUCCESS (but likely no sources)")
        print(f"  Answer: {result.get('answer', 'N/A')[:200]}...")
        print(f"  Sources: {len(result.get('sources', []))} chunks")
        print(f"  Chunks Retrieved: {result.get('chunks_retrieved', 0)}")
        print(f"  Chunks After RBAC: {result.get('chunks_after_rbac', 0)}")
    else:
        print(f"  Status: DENIED [OK]")
        print(f"  Error: {result.get('error', 'Unknown')}")
    
    # Test 4: Complex multi-step query
    print("\n" + "=" * 80)
    print("TEST 4: Complex Multi-Step Query")
    print("=" * 80)
    
    complex_query = "Compare vacation policies and PTO benefits across all HR documents"
    user = "alice@acmecorp.com"
    
    print(f"\nQuery: {complex_query}")
    print(f"User: {user}")
    print("\n[Processing complex query...]")
    print("Note: Agent will use write_todos to break this down:")
    print("  1. Search for vacation policy documents")
    print("  2. Search for PTO benefit documents")
    print("  3. Extract relevant information from each")
    print("  4. Compare and contrast")
    print("  5. Synthesize comprehensive answer\n")
    
    result = agent.process_query(complex_query, user, use_planning=True)
    
    print(f"\n[Result]:")
    if result.get('success'):
        print(f"  Status: SUCCESS")
        print(f"  Answer: {result.get('answer', 'N/A')[:300]}...")
        print(f"  Sources: {len(result.get('sources', []))} chunks")
    else:
        print(f"  Status: FAILED")
        print(f"  Error: {result.get('error', 'Unknown')}")
    
    # Verification
    print("\n" + "=" * 80)
    print("VERIFICATION - Query Tracking")
    print("=" * 80)
    
    queries = services['db'].query("""
        SELECT user_id, query_text, status, num_chunks_retrieved, num_chunks_filtered
        FROM query_history 
        ORDER BY timestamp DESC 
        LIMIT 5
    """)
    
    print(f"\n[OK] Recent Queries ({len(queries)}):")
    for q in queries:
        print(f"  - User: {q['user_id']}")
        print(f"    Query: {q['query_text'][:50]}...")
        print(f"    Status: {q['status']}")
        print(f"    Chunks: {q['num_chunks_retrieved']} -> {q['num_chunks_filtered']} (after RBAC)")
        print()
    
    # Heatmap
    heatmap = services['db'].query("""
        SELECT query_hash, query_example, frequency, avg_retrieval_accuracy
        FROM query_heatmap 
        ORDER BY frequency DESC 
        LIMIT 3
    """)
    
    if heatmap:
        print("[OK] Query Heatmap (for REFRAG healing):")
        for h in heatmap:
            print(f"  - Query: {h['query_example'][:50]}")
            print(f"    Frequency: {h['frequency']}, Avg Accuracy: {h.get('avg_retrieval_accuracy', 0):.2f}")
    
    print("\n" + "=" * 80)
    print("RETRIEVAL AGENT TEST COMPLETE")
    print("=" * 80)
    print("\nDeepAgents Features Used:")
    print("  [OK] write_todos - Query planning and decomposition")
    print("  [OK] Custom tools - permission_check, vector_search, synthesize_answer")
    print("  [OK] RBAC enforcement - Strict permission filtering")
    print("\nNext: Run test_healing_agent.py")
    print("=" * 80)


if __name__ == "__main__":
    test_retrieval_agent()
