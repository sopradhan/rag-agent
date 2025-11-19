# RBAC-Aware Retrieval and Healing Guide

## Overview

The RAG system now includes comprehensive RBAC-aware retrieval and healing capabilities, extending the intelligent ingestion system with sophisticated document search and embedding optimization.

### Key Components

1. **RBAC Retrieval Subagent** - Intelligent search with permission filtering
2. **Healing Subagent** - Embedding optimization and namespace management
3. **Tag Management** - Flexible document classification and filtering

---

## RBAC-Aware Retrieval System

### Architecture

The retrieval system consists of three integrated components:

#### 1. RBACFilteringSubagent

Enforces access control on search results based on user's RBAC context.

**Key Methods:**

- `get_user_rbac_context(user_id: int)` → Dict
  - Retrieves user's company, department, role, and access level
  - Calculates access_level from role grade (1-5 scale)

- `filter_by_rbac(doc_ids: List[str], user_rbac: Dict)` → List[str]
  - Filters documents by RBAC permissions
  - Checks minimum access level requirement
  - Validates departmental boundaries

- `get_document_rbac_info(doc_id: str)` → Dict
  - Returns document's classification and allowed departments
  - Shows minimum access level required

**Example Usage:**

```python
from src.storage.sqlite_storage import RAGDatabase
from src.subagents.rbac_retrieval_subagent import RBACFilteringSubagent

rag_db = RAGDatabase("data/rag_system.db")
rbac_filter = RBACFilteringSubagent(rag_db)

# Get user's RBAC context
user_rbac = rbac_filter.get_user_rbac_context(user_id=1)
print(f"User: {user_rbac['role_name']}, Department: {user_rbac['department_name']}")
print(f"Access Level: {user_rbac['access_level']}")

# Filter documents
doc_ids = ["doc_1", "doc_2", "doc_3"]
accessible = rbac_filter.filter_by_rbac(doc_ids, user_rbac)
print(f"User can access: {accessible}")
```

#### 2. TagRetrievalSubagent

Manages document tags for flexible classification and filtering.

**Key Methods:**

- `get_document_tags(doc_id: str)` → List[str]
  - Returns all tags for a document

- `search_by_tags(tags: List[str], match_all: bool)` → List[str]
  - Search documents by tags
  - `match_all=True`: Document must have ALL tags
  - `match_all=False`: Document must have ANY tag

- `get_tag_suggestions(search_query: str, limit: int)` → List[Dict]
  - Returns frequently used tags in matching documents
  - Useful for search autocomplete

- `add_tag_to_document(doc_id: str, tag: str)`
  - Add a tag to a document (post-ingestion)

- `remove_tag_from_document(doc_id: str, tag: str)`
  - Remove a tag from a document

**Example Usage:**

```python
from src.subagents.rbac_retrieval_subagent import TagRetrievalSubagent

tag_retriever = TagRetrievalSubagent(rag_db)

# Get tags for a document
tags = tag_retriever.get_document_tags("doc_1")
print(f"Tags: {tags}")  # e.g., ['policy', 'important', 'security']

# Search documents with specific tags
policy_docs = tag_retriever.search_by_tags(["policy"], match_all=False)
print(f"Found {len(policy_docs)} policy documents")

# Search documents with multiple tags (must have all)
critical_docs = tag_retriever.search_by_tags(
    ["important", "security"],
    match_all=True
)

# Get tag suggestions
suggestions = tag_retriever.get_tag_suggestions("security", limit=5)
for suggestion in suggestions:
    print(f"{suggestion['tag']}: {suggestion['frequency']} documents")
```

#### 3. RBACSearchSubagent

Orchestrates complete RBAC-filtered search with tag association.

**Key Methods:**

- `search_with_rbac_and_tags(query, user_id, top_k, tags_filter)` → List[Dict]
  - Execute complete RBAC-aware search
  - Returns documents with RBAC and tag information

**Search Pipeline:**

1. Get user's RBAC context
2. Search in ChromaDB by similarity
3. Apply RBAC filtering
4. Apply tag filtering (optional)
5. Enrich results with metadata
6. Return top-k documents

**Result Format:**

```python
{
    "doc_id": "unique_doc_id",
    "content": "document content...",
    "source": "source_file.txt",
    "classification": "technical",
    "similarity_score": 0.95,
    "tags": ["important", "policy"],
    "min_access_level": 2,
    "user_access_level": 4
}
```

**Example Usage:**

```python
from src.storage.vector_store import ChromaVectorStore
from src.subagents.rbac_retrieval_subagent import RBACSearchSubagent

rag_db = RAGDatabase("data/rag_system.db")
vector_store = ChromaVectorStore("data/chroma_db")
search_agent = RBACSearchSubagent(rag_db, vector_store)

# Basic search with RBAC filtering
results = search_agent.search_with_rbac_and_tags(
    query="database performance optimization",
    user_id=1,
    top_k=5
)

for result in results:
    print(f"Source: {result['source']}")
    print(f"Relevance: {result['similarity_score']:.3f}")
    print(f"Tags: {result['tags']}")
    print(f"Can access: {result['user_access_level']} >= {result['min_access_level']}")
    print()

# Search with tag filtering
results = search_agent.search_with_rbac_and_tags(
    query="policies",
    user_id=1,
    top_k=5,
    tags_filter=["policy", "important"]
)
```

