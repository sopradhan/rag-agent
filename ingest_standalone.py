"""
Pure Standalone Ingestion - No Package Imports
Directly access SQLite and ChromaDB without going through src package
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Direct SQLite operations (no imports)
def ingest_to_sqlite():
    """Directly write to SQLite without imports"""
    
    print("="*70)
    print("INGESTION: SQLite + ChromaDB (Standalone)")
    print("="*70)
    
    db_path = 'data/rag_system.db'
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path, check_same_thread=False)
    cursor = conn.cursor()
    
    # Ensure tables exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            content TEXT NOT NULL,
            chunk_id INTEGER,
            total_chunks INTEGER,
            classification TEXT,
            min_access_level INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
        )
    """)
    
    conn.commit()
    
    # Files to ingest
    files = [
        ('data/engineering_manual.txt', 'engineering', 2, ['read', 'engineer']),
        ('data/hr_policies.txt', 'hr', 1, ['read', 'hr']),
        ('data/company_handbook.txt', 'general', 1, ['read', 'public']),
    ]
    
    total_docs = 0
    
    for file_path, category, access_level, rbac_tags in files:
        if not os.path.exists(file_path):
            print(f"\n[ERROR] File not found: {file_path}")
            continue
        
        print(f"\n[*] Ingesting: {file_path}")
        
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if len(p.strip()) > 50]
        
        print(f"    Found {len(paragraphs)} paragraphs")
        
        # Ingest each paragraph
        for chunk_id, paragraph in enumerate(paragraphs, 1):
            doc_id = f"{category}_chunk_{chunk_id:03d}"
            title = paragraph.split('\n')[0][:100]
            
            try:
                # Insert into documents table
                cursor.execute("""
                    INSERT INTO documents 
                    (doc_id, source, content, chunk_id, total_chunks, classification, min_access_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    Path(file_path).name,
                    paragraph,
                    chunk_id,
                    len(paragraphs),
                    category,
                    access_level
                ))
                
                # Insert metadata
                cursor.execute("""
                    INSERT INTO metadata (doc_id, key, value)
                    VALUES (?, ?, ?)
                """, (doc_id, "title", title))
                
                cursor.execute("""
                    INSERT INTO metadata (doc_id, key, value)
                    VALUES (?, ?, ?)
                """, (doc_id, "category", category))
                
                cursor.execute("""
                    INSERT INTO metadata (doc_id, key, value)
                    VALUES (?, ?, ?)
                """, (doc_id, "source", Path(file_path).name))
                
                cursor.execute("""
                    INSERT INTO metadata (doc_id, key, value)
                    VALUES (?, ?, ?)
                """, (doc_id, "access_level", str(access_level)))
                
                # Insert RBAC tags
                for tag in rbac_tags:
                    cursor.execute("""
                        INSERT INTO metadata (doc_id, key, value)
                        VALUES (?, ?, ?)
                    """, (doc_id, f"rbac_tag_{tag}", "true"))
                
                conn.commit()
                print(f"    [OK] {doc_id}")
                total_docs += 1
                
            except Exception as e:
                print(f"    [ERROR] {doc_id}: {e}")
                conn.rollback()
    
    # Verify
    print("\n" + "="*70)
    print("VERIFICATION: SQLite")
    print("="*70)
    
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    print(f"[OK] Documents: {doc_count}")
    
    cursor.execute("SELECT COUNT(*) FROM metadata")
    meta_count = cursor.fetchone()[0]
    print(f"[OK] Metadata entries: {meta_count}")
    
    # Show sample data
    cursor.execute("""
        SELECT d.doc_id, d.classification, d.min_access_level
        FROM documents d
        LIMIT 5
    """)
    
    print("\nSample documents:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} (level {row[2]})")
    
    # Show RBAC tags
    cursor.execute("""
        SELECT DISTINCT key, value
        FROM metadata
        WHERE key LIKE 'rbac_tag_%'
        LIMIT 10
    """)
    
    print("\nRBAC tags found:")
    for row in cursor.fetchall():
        print(f"  {row[0]} = {row[1]}")
    
    conn.close()
    
    print(f"\n[OK] Total documents ingested: {total_docs}")
    print("[OK] SQLite ingestion complete!")
    
    return total_docs


if __name__ == "__main__":
    total = ingest_to_sqlite()
    print("\n" + "="*70)
    print(f"SUCCESS: {total} documents stored in SQLite")
    print("="*70)
