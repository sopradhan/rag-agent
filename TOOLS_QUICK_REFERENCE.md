# Quick Reference: Tools Architecture

## 🔷 Simple Comparison

### ❌ BAD: Everything embedded in agent
```
IngestionAgent
    └── _create_tools()
        └── ingest_document_from_file (tool)
            ├── Chunking code
            ├── Metadata code  
            ├── RBAC code
            ├── Embedding code
            └── DB calls
            
Problem: Can't reuse chunking in HealingAgent!
         Can't test chunking independently!
```

### ✅ GOOD: Reusable tools in separate files
```
tools/ingestion_tools.py
├── chunk_document_tool()         ← Reusable
├── extract_metadata_tool()       ← Reusable
├── classify_rbac_tool()          ← Reusable
├── generate_embeddings_tool()    ← Reusable
└── store_embeddings_tool()       ← Reusable

IngestionAgent
└── _create_tools()
    ├── chunk_document_tool
    ├── classify_rbac_tool
    ├── generate_embeddings_tool
    └── store_embeddings_tool

HealingAgent  (REUSES same tools!)
└── _create_tools()
    ├── chunk_document_tool       ← REUSED for reindexing
    ├── generate_embeddings_tool  ← REUSED for reindexing
    └── reindex_documents_tool

✅ Chunking code exists in ONE place
✅ Both agents can use it
✅ Easy to test
✅ Easy to maintain
```

---

## 🔷 Real World Example

### Current IngestionAgent (EMBEDDED - not ideal)
```python
@tool
def ingest_document_from_file(doc_id, file_path):
    # Line 70: Direct chunking
    chunks = splitter.split_text(document_text)
    
    # Line 90: Direct metadata LLM call
    metadata = llm_service.generate_json(metadata_prompt)
    
    # Line 120: Direct RBAC classification
    subject = llm_service.generate_json(subject_prompt)
    
    # Line 150: Direct embedding generation
    embeddings = llm_service.generate_embeddings(texts)
    
    # Line 180: Direct DB calls
    vectordb_service.insert_embeddings(ids, embeddings, ...)
    db_service.assign_document_permission(...)
    
    return result
```

**Problem**: If HealingAgent needs to reindex with same chunking logic...
```python
# It either:
# 1. Copy-pastes the chunking code (DUPLICATION)
# 2. Calls IngestionAgent.ingest_document_from_file (WRONG - too many steps)
# 3. Has its own chunking logic (DUPLICATION)
```

### Better Approach (TOOLS-BASED)
```python
# tools/ingestion_tools.py - Write ONCE
@tool
def chunk_document_tool(text, strategy="recursive", chunk_size=500, overlap=50):
    splitter = RecursiveCharacterTextSplitter(...)
    chunks = splitter.split_text(text)
    return json.dumps({"chunks": chunks})

# IngestionAgent uses it
class IngestionAgent:
    def _create_tools(self):
        from tools.ingestion_tools import chunk_document_tool
        return [Tool(name="chunk_document", func=chunk_document_tool)]

# HealingAgent REUSES it
class HealingAgent:
    def _create_tools(self):
        from tools.ingestion_tools import chunk_document_tool  # REUSE!
        return [Tool(name="chunk_document", func=chunk_document_tool)]
```

✅ Chunking code in ONE place
✅ Both agents call the same function
✅ No duplication
✅ Easy to improve chunking for everyone

---

## 🔷 DB Calls: Why Everywhere?

**Short Answer**: Because each tool needs to actually DO something with the database.

