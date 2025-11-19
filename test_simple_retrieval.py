"""
Simple Retrieval Test - Direct agent invocation with proper workflow
Tests the retrieval agent with a simpler prompt that guides proper tool usage
"""
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import RetrievalAgent


def test_simple_retrieval():
    print("\n" + "=" * 100)
    print("SIMPLE RETRIEVAL TEST")
    print("=" * 100)
    
    # Initialize
    print("\n[1/2] Initializing services...")
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
    print("[2/2] Setting up admin user...")
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
    
    print(f"[OK] Admin user setup ({len(admin_cdrs)} CDR codes)\n")
    
    # Initialize agent
    agent = RetrievalAgent(services, configs.get('agent', {}))
    
    # Test queries
    test_queries = [
        "What documents are available in the system?",
        "List all employees in the system",
        "What is the company handbook about?",
    ]
    
    print("=" * 100)
    print("TESTING QUERIES")
    print("=" * 100)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}] Query: {query}")
        print(f"    User: {admin_user} (Admin)")
        
        try:
            result = agent.process_query(query, admin_user, use_planning=False)
            
            if result.get('success'):
                print(f"    Status: SUCCESS")
                print(f"    Time: {result.get('execution_time_ms')}ms")
                answer = result.get('answer', '')
                if isinstance(answer, str):
                    preview = answer[:200] if len(answer) > 200 else answer
                    print(f"    Answer Preview: {preview}...")
                else:
                    print(f"    Answer: {answer}")
            else:
                print(f"    Status: FAILED")
                print(f"    Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"    Status: ERROR")
            print(f"    Exception: {str(e)}")
    
    print("\n" + "=" * 100)
    print("TEST COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    test_simple_retrieval()
