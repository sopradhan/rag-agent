"""
Quick Test: RetrievalAgent Results Table
Minimal test with single question to verify results table and JSON metadata storage
"""
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import RetrievalAgent


def test_quick_retrieval():
    print("\n" + "=" * 100)
    print("QUICK RETRIEVAL TEST - RESULTS TABLE WITH JSON METADATA")
    print("=" * 100)
    
    # Initialize
    print("\n[1/3] Initializing services...")
    configs = load_all_configs('config')
    configs['llm']['default_provider'] = 'ollama'
    
    services = {
        'llm': LLMService(configs['llm']),
        'db': DatabaseService('data/rag_system.db'),
        'vectordb': VectorDBService('data/chroma_db'),
        'rbac_config': configs['rbac']
    }
    print("[OK] Services initialized")
    
    # Setup RBAC and admin user
    print("\n[2/3] Setting up admin user...")
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
    
    admin_user = "admin@acmecorp.com"
    admin_cdrs = list(configs['rbac'].get('role_mappings', {}).keys())
    for cdr in admin_cdrs:
        services['db'].execute("""
            INSERT OR REPLACE INTO user_roles (user_id, cdr_code) VALUES (?, ?)
        """, (admin_user, cdr))
    
    print(f"[OK] Admin user setup ({len(admin_cdrs)} CDR codes)")
    
    # Create results table
    print("\n[3/3] Creating results table...")
    services['db'].execute("""
        DROP TABLE IF EXISTS retrieval_results
    """)
    services['db'].execute("""
        CREATE TABLE retrieval_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_role TEXT,
            user_cdr_codes TEXT,
            retrieval_status TEXT,
            chunks_retrieved INTEGER,
            chunks_granted INTEGER,
            chunks_denied INTEGER,
            rbac_report TEXT,
            thought_process TEXT,
            answer TEXT,
            metadata TEXT,
            execution_time_ms INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[OK] Results table created")
    
    # Initialize agent
    agent = RetrievalAgent(services, configs.get('agent', {}))
    
    # Test single question
    print("\n" + "=" * 100)
    print("PROCESSING SINGLE QUESTION")
    print("=" * 100)
    
    question = "What is the vacation policy?"
    print(f"\nQuestion: {question}")
    print(f"User: {admin_user} (Admin - Full Access)")
    print(f"CDR Codes: {admin_cdrs[:3]}..." if len(admin_cdrs) > 3 else f"CDR Codes: {admin_cdrs}")
    
    import time
    start = time.time()
    
    try:
        result = agent.process_query(question, admin_user, use_planning=False)
        exec_time = int((time.time() - start) * 1000)
        
        response = result.get('response', str(result))
        
        # Extract sections
        thought_process = ""
        rbac_report = ""
        answer = ""
        
        if "[THOUGHT PROCESS]" in response:
            start_idx = response.find("[THOUGHT PROCESS]")
            end_idx = response.find("[", start_idx + 1)
            if end_idx == -1:
                end_idx = len(response)
            thought_process = response[start_idx:end_idx].strip()
        
        if "[RBAC REPORT]" in response:
            start_idx = response.find("[RBAC REPORT]")
            end_idx = response.find("[", start_idx + 1)
            if end_idx == -1:
                end_idx = len(response)
            rbac_report = response[start_idx:end_idx].strip()
        
        if "[RESULT]" in response:
            start_idx = response.find("[RESULT]")
            answer = response[start_idx:].strip()
        else:
            answer = response[:500]
        
        # Parse RBAC metrics
        chunks_retrieved = 0
        chunks_granted = 0
        chunks_denied = 0
        
        if rbac_report:
            import re
            m = re.search(r'retrieved[:\s]+(\d+)', rbac_report)
            if m:
                chunks_retrieved = int(m.group(1))
            m = re.search(r'granted[:\s]+(\d+)', rbac_report)
            if m:
                chunks_granted = int(m.group(1))
            m = re.search(r'denied[:\s]+(\d+)', rbac_report)
            if m:
                chunks_denied = int(m.group(1))
        
        # Create metadata JSON
        metadata = {
            "success": True,
            "response_time_ms": exec_time,
            "response_length": len(response),
            "thought_process_length": len(thought_process),
            "rbac_report_length": len(rbac_report),
            "answer_length": len(answer),
            "has_thought_process": len(thought_process) > 0,
            "has_rbac_report": len(rbac_report) > 0,
            "has_result": len(answer) > 0,
            "admin_mode": True,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in database
        result_id = services['db'].insert_and_get_id("""
            INSERT INTO retrieval_results 
            (question, user_id, user_role, user_cdr_codes, retrieval_status,
             chunks_retrieved, chunks_granted, chunks_denied,
             rbac_report, thought_process, answer, metadata, execution_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question,
            admin_user,
            "Admin",
            json.dumps(admin_cdrs),
            "success",
            chunks_retrieved,
            chunks_granted,
            chunks_denied,
            rbac_report,
            thought_process,
            answer,
            json.dumps(metadata),
            exec_time
        ))
        
        print(f"\nStatus: SUCCESS")
        print(f"Result ID: {result_id}")
        print(f"Execution Time: {exec_time}ms")
        print(f"Chunks - Retrieved: {chunks_retrieved}, Granted: {chunks_granted}, Denied: {chunks_denied}")
        print(f"Sections - Thought Process: {len(thought_process)} chars, RBAC Report: {len(rbac_report)} chars, Answer: {len(answer)} chars")
        
    except Exception as e:
        print(f"\nStatus: FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Display stored result
    print("\n" + "=" * 100)
    print("RESULT STORED IN DATABASE")
    print("=" * 100)
    
    stored = services['db'].query("SELECT * FROM retrieval_results LIMIT 1")
    
    if stored:
        row = stored[0]
        print(f"\n[Result Record]")
        print(f"  ID: {row['result_id']}")
        print(f"  Question: {row['question']}")
        print(f"  User: {row['user_id']}")
        print(f"  Status: {row['retrieval_status']}")
        print(f"  Chunks Retrieved: {row['chunks_retrieved']}")
        print(f"  Chunks Granted: {row['chunks_granted']}")
        print(f"  Chunks Denied: {row['chunks_denied']}")
        print(f"  Execution Time: {row['execution_time_ms']}ms")
        
        print(f"\n[User CDR Codes (JSON)]")
        try:
            cdrs = json.loads(row['user_cdr_codes'])
            print(f"  Total CDR codes: {len(cdrs)}")
            for cdr in cdrs[:5]:
                print(f"    - {cdr}")
            if len(cdrs) > 5:
                print(f"    ... and {len(cdrs)-5} more")
        except Exception as e:
            print(f"  Error parsing CDR codes: {e}")
        
        print(f"\n[Metadata (JSON)]")
        try:
            meta = json.loads(row['metadata'])
            for key, value in meta.items():
                if isinstance(value, str) and len(str(value)) > 50:
                    print(f"  {key}: {str(value)[:50]}...")
                else:
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"  Error parsing metadata: {e}")
        
        print(f"\n[RBAC Report (First 300 chars)]")
        rbac = row['rbac_report'][:300] if row['rbac_report'] else "N/A"
        print(f"  {rbac}...")
        
        print(f"\n[Thought Process (First 300 chars)]")
        tp = row['thought_process'][:300] if row['thought_process'] else "N/A"
        print(f"  {tp}...")
        
        print(f"\n[Answer (First 300 chars)]")
        ans = row['answer'][:300] if row['answer'] else "N/A"
        print(f"  {ans}...")
    
    # Show query examples
    print("\n" + "=" * 100)
    print("QUERY EXAMPLES - How to Access Results")
    print("=" * 100)
    
    print("\n[1] Get all results:")
    print("  SELECT * FROM retrieval_results")
    
    print("\n[2] Get specific columns:")
    print("  SELECT result_id, question, retrieval_status, chunks_retrieved FROM retrieval_results")
    
    print("\n[3] Extract metadata JSON:")
    print("  SELECT result_id, metadata FROM retrieval_results")
    
    print("\n[4] Extract user CDR codes:")
    print("  SELECT result_id, user_cdr_codes FROM retrieval_results")
    
    print("\n[5] Get statistics:")
    print("  SELECT COUNT(*) as total, ")
    print("         SUM(chunks_retrieved) as total_chunks,")
    print("         AVG(execution_time_ms) as avg_time_ms")
    print("  FROM retrieval_results")
    
    print("\n" + "=" * 100)
    print("TEST COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    test_quick_retrieval()