### Access Level System

Access levels are determined by role grade:

| Grade | Level | Permissions |
|-------|-------|------------|
| intern | 1 | Basic documents |
| junior | 2 | Standard documents |
| senior | 3 | Advanced documents |
| lead | 4 | Sensitive documents |
| manager | 4 | Sensitive documents |
| director | 5 | Confidential documents |
| executive | 5 | Confidential documents |

---

## RBAC-Aware Healing System

### Architecture

The healing system optimizes embeddings and namespace organization through three components:

#### 1. EmbeddingShuffler

Rebalances documents across namespaces based on classification and access patterns.

**Key Methods:**

- `get_namespace_statistics()` → Dict
  - Returns document count and access level statistics per namespace
  - 7 namespaces: engineering, hr, security, finance, general, operations, product

- `analyze_access_patterns()` → Dict
  - Shows which departments access which namespaces
  - Identifies cross-namespace access patterns

- `calculate_namespace_affinity(doc_id: str)` → str
  - Determines optimal namespace based on classification
  - Checks if document is in right namespace

- `move_document_to_namespace(doc_id: str, target_namespace: str)`
  - Moves document to different namespace
  - Logs operation to healing_operations table

- `rebalance_namespaces()` → Dict
  - Automatically rebalances all documents to optimal namespaces
  - Returns count and list of moved documents

**Example Usage:**

```python
from src.subagents.rbac_healing_subagent import EmbeddingShuffler

shuffler = EmbeddingShuffler(rag_db, vector_store)

# Get current namespace distribution
stats = shuffler.get_namespace_statistics()
for ns, info in stats.items():
    print(f"{ns}: {info['doc_count']} docs, avg_level={info['avg_access_level']:.1f}")

# Analyze access patterns
patterns = shuffler.analyze_access_patterns()
for ns, depts in patterns.items():
    print(f"{ns}: accessed by {len(depts)} departments")

# Rebalance namespaces
result = shuffler.rebalance_namespaces()
print(f"Rebalanced {result['rebalance_count']} documents")
for move in result['moved_documents'][:5]:
    print(f"  {move['doc_id']}: {move['from']} → {move['to']}")
```

#### 2. EmbeddingRefragmenter

Optimizes chunk sizes and distribution for better retrieval.

**Key Methods:**

- `analyze_chunk_distribution()` → Dict
  - Returns statistics on chunk sizes
  - Calculates average, min, max, and standard deviation

- `identify_large_chunks(threshold=5000)` → List[Dict]
  - Returns chunks larger than threshold
  - Default: 5000 bytes

- `identify_small_chunks(threshold=200)` → List[Dict]
  - Returns chunks smaller than threshold
  - Default: 200 bytes

- `recommend_refragmentation()` → Dict
  - Analyzes chunk distribution and makes recommendations
  - Suggests whether to split or merge chunks

- `split_document(doc_id: str, chunk_size=2000)` → List[str]
  - Splits large document into smaller chunks
  - Maintains semantic coherence by splitting on sentences
  - Returns new doc_ids created

**Example Usage:**

```python
from src.subagents.rbac_healing_subagent import EmbeddingRefragmenter

refragmenter = EmbeddingRefragmenter(rag_db)

# Analyze current distribution
stats = refragmenter.analyze_chunk_distribution()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Avg size: {stats['avg_chunk_size']:.0f} bytes")
print(f"Range: {stats['min_chunk_size']} - {stats['max_chunk_size']} bytes")

# Find problematic chunks
large = refragmenter.identify_large_chunks(threshold=5000)
small = refragmenter.identify_small_chunks(threshold=200)
print(f"Large chunks: {len(large)}, Small chunks: {len(small)}")

# Get recommendations
recommendations = refragmenter.recommend_refragmentation()
if recommendations['recommendation']['should_split']:
    print("System recommends splitting large chunks")
    print(f"Target size: {recommendations['recommendation']['target_avg_size']}")

# Split a large document
new_ids = refragmenter.split_document("doc_1", chunk_size=2000)
print(f"Split into {len(new_ids)} chunks: {new_ids}")
```

#### 3. RBACHealingSubagent

Master healing orchestrator running comprehensive optimization.

**Key Methods:**

- `run_full_healing()` → Dict
  - Runs complete healing pipeline:
    1. Namespace analysis
    2. Namespace rebalancing
    3. Access pattern analysis
    4. Chunk distribution analysis
    5. Refragmentation recommendations

- `run_namespace_optimization()` → Dict
  - Runs only namespace optimization

- `run_chunk_optimization()` → Dict
  - Runs only chunk optimization

- `apply_refragmentation(auto_split_threshold=5000)` → Dict
  - Automatically splits large chunks above threshold

- `get_healing_status()` → Dict
  - Returns current system health status
  - Shows operations performed and optimization metrics

**Example Usage:**

