"""
Quick Start Script - Simplified REFRAG initialization with Ollama
"""
import sys
from pathlib import Path
import os

# Ensure Ollama is used by default
os.environ['REFRAG_DEFAULT_PROVIDER'] = 'ollama'

sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs


def quick_start():
    """Quick start with minimal dependencies (Ollama only)"""
    print("\n" + "=" * 80)
    print("REFRAG QUICK START - Using Ollama")
    print("=" * 80)
    
    # Load configs and override to use Ollama
    print("\n[1/4] Loading configurations...")
    configs = load_all_configs('config')
    configs['llm']['default_provider'] = 'ollama'
    print("[OK] Loaded configs")
    
    # Initialize services
    print("\n[2/4] Initializing services...")
    
    try:
        llm_service = LLMService(configs['llm'])
        print("[OK] LLM service ready (Ollama)")
    except Exception as e:
        print(f"[ERROR] LLM service failed: {e}")
        print("\nMake sure Ollama is running:")
        print("  1. Install Ollama from https://ollama.com")
        print("  2. Run: ollama serve")
        print("  3. Pull model: ollama pull gemma3:4b")
        return None
    
    db_service = DatabaseService('data/rag_system.db')
    print("[OK] Database ready")
    
    vectordb_service = VectorDBService('data/chroma_db')
    print("[OK] Vector database ready")
    
    # Populate RBAC
    print("\n[3/4] Setting up RBAC...")
    rbac_config = configs['rbac']
    count = 0
    for cdr_code, mapping in rbac_config.get('role_mappings', {}).items():
        db_service.execute("""
            INSERT OR REPLACE INTO role_mappings 
            (company_id, department_id, role_id, cdr_code, company_name, 
             department_name, role_name, access_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mapping['company_id'],
            mapping['department_id'],
            mapping['role_id'],
            cdr_code,
            mapping['company_name'],
            mapping['department_name'],
            mapping['role_name'],
            mapping['access_level']
        ))
        count += 1
    print(f"[OK] {count} role mappings loaded")
    
    # Create test users
    print("\n[4/4] Creating test users...")
    test_users = [
        ("alice@acmecorp.com", "112", 1, 1, 2),  # HR Associate
        ("bob@acmecorp.com", "123", 1, 2, 3),    # Engineering Manager  
        ("carol@techco.com", "231", 2, 3, 1),    # Finance Manager
    ]
    
    for user_id, cdr_code, company_id, dept_id, role_id in test_users:
        db_service.execute("""
            INSERT OR REPLACE INTO user_roles 
            (user_id, cdr_code, company_id, department_id, role_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, cdr_code, company_id, dept_id, role_id))
    print(f"[OK] {len(test_users)} test users created")
    
    print("\n" + "=" * 80)
    print("REFRAG SYSTEM READY!")
    print("=" * 80)
    print("\nServices initialized:")
    print("  - LLM: Ollama (gemma3:4b)")
    print("  - Database: SQLite")
    print("  - Vector DB: ChromaDB")
    print("\nTest users:")
    print("  - alice@acmecorp.com (HR)")
    print("  - bob@acmecorp.com (Engineering)")
    print("  - carol@techco.com (Finance)")
    print("\nNext: Run `python example_usage.py` for a complete demo")
    print("=" * 80)
    
    return {
        'llm': llm_service,
        'db': db_service,
        'vectordb': vectordb_service,
        'rbac_config': rbac_config
    }


if __name__ == "__main__":
    services = quick_start()
    if services:
        print("\n[SUCCESS] All services ready!")
    else:
        print("\n[FAILED] Check errors above")