```
Tools with DB operations:
├── tools/ingestion_tools.py
│   ├── chunk_document_tool (no DB)
│   ├── extract_metadata_tool (no DB)
│   ├── classify_rbac_tool (no DB)
│   ├── generate_embeddings_tool (no DB)
│   └── store_embeddings_tool (YES - writes to ChromaDB + SQLite)
│
├── tools/retrieval_tools.py
│   ├── vector_search_tool (YES - reads from ChromaDB)
│   ├── permission_check_tool (YES - reads user/doc permissions from SQLite)
│   ├── rerank_results_tool (no DB)
│   └── synthesize_answer_tool (YES - might log to SQLite)
│
├── tools/healing_tools.py
│   ├── analyze_heatmap_tool (YES - reads from SQLite)
│   ├── detect_low_quality_tool (YES - reads from SQLite)
│   ├── generate_synthetic_questions_tool (YES - writes to SQLite)
│   └── reindex_documents_tool (YES - writes to ChromaDB + SQLite)
│
└── tools/common_tools.py
    ├── get_system_status_tool (YES - reads from SQLite)
    └── query_database_tool (YES - reads from SQLite)
```

✅ Tools that **DO WORK** (store, retrieve, analyze) use DB
✅ Tools that **TRANSFORM DATA** (chunk, rerank) don't need DB
✅ Each tool receives services as parameters: `def tool(param, llm_service, db_service, vectordb_service)`

---

## 🔷 Current State vs Ideal State

### Current IngestionAgent (Mixed Approach)
```
✅ Embedded 5-step workflow (OK for this specific agent)
❌ Uses DB calls directly without tool isolation
❌ Chunking logic not separated
❌ RBAC classification not separated
❌ Can't be reused by HealingAgent
```

### Ideal State (Fully Tool-Based)
```
✅ Chunking → tools/ingestion_tools.py
✅ Metadata extraction → tools/ingestion_tools.py
✅ RBAC classification → tools/ingestion_tools.py
✅ Embedding generation → tools/ingestion_tools.py
✅ Storage → tools/ingestion_tools.py
✅ All reusable by other agents
✅ All have consistent DB call patterns
✅ All testable independently
```

---

## 🔷 What We Already Have Working

| Agent | Approach | Status |
|-------|----------|--------|
| **RetrievalAgent** | ✅ Uses external tools (retrieval_tools.py) | Working correctly |
| **HealingAgent** | ✅ Uses external tools (healing_tools.py) | Working correctly |
| **MasterOrchestrator** | ✅ Uses external tools (common_tools.py) | Working correctly |
| **IngestionAgent** | ⚠️ Embedded logic + no separate tools | Works but not reusable |

---

## 🔷 Recommended Next Step (Optional Refactoring)

### Extract IngestionAgent's embedded logic to tools/

**Before** (Current):
```python
# agents/ingestion_agent.py - 393 lines, ALL logic embedded
@tool
def ingest_document_from_file(doc_id, file_path):
    # 250+ lines of chunking, metadata, RBAC, embedding, storage
```

**After** (Better):
```python
# tools/ingestion_tools.py - Already has most logic
# Just add the missing pieces:

@tool
def ingest_document_complete(doc_id, file_path, llm_service, vectordb_service, db_service):
    """Complete 5-step ingestion workflow"""
    # Orchestrate the other tools

# agents/ingestion_agent.py - Much simpler
@tool
def ingest_wrapper(doc_id, file_path):
    return ingest_document_complete(doc_id, file_path, ...)
```

Benefits:
- ✅ HealingAgent can reuse individual steps for reindexing
- ✅ RetrievalAgent can use RBAC classification for live classification
- ✅ Each step independently testable
- ✅ Less code duplication

---

## 🔷 Summary Table

| Concept | Purpose | Example |
|---------|---------|---------|
| **Tool Function** | Reusable, testable operation | `chunk_document_tool()` |
| **Tool Wrapper** | Bind services + create Tool object | `Tool(name="chunk", func=wrapper)` |
| **Agent Tool** | Register with agent for LLM access | `self.tools = [Tool(...)]` |
| **DB Call** | Actual database operation | `db_service.insert_embedding_metadata()` |
| **Service** | Dependency injection | `llm_service`, `vectordb_service`, `db_service` |

All tied together:
```
Tool Function (with DB calls) 
    ↓
Service Binding (inject db_service)
    ↓
Tool Wrapper (create Tool object)
    ↓
Agent Tools (register with agent)
    ↓
DeepAgent (calls tool when LLM decides to use it)
    ↓
Tool Executes (DB call happens here)
    ↓
Result back to LLM
```

