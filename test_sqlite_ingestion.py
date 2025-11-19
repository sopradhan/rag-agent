"""Test SQLite table ingestion"""
import sqlite3
import sys
from pathlib import Path

# Check what's in the knowledge base
db_path = "data/test_sources/sqlite_sources/knowledge_base.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List tables
print("\n=== Tables in knowledge_base.db ===")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for table in tables:
    print(f"  - {table[0]}")
    
    # Show structure
    columns = cursor.execute(f"PRAGMA table_info({table[0]})").fetchall()
    print(f"    Columns: {[col[1] for col in columns]}")
    
    # Count records
    count = cursor.execute(f"SELECT COUNT(*) FROM {table[0]}").fetchone()[0]
    print(f"    Records: {count}")
    
    # Show sample data
    if count > 0:
        sample = cursor.execute(f"SELECT * FROM {table[0]} LIMIT 1").fetchone()
        print(f"    Sample: {sample[:3] if len(sample) > 3 else sample}")

conn.close()

print("\n=== Testing Ingestion Agent ===")
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.services import LLMService, VectorDBService, DatabaseService
from core.config import load_all_configs
from agents import IngestionAgent

print("Loading configuration...")
configs = load_all_configs('config')

services = {
    'llm': LLMService(configs['llm']),
    'db': DatabaseService('data/rag_system.db'),
    'vectordb': VectorDBService('data/chroma_db'),
    'rbac_config': configs['rbac']
}

print("Creating ingestion agent...")
agent = IngestionAgent(services, configs.get('agent', {}))

# Test ingesting a single text document first
print("\n=== Testing Single Document Ingestion ===")
test_file = "data/test_sources/hr/benefits.txt"
if Path(test_file).exists():
    result = agent.ingest_document(
        test_file, 
        metadata={"subject": "HR", "sensitivity": "internal"}
    )
    print(f"\nResult: {result}")
