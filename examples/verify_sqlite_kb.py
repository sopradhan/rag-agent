#!/usr/bin/env python
"""
Verify SQLite knowledge base was created correctly
"""
import sqlite3

db_path = 'data/test_sources/sqlite_sources/knowledge_base.db'

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Show tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("Tables in knowledge_base.db:")
    for table in tables:
        print(f"  - {table}")
    
    # Show sample data
    print("\nSample Knowledge Base Articles:")
    cursor.execute("SELECT id, title, category FROM knowledge_base LIMIT 2")
    for row in cursor.fetchall():
        print(f"  [{row['id']}] {row['title']} ({row['category']})")
    
    print("\nSample Incidents:")
    cursor.execute("SELECT id, title, severity, status FROM incidents LIMIT 2")
    for row in cursor.fetchall():
        print(f"  [{row['id']}] {row['title']} - {row['severity']} ({row['status']})")
    
    print("\nSample Procedures:")
    cursor.execute("SELECT id, name FROM procedures LIMIT 2")
    for row in cursor.fetchall():
        print(f"  [{row['id']}] {row['name']}")
    
    conn.close()
    print("\n[OK] SQLite knowledge base verified successfully!")
    
except Exception as e:
    print(f"[ERROR] Failed to verify: {e}")
