#!/usr/bin/env python
"""
Example: Ingest SQLite Knowledge Base into RAG System

This example demonstrates how to ingest data from the SQLite knowledge base
into the RAG system using the UnifiedIngestionAgent.
"""

from src.agents.unified_ingestion import UnifiedIngestionAgent

def main():
    print("=" * 70)
    print("SQLite Knowledge Base Ingestion Example")
    print("=" * 70)
    
    # Initialize ingestion agent
    agent = UnifiedIngestionAgent(use_deep_classifier=True)
    
    # 1. Ingest from knowledge_base table
    print("\n[1] Ingesting from knowledge_base table...")
    result1 = agent.ingest_from_sqlite(
        db_path="data/test_sources/sqlite_sources/knowledge_base.db",
        table_name="knowledge_base",
        text_columns=["title", "content"],
        metadata_columns=["category", "tags"],
        classification="engineering",
        min_access_level=2
    )
    
    # 2. Ingest incidents using query
    print("\n[2] Ingesting active incidents from SQLite query...")
    result2 = agent.ingest_from_sqlite_query(
        db_path="data/test_sources/sqlite_sources/knowledge_base.db",
        query="SELECT id, title, description, severity FROM incidents WHERE status IN ('open', 'investigating', 'in-progress')",
        text_columns=["title", "description"],
        metadata_columns=["id", "severity"],
        classification="security",
        min_access_level=3,
        query_name="active_incidents"
    )
    
    # 3. Ingest procedures
    print("\n[3] Ingesting procedures from SQLite...")
    result3 = agent.ingest_from_sqlite(
        db_path="data/test_sources/sqlite_sources/knowledge_base.db",
        table_name="procedures",
        text_columns=["name", "description", "steps"],
        metadata_columns=[],
        classification="general",
        min_access_level=1
    )
    
    # Summary
    print("\n" + "=" * 70)
    print("INGESTION SUMMARY")
    print("=" * 70)
    
    total_docs = (result1.get("documents_created", 0) + 
                  result2.get("documents_created", 0) + 
                  result3.get("documents_created", 0))
    
    print(f"\nTotal documents ingested: {total_docs}")
    print("\nResults:")
    print(f"  Knowledge Base: {result1.get('documents_created', 0)} docs")
    print(f"  Active Incidents: {result2.get('documents_created', 0)} docs")
    print(f"  Procedures: {result3.get('documents_created', 0)} docs")
    
    print("\n✓ SQLite data successfully ingested into RAG system!")
    print("\nYou can now query this data via the dashboard or API:")
    print("  - Dashboard: http://localhost:8501")
    print("  - Query example: 'What is the database rollback procedure?'")
    print("  - Query example: 'Show me active incidents'")

if __name__ == "__main__":
    main()
