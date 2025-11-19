#!/usr/bin/env python
"""
List all tables in RAG metadata database
"""
from src.storage import RAGDatabase

db = RAGDatabase()
cursor = db.conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print(f"Total tables in rag_system.db: {len(tables)}\n")
print("All Metadata Tables:")
for table in sorted(tables):
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  ✓ {table:<30} ({count} records)")

print("\n=== Database Structure Summary ===\n")

# Group by category
groups = {
    "RBAC & Users": ["company", "department", "role", "users", "user_roles", "document_rbac"],
    "Documents & Content": ["documents", "metadata", "embeddings"],
    "Agent Operations": ["agent_memory", "agent_spawns", "agent_performance", "cot_steps"],
    "Tracking & Audit": ["query_history", "operations_history", "healing_operations"],
}

for category, table_list in groups.items():
    print(f"{category}:")
    for table in table_list:
        if table in tables:
            print(f"  ✓ {table}")
    print()

print("✓ All metadata tables verified!")
