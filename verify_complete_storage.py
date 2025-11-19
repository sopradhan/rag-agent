#!/usr/bin/env python3
"""Verify that embeddings, metadata, and RBAC are properly stored"""

import sqlite3
import json
from pathlib import Path

print("\n" + "="*80)
print("STORAGE VERIFICATION")
print("="*80 + "\n")

# SQLite verification
print("[SQLite Database Verification]")
conn = sqlite3.connect('data/rag_system.db')
cursor = conn.cursor()

# Check documents
cursor.execute("SELECT id, title, doc_type FROM documents")
docs = cursor.fetchall()
print(f"\n1. Documents Table: {len(docs)} records")
for doc in docs:
    print(f"   - ID: {doc[0]}, Title: {doc[1]}, Type: {doc[2]}")

# Check embedding metadata
cursor.execute("SELECT document_id, chunk_id, chunk_strategy, embedding_model FROM embedding_metadata")
chunks = cursor.fetchall()
print(f"\n2. Embedding Metadata Table: {len(chunks)} records (metadata only, NO vectors)")
for chunk in chunks:
    print(f"   - Doc: {chunk[0]}, Chunk: {chunk[1]}")
    print(f"     Strategy: {chunk[2]}, Model: {chunk[3]}")

# Check document metadata (key-value pairs)
cursor.execute("SELECT document_id, key, value FROM document_metadata ORDER BY document_id, key")
metadata = cursor.fetchall()
print(f"\n3. Document Metadata Table: {len(metadata)} key-value pairs")
current_doc = None
for doc_id, key, value in metadata:
    if doc_id != current_doc:
        current_doc = doc_id
        print(f"\n   Document: {doc_id}")
    if key in ['embedding_model', 'embedding_dimension', 'chunking_strategy', 'chunk_size', 'chunk_overlap']:
        print(f"     • {key}: {value}")

# Check RBAC permissions
cursor.execute("SELECT doc_id, cdr_code, sensitivity, subject FROM document_permissions")
perms = cursor.fetchall()
print(f"\n4. Document Permissions Table (RBAC): {len(perms)} records")
for doc_id, cdr_code, sensitivity, subject in perms:
    print(f"   - Doc: {doc_id}, CDR: {cdr_code}, Subject: {subject}, Sensitivity: {sensitivity}")

conn.close()

# ChromaDB verification
print("\n\n[ChromaDB Verification]")
import sys
sys.path.insert(0, str(Path('.').absolute()))
from core.services.vectordb_service import VectorDBService

vectordb = VectorDBService('data/chroma_db')
count = vectordb.count()
print(f"1. ChromaDB Collection Count: {count} embeddings")

if count > 0:
    samples = vectordb.peek(limit=3)
    print(f"\n2. Sample Embeddings:")
    embeddings_list = samples.get('embeddings', [None]*len(samples['ids'])) if samples.get('embeddings') is not None else [None]*len(samples['ids'])
    for doc_id, metadata, document, embedding in zip(
        samples['ids'],
        samples['metadatas'],
        samples['documents'],
        embeddings_list
    ):
        print(f"\n   ID: {doc_id}")
        print(f"   Text: {document[:60]}...")
        if metadata:
            print(f"   Metadata:")
            print(f"     • subject: {metadata.get('subject')}")
            print(f"     • sensitivity: {metadata.get('sensitivity')}")
            print(f"     • keywords: {metadata.get('keywords')}")
            print(f"     • cdr_codes: {metadata.get('cdr_codes')}")
        if embedding is not None:
            embedding_list = embedding if isinstance(embedding, list) else embedding.tolist() if hasattr(embedding, 'tolist') else None
            if embedding_list:
                print(f"   Embedding: ✅ STORED ({len(embedding_list)} dimensions)")
                print(f"     Values: [{embedding_list[0]:.4f}, {embedding_list[1]:.4f}, {embedding_list[2]:.4f}, ... {embedding_list[-1]:.4f}]")
        else:
            print(f"   Embedding: ❌ NOT STORED")

print("\n" + "="*80)
print("✅ STORAGE VERIFICATION COMPLETE")
print("="*80 + "\n")
