# SQLite3 Data Source Ingestion Guide

## Overview

The RAG system now supports ingesting data directly from SQLite3 databases. This enables you to:

- Extract knowledge from existing business databases
- Ingest structured data (tables, records)
- Convert database records into searchable documents
- Maintain RBAC and classification
- Automatically chunk large text fields

## Key Concepts

### Data Flow

```
SQLite Database
    ↓
Extract Table/Query
    ↓
Combine Text Fields
    ↓
Generate Documents
    ↓
Chunk Large Content
    ↓
Generate Embeddings (ChromaDB)
    ↓
Store Metadata (SQLite)
    ↓
RBAC Applied
    ↓
Ready for Search
```

### Embeddings Table (Metadata Only)

The `embeddings` table in SQLite now tracks:
- Which documents have embeddings
- Which model was used (e.g., `all-MiniLM-L6-v2`)
- Vector dimensions (e.g., 384)
- Vector store location (e.g., `chromadb`)
- Sync status

**Important**: Actual vectors are stored in ChromaDB, not in SQLite. SQLite acts as metadata/audit trail.

### Storage Architecture

| Component | Purpose | Storage |
|-----------|---------|---------|
| Documents | Content, chunks, classification | SQLite `documents` table |
| Embeddings | Metadata about vectors | SQLite `embeddings` table (metadata only) |
| Vectors | Actual embeddings (384 dims) | ChromaDB |
| RBAC | Access control | SQLite `document_rbac` table |

## Usage Examples

### 1. Ingest Entire Table

```python
from src.agents.unified_ingestion import UnifiedIngestionAgent

agent = UnifiedIngestionAgent(use_deep_classifier=True)

# Ingest knowledge base table
result = agent.ingest_from_sqlite(
    db_path="data/knowledge_base.db",
    table_name="knowledge_base",
    text_columns=["title", "content", "description"],
    metadata_columns=["category", "source", "tags"],
    classification="engineering",
    min_access_level=2
)

print(f"Ingestion result: {result}")
# Output:
# {
#   'status': 'success',
#   'table': 'knowledge_base',
#   'records_processed': 150,
#   'documents_created': 320,
#   'errors': 0
# }
```

### 2. Ingest from Custom SQL Query

```python
# Ingest only open incidents from past 30 days
result = agent.ingest_from_sqlite_query(
    db_path="data/operations.db",
    query="""
        SELECT id, title, description, severity, created_by 
        FROM incidents 
        WHERE status = 'open' 
        AND created_date > datetime('now', '-30 days')
    """,
    text_columns=["title", "description"],
    metadata_columns=["id", "severity", "created_by"],
    classification="security",
    min_access_level=3,
    query_name="active_incidents"
)
```

### 3. Batch Ingest Multiple Tables

```python
from src.storage import RAGDatabase
from src.storage.vector_store import ChromaVectorStore
from src.subagents import SQLiteIngestionSubagent

db = RAGDatabase()
vector_store = ChromaVectorStore()
sqlite_agent = SQLiteIngestionSubagent(db, vector_store)

# Configuration for multiple sources
sources = [
    {
        "db": "data/engineering.db",
        "table": "api_docs",
        "text_cols": ["endpoint", "description", "parameters"],
        "classification": "engineering",
        "level": 2
    },
    {
        "db": "data/hr.db",
        "table": "policies",
        "text_cols": ["policy_name", "content"],
        "classification": "hr",
        "level": 1
    },
    {
        "db": "data/sales.db",
        "table": "products",
        "text_cols": ["name", "description", "features"],
        "classification": "general",
        "level": 1
    }
]

# Ingest all
for source in sources:
    result = sqlite_agent.ingest_from_table(
        db_path=source["db"],
        table_name=source["table"],
        text_columns=source["text_cols"],
        classification=source["classification"],
        min_access_level=source["level"]
    )
    print(f"✓ {source['table']}: {result['documents_created']} docs")
```

### 4. Configuration via data_sources.yaml

In `config/data_sources.yaml`:

```yaml
sqlite:
  enabled: true
  ingestion_modes:
    table_based:
      enabled: true
      tables_to_ingest:
        - name: "knowledge_base"
          text_columns: ["title", "content"]
          metadata_columns: ["category", "tags"]
          chunk_strategy: "per_record"
    
    query_based:
      enabled: true
      queries:
        - name: "active_incidents"
          sql: "SELECT * FROM incidents WHERE status = 'open'"
          text_columns: ["title", "description"]
```

## Advanced Features

### 1. Document Chunking

Large text fields are automatically chunked:

```python
# Configuration
result = agent.ingest_from_sqlite(
    db_path="data/docs.db",
    table_name="documents",
    text_columns=["content"],
    chunk_strategy="per_record"  # Each record becomes 1+ chunks
)

# Internally uses token-aware chunking
# - Chunk size: 512 tokens
# - Overlap: 50 tokens
# - Respects sentence boundaries
```

### 2. Metadata Extraction

Metadata is automatically extracted from database records:

```python
# From record: {"id": 123, "title": "API Guide", "category": "engineering"}
# Generated metadata:
{
    "source": "sqlite://data/kb.db#knowledge_base",
    "classification": "engineering",
    "database": "kb.db",
    "ingestion_time": "2025-11-19T15:30:45.123456",
    "field_id": "123",
    "field_category": "engineering"
}
```

### 3. RBAC Integration

Access control is automatically applied:

```python
# Document ingested with min_access_level=2
# User with role level < 2 cannot access
result = orchestrator.process_query(
    query="API documentation",
    user_role="engineer",      # Level 3 - can see it
    access_level=3
)

result = orchestrator.process_query(
    query="API documentation",
    user_role="intern",        # Level 1 - cannot see it
    access_level=1
)
```

## Configuration Options

### Table-Based Ingestion

```python
ingest_from_table(
    db_path: str,              # Path to SQLite database
    table_name: str,           # Table to ingest
    text_columns: List[str],   # Columns with text content
    metadata_columns: Optional[List[str]] = None,
    classification: str = "general",
    min_access_level: int = 1,
    chunk_strategy: str = "per_record"  # "per_record" or "combined"
)
```

### Query-Based Ingestion

```python
ingest_from_sqlite_query(
    db_path: str,
    query: str,                # SQL query (must return rows)
    text_columns: List[str],   # Result columns with text
    metadata_columns: Optional[List[str]] = None,
    classification: str = "general",
    min_access_level: int = 1,
    query_name: str = "custom_query"
)
```

## Data Types Supported

### Text Columns
- String (TEXT)
- Large text (BLOB as TEXT)
- Concatenated fields

### Metadata Columns
- String (TEXT)
- Integer (INT)
- DateTime (auto-converted to string)
- Any value (converted to string)

## Filtering & Quality Control

The ingestion process includes:

1. **Null Handling**: Skips empty/null text fields
2. **Validation**: Ensures text_columns exist in table
3. **Error Handling**: Logs errors, continues with other records
4. **Filtering**: Can exclude tables matching patterns (e.g., `temp_*`)

## Performance Considerations

### Large Datasets

For tables with 100K+ records:

```python
# 1. Use query-based ingestion with LIMIT
result = agent.ingest_from_sqlite_query(
    db_path="data/large.db",
    query="SELECT * FROM logs LIMIT 10000",  # Batch 1
    text_columns=["message"],
    query_name="logs_batch_1"
)

# 2. Process in batches
for batch_num in range(10):
    offset = batch_num * 10000
    query = f"SELECT * FROM logs LIMIT 10000 OFFSET {offset}"
    # ... ingest
```

### Memory Optimization

- Embeddings stored in ChromaDB (not in memory)
- Chunking reduces individual record size
- Metadata in SQLite, not in memory

## Monitoring & Debugging

### Check Ingestion Statistics

```python
from src.subagents import SQLiteIngestionSubagent

subagent = SQLiteIngestionSubagent(db, vector_store)
result = subagent.ingest_from_table(...)

stats = subagent.get_statistics()
print(f"Records: {stats['records_processed']}")
print(f"Documents: {stats['documents_created']}")
print(f"Errors: {stats['errors']}")
print(f"Tokens: {stats['total_tokens']}")
```

### Verify Data in RAG

```python
from src.storage import RAGDatabase

db = RAGDatabase()

# Check ingested documents
docs = db.get_all_documents(limit=10)
for doc in docs:
    print(f"Doc: {doc['doc_id']}")
    print(f"  Source: {doc['source']}")
    print(f"  Classification: {doc['classification']}")
    print(f"  Size: {len(doc['content'])} chars")

# Check embeddings metadata
embedding_meta = db.get_embedding_metadata("sqlite_kb_123_0_20251119")
print(f"Model: {embedding_meta['embedding_model']}")
print(f"Dims: {embedding_meta['embedding_dimension']}")
print(f"Store: {embedding_meta['vector_store']}")
```

## Best Practices

### 1. Classification Strategy

```python
# Different classifications for different sources
engineering_docs = agent.ingest_from_sqlite(
    ...,
    classification="engineering",
    min_access_level=2  # Engineers and above
)

hr_docs = agent.ingest_from_sqlite(
    ...,
    classification="hr",
    min_access_level=1  # Everyone can see (if authorized by role)
)
```

### 2. Naming Conventions

```python
# Query names should be descriptive
query_names = {
    "active_tickets": "SELECT * FROM tickets WHERE status != 'closed'",
    "product_features": "SELECT * FROM products WHERE active = 1",
    "incident_history": "SELECT * FROM incidents WHERE severity >= 3"
}
```

### 3. Backup Before Ingesting

```python
# Backup database
import shutil
shutil.copy("data/rag_system.db", "data/rag_system.db.backup")

# Then ingest
result = agent.ingest_from_sqlite(...)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "no such table" | Verify table name exists in database |
| "no such column" | Check text_columns match actual columns |
| Out of memory | Use query-based with LIMIT, process in batches |
| Slow ingestion | Increase chunk_size, reduce metadata_columns |
| Duplicate documents | Use unique query_name, avoid re-ingesting same table |

---

**Version**: 1.0.0  
**Last Updated**: November 19, 2025