```python
from src.subagents.rbac_healing_subagent import RBACHealingSubagent

healing_agent = RBACHealingSubagent(rag_db, vector_store)

# Get current system health
status = healing_agent.get_healing_status()
print(f"System health: {status['system_health']}")
print(f"Operations performed: {status['healing_operations']}")

# Run namespace optimization
ns_result = healing_agent.run_namespace_optimization()
print(f"Rebalanced {ns_result['rebalance_results']['rebalance_count']} documents")

# Run chunk optimization
chunk_result = healing_agent.run_chunk_optimization()
print(f"Large chunks: {len(chunk_result['large_chunks'])}")
print(f"Small chunks: {len(chunk_result['small_chunks'])}")

# Apply refragmentation
refrag_result = healing_agent.apply_refragmentation(auto_split_threshold=5000)
print(f"Split {len(refrag_result['split_operations'])} documents")

# Run full healing pipeline
full_result = healing_agent.run_full_healing()
print(json.dumps(full_result, indent=2, default=str))
```

### Namespace Categories

Documents are organized into 7 namespaces:

| Namespace | Purpose | Classification |
|-----------|---------|-----------------|
| engineering_ns | Technical documentation | technical, api, architecture |
| hr_ns | Human resources | hr, people |
| security_ns | Security & compliance | security, compliance |
| finance_ns | Financial information | finance, budget |
| operations_ns | Procedures & operations | operations, procedure |
| product_ns | Product information | product, feature |
| general_ns | General content | general, incident |

---

## Integration Example

### Complete Workflow

```python
from src.storage.sqlite_storage import RAGDatabase
from src.storage.vector_store import ChromaVectorStore
from src.subagents.rbac_ingestion_subagent import RBACIntelligentIngestionSubagent
from src.subagents.rbac_retrieval_subagent import RBACSearchSubagent
from src.subagents.rbac_healing_subagent import RBACHealingSubagent

# Initialize components
rag_db = RAGDatabase("data/rag_system.db")
vector_store = ChromaVectorStore("data/chroma_db")

# 1. Ingest with RBAC awareness
ingestion = RBACIntelligentIngestionSubagent(rag_db, vector_store)
ingest_result = ingestion.ingest_with_rbac(
    document_path="documents/architecture.txt",
    doc_type="technical documentation"
)

# 2. Search with RBAC and tags
search_agent = RBACSearchSubagent(rag_db, vector_store)
results = search_agent.search_with_rbac_and_tags(
    query="microservices architecture",
    user_id=1,
    top_k=5,
    tags_filter=["important"]
)

# 3. Optimize with healing
healing_agent = RBACHealingSubagent(rag_db, vector_store)
healing_result = healing_agent.run_full_healing()

# 4. Check system health
status = healing_agent.get_healing_status()
```

---

## Database Schema Extensions

### Key Tables Used

**documents** (extended)
- `doc_id` - Unique identifier
- `content` - Document content
- `namespace` - One of 7 namespaces
- `classification` - Content classification
- `min_access_level` - Required access level

**document_rbac** (RBAC enforcement)
- `doc_id` - Document ID
- `department_id` - Authorized department
- Links documents to authorized departments

**metadata** (Tag storage)
- `doc_id` - Document ID
- `key` - "tag" for tags
- `value` - Tag value

**healing_operations** (Healing audit trail)
- `operation_type` - "namespace_move", "document_split"
- `doc_id` - Document involved
- `operation_details` - Details of operation
- `status` - "completed" or "pending"

---

## Performance Considerations

### Retrieval Performance

- RBAC filtering happens after similarity search for efficiency
- Tag filtering is applied to reduce result set
- Indexed queries on department_id and doc_id

### Healing Performance

- Namespace rebalancing scans all documents (can be large)
- Recommend running during off-peak hours
- Refragmentation is incremental (can be targeted or bulk)

### Optimization Tips

1. **Keep access levels balanced** - Don't overuse high access levels
2. **Use tags strategically** - Helps with filtering and search
3. **Run healing regularly** - Maintain optimal distribution
4. **Monitor chunk sizes** - Split very large documents
5. **Archive old documents** - Remove from namespaces periodically

---

## Troubleshooting

### Issue: User getting no results

**Check:**
1. User's access level vs document's min_access_level
2. User's department in document_rbac table
3. Document exists in ChromaDB

### Issue: Slow searches

**Check:**
1. Number of documents in namespaces
2. Chunk sizes (optimize with refragmentation)
3. RBAC filtering is working (not returning duplicates)

### Issue: Unbalanced namespaces

**Solution:**
```python
healing_agent.run_namespace_optimization()
```

### Issue: Large chunks affecting retrieval

**Solution:**
```python
healing_agent.apply_refragmentation(auto_split_threshold=5000)
```

---

## See Also

- [INSTALLATION.md](INSTALLATION.md) - System setup
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [SQLITE_INTEGRATION.md](SQLITE_INTEGRATION.md) - SQLite ingestion
- [examples/rbac_retrieval_example.py](examples/rbac_retrieval_example.py) - Retrieval examples
- [examples/rbac_healing_example.py](examples/rbac_healing_example.py) - Healing examples
