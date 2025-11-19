"""
Test RetrievalAgent Through Orchestrator with Results Table
Creates questions, retrieves answers via orchestrator with admin role,
stores complete responses and metadata in JSON format
"""
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import MasterOrchestrator


def create_results_table(db_service):
    """Create table to store retrieval results with full metadata"""
    db_service.execute("""
        CREATE TABLE IF NOT EXISTS retrieval_results (
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
            sources TEXT,
            relevance_scores TEXT,
            metadata TEXT,
            execution_time_ms INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("[OK] Results table created/verified")


def generate_test_questions():
    """Generate test questions to ask the system"""
    questions = [
        "What is the vacation policy?",
        "How many days of PTO do employees get?",
        "What are the benefits for health insurance?",
        "Tell me about the employee handbook",
        "What are the company policies?",
        "Describe the benefits package",
        "What is the PTO policy?",
        "How much vacation time do I get per year?",
    ]
    return questions


def extract_rbac_report(response_text):
    """Extract RBAC report from response"""
    if "[RBAC REPORT]" in response_text:
        start = response_text.find("[RBAC REPORT]")
        end = response_text.find("[", start + 1)
        if end == -1:
            return response_text[start:]
        return response_text[start:end].strip()
    return "No RBAC report found"


def extract_thought_process(response_text):
    """Extract thought process from response"""
    if "[THOUGHT PROCESS]" in response_text:
        start = response_text.find("[THOUGHT PROCESS]")
        end = response_text.find("[", start + 1)
        if end == -1:
            end = response_text.find("[RESULTS]")
        if end == -1:
            end = len(response_text)
        return response_text[start:end].strip()
    return "No thought process provided"


def extract_answer(response_text):
    """Extract main answer from response"""
    if "[RESULT]" in response_text:
        start = response_text.find("[RESULT]")
        return response_text[start:].strip()
    elif "[RESULTS]" in response_text:
        start = response_text.find("[RESULTS]")
        end = response_text.find("[RBAC", start)
        if end == -1:
            return response_text[start:].strip()
        return response_text[start:end].strip()
    return response_text[:500]  # First 500 chars


def test_retrieval_with_orchestrator():
    configs = load_all_configs('config')
    configs['llm']['default_provider'] = 'ollama'
    
    services = {
        'llm': LLMService(configs['llm']),
        'db': DatabaseService('data/rag_system.db'),
        'vectordb': VectorDBService('data/chroma_db'),
        'rbac_config': configs['rbac']
    }
    
    admin_user_id = "admin@acmecorp.com"
    admin_cdr_codes = list(configs['rbac'].get('role_mappings', {}).keys())
    
    create_results_table(services['db'])
    orchestrator = MasterOrchestrator(services, configs)
    
    print("\n" + "=" * 100)
    print("EXECUTING QUESTIONS AND STORING RESULTS")
    print("=" * 100)
    
    questions = generate_test_questions()
    results_stored = 0
    
    for idx, question in enumerate(questions, 1):
        print(f"\n[{idx}/{len(questions)}] Processing question...")
        print(f"     Question: {question}")
        print(f"     User: {admin_user_id} (Admin - Full Access)")
        
        import time
        start_time = time.time()
        
        try:
            # Call retrieval through orchestrator
            result = orchestrator.query(
                query=question,
                user_id=admin_user_id,
                use_planning=False
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Extract components from response
            response_text = result.get('response', str(result))
            thought_process = extract_thought_process(response_text)
            rbac_report = extract_rbac_report(response_text)
            answer = extract_answer(response_text)
            
            # Build metadata JSON
            metadata = {
                "success": result.get('success', True),
                "query_type": "admin_retrieval",
                "response_time_ms": execution_time,
                "response_messages": result.get('messages', 0),
                "full_response_length": len(response_text),
                "thought_process_length": len(thought_process),
                "rbac_report_present": "[RBAC REPORT]" in response_text,
                "answer_length": len(answer),
                "timestamp": datetime.now().isoformat()
            }
            
            # Extract RBAC metrics if available
            if "Total retrieved:" in rbac_report:
                try:
                    import re
                    retrieved = re.search(r'Total retrieved[:\s]+(\d+)', rbac_report)
                    granted = re.search(r'granted[:\s]+(\d+)', rbac_report)
                    denied = re.search(r'denied[:\s]+(\d+)', rbac_report)
                    
                    chunks_retrieved = int(retrieved.group(1)) if retrieved else 0
                    chunks_granted = int(granted.group(1)) if granted else 0
                    chunks_denied = int(denied.group(1)) if denied else 0
                except:
                    chunks_retrieved = 0
                    chunks_granted = 0
                    chunks_denied = 0
            else:
                chunks_retrieved = 0
                chunks_granted = 0
                chunks_denied = 0
            
            # Store in results table
            services['db'].execute("""
                INSERT INTO retrieval_results 
                (question, user_id, user_role, user_cdr_codes, retrieval_status,
                 chunks_retrieved, chunks_granted, chunks_denied,
                 rbac_report, thought_process, answer, metadata, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                question,
                admin_user_id,
                "Admin",
                json.dumps(admin_cdr_codes),
                "success" if result.get('success') else "failed",
                chunks_retrieved,
                chunks_granted,
                chunks_denied,
                rbac_report,
                thought_process,
                answer,
                json.dumps(metadata),
                execution_time
            ))
            
            results_stored += 1
            
            print(f"     Status: SUCCESS")
            print(f"     Execution Time: {execution_time}ms")
            print(f"     Chunks Retrieved: {chunks_retrieved}, Granted: {chunks_granted}, Denied: {chunks_denied}")
            print(f"     Answer Length: {len(answer)} chars")
            print(f"     RBAC Report: {len(rbac_report)} chars")
            
        except Exception as e:
            print(f"     Status: FAILED")
            print(f"     Error: {str(e)}")
            
            # Store failed result
            services['db'].execute("""
                INSERT INTO retrieval_results 
                (question, user_id, user_role, user_cdr_codes, retrieval_status,
                 answer, metadata, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                question,
                admin_user_id,
                "Admin",
                json.dumps(admin_cdr_codes),
                "failed",
                f"Error: {str(e)}",
                json.dumps({"error": str(e), "timestamp": datetime.now().isoformat()}),
                int((time.time() - start_time) * 1000)
            ))
    
    # Verify and display results
    print("\n" + "=" * 100)
    print("RESULTS SUMMARY")
    print("=" * 100)
    
    # Count results
    total_results = services['db'].query("SELECT COUNT(*) as count FROM retrieval_results")[0]['count']
    successful = services['db'].query("SELECT COUNT(*) as count FROM retrieval_results WHERE retrieval_status = 'success'")[0]['count']
    failed = total_results - successful
    
    print(f"\n[OK] Total Results Stored: {total_results}")
    print(f"     Successful: {successful}")
    print(f"     Failed: {failed}")
    print(f"     Success Rate: {(successful/total_results*100):.1f}%" if total_results > 0 else "     Success Rate: N/A")
    
    # Display sample results
    print("\n[SAMPLE RESULTS - First 3 Questions]")
    print("=" * 100)
    
    sample_results = services['db'].query("""
        SELECT result_id, question, retrieval_status, chunks_retrieved, 
               chunks_granted, execution_time_ms, LENGTH(answer) as answer_len
        FROM retrieval_results 
        ORDER BY timestamp 
        LIMIT 3
    """)
    
    for i, row in enumerate(sample_results, 1):
        print(f"\n[{i}] Question: {row['question']}")
        print(f"    Status: {row['retrieval_status']}")
        print(f"    Chunks - Retrieved: {row['chunks_retrieved']}, Granted: {row['chunks_granted']}")
        print(f"    Answer Length: {row['answer_len']} chars")
        print(f"    Execution Time: {row['execution_time_ms']}ms")
    
    # Show schema verification
    print("\n" + "=" * 100)
    print("RESULTS TABLE SCHEMA")
    print("=" * 100)
    
    schema_info = services['db'].query("""
        PRAGMA table_info(retrieval_results)
    """)
    
    print("\nColumns in retrieval_results table:")
    for col in schema_info:
        print(f"  - {col['name']}: {col['type']}")
    
    # Display data types stored
    print("\n" + "=" * 100)
    print("DATA STORED IN RESULTS TABLE")
    print("=" * 100)
    
    sample = services['db'].query("""
        SELECT result_id, question, user_id, user_cdr_codes, retrieval_status,
               chunks_retrieved, rbac_report, answer, metadata
        FROM retrieval_results 
        LIMIT 1
    """)
    
    if sample:
        row = sample[0]
        print(f"\n[Example Record - ID: {row['result_id']}]")
        print(f"\nQuestion: {row['question']}")
        print(f"User: {row['user_id']}")
        print(f"Status: {row['retrieval_status']}")
        print(f"Chunks Retrieved: {row['chunks_retrieved']}")
        
        print(f"\nUser CDR Codes (JSON):")
        try:
            cdr_codes = json.loads(row['user_cdr_codes'])
            for code in cdr_codes[:3]:
                print(f"  - {code}")
            if len(cdr_codes) > 3:
                print(f"  ... and {len(cdr_codes)-3} more")
        except:
            print(f"  {row['user_cdr_codes']}")
        
        print(f"\nMetadata (JSON):")
        try:
            metadata = json.loads(row['metadata'])
            for key, value in list(metadata.items())[:5]:
                print(f"  {key}: {value}")
            if len(metadata) > 5:
                print(f"  ... and {len(metadata)-5} more fields")
        except:
            print(f"  {row['metadata']}")
        
        print(f"\nRBAC Report (First 200 chars):")
        print(f"  {row['rbac_report'][:200]}...")
        
        print(f"\nAnswer (First 300 chars):")
        print(f"  {row['answer'][:300]}...")
    
    print("\n" + "=" * 100)
    print("TEST COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    test_retrieval_with_orchestrator()
