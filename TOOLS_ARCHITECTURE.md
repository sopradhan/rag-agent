# Tools Architecture: Why Separate Tool Files?

## The Problem You're Asking About

**Question**: "Why do we need separate tool files (retrieval_tools.py, ingestion_tools.py, etc.) when agents already have tools inside them? And why do DB calls happen everywhere?"

**Answer**: It's about **reusability, maintainability, and separation of concerns**. Let me show you the difference:

---

## Current Architecture: Two Approaches

### ❌ APPROACH 1: Tools ONLY Inside Agents (What IngestionAgent Does Now)

```python
# agents/ingestion_agent.py - ALL logic embedded
class IngestionAgent:
    def _create_tools(self):
        @tool
        def ingest_document_from_file(doc_id: str, file_path: str) -> str:
            # Step 1: Direct chunking logic
            splitter = RecursiveCharacterTextSplitter(...)
            chunks = splitter.split_text(document_text)
            
            # Step 2: Direct LLM call for metadata
            metadata = llm_service.generate_json(metadata_prompt)
            
            # Step 3: Direct RBAC classification
            subject = llm_service.generate_json(subject_prompt)
            
            # Step 4: Direct embedding generation
            embeddings = llm_service.generate_embeddings(texts)
            
            # Step 5: Direct DB calls
            vectordb_service.insert_embeddings(...)
            db_service.execute("INSERT INTO embedding_metadata...")
            db_service.assign_document_permission(...)
            
            return result
```

**Problems**:
- ❌ Logic is TIGHTLY COUPLED to IngestionAgent
- ❌ Can't reuse chunking in HealingAgent (reindexing needs same logic)
- ❌ Can't reuse RBAC classification if you add another ingestion method
- ❌ Hard to test individual steps
- ❌ If you want to use chunking tool from orchestrator, you can't
- ❌ DB calls scattered throughout tool code

---

### ✅ APPROACH 2: Tools as SEPARATE REUSABLE MODULES (What We're Trying to Do)

```python
# tools/ingestion_tools.py - Reusable, standalone functions
@tool
def chunk_document_tool(text: str, strategy: str = "recursive", 
                       chunk_size: int = 500, overlap: int = 50) -> str:
    """Chunking is ISOLATED - can be used by ANY agent"""
    splitter = RecursiveCharacterTextSplitter(...)
    chunks = splitter.split_text(text)
    return json.dumps({"success": True, "chunks": chunks})

@tool
def classify_rbac_tool(text: str, llm_service, rbac_config: dict) -> str:
    """RBAC classification is ISOLATED - reusable"""
    subject_result = llm_service.generate_json(subject_prompt)
    sensitivity_result = llm_service.generate_json(sensitivity_prompt)
    required_roles = _map_to_cdr_codes(subject, sensitivity, rbac_config)
    return json.dumps({"success": True, "classification": {...}})

@tool
def generate_embeddings_tool(chunks: str, llm_service) -> str:
    """Embedding generation is ISOLATED - reusable"""
    embeddings = llm_service.generate_embeddings(texts)
    return json.dumps({"success": True, "embeddings": embeddings})

# agents/ingestion_agent.py - Uses tools
class IngestionAgent:
    def _create_tools(self):
        from tools.ingestion_tools import (
            chunk_document_tool,
            classify_rbac_tool,
            generate_embeddings_tool
        )
        
        # Agent CALLS these as tools, doesn't implement them
        return [
            Tool(name="chunk_document", func=chunk_document_tool),
            Tool(name="classify_rbac", func=classify_rbac_tool),
            Tool(name="generate_embeddings", func=generate_embeddings_tool),
        ]

# agents/healing_agent.py - REUSES same tools!
class HealingAgent:
    def _create_tools(self):
        from tools.ingestion_tools import (
            chunk_document_tool,  # <-- REUSE for reindexing
            generate_embeddings_tool  # <-- REUSE for reindexing
        )
        from tools.healing_tools import (
            analyze_heatmap_tool,
            detect_low_quality_tool,
            reindex_documents_tool
        )
        
        return [
            Tool(name="chunk_document", func=chunk_document_tool),
            Tool(name="reindex", func=reindex_documents_tool),
        ]
```

**Benefits**:
- ✅ Tools are REUSABLE across agents
- ✅ Logic is TESTABLE independently
- ✅ Easy to SWAP implementations (e.g., different embeddings model)
- ✅ DB calls centralized in tool functions
- ✅ Can add new agents that reuse same tools
- ✅ Clear separation: Tools = business logic, Agents = orchestration

---

## Current State: Mixed Implementation

### What IngestionAgent Does (Embedded Logic)
```
IngestionAgent
├── Tool defined inside _create_tools()
│   ├── Chunking logic (embedded)
│   ├── Metadata extraction (embedded)
│   ├── RBAC classification (embedded)
│   ├── Embedding generation (embedded)
│   └── DB calls (embedded)
└── Direct DB operations in __init__
```

### What RetrievalAgent Does (Uses External Tools)
```
RetrievalAgent
├── Imports from tools/ directory
│   ├── permission_check_tool from tools/retrieval_tools.py
│   ├── vector_search_tool from tools/retrieval_tools.py
│   ├── rerank_results_tool from tools/retrieval_tools.py
│   ├── synthesize_answer_tool from tools/retrieval_tools.py
│   └── get_system_status_tool from tools/common_tools.py
├── Wraps them with service bindings
└── Passes to DeepAgent as tools
```

---

## DB Calls: Why Everywhere?

Each agent needs direct DB access because:

1. **IngestionAgent** needs DB calls to:
   - Store document metadata
   - Assign RBAC permissions
   - Track embedding metadata
   - Insert into vector DB

2. **RetrievalAgent** needs DB calls to:
   - Get user roles (for RBAC checking)
   - Get document permissions
   - Log queries
   - Update heatmap

3. **HealingAgent** needs DB calls to:
   - Query heatmap for analysis
   - Find low-quality embeddings
   - Store synthetic questions
   - Track healing operations

4. **Common tools** need DB calls to:
   - Get system status metrics
   - Execute user queries

**The solution is NOT to remove DB calls** - it's to make them **consistent and organized** through tool functions rather than scattered everywhere.

---

## Recommended Refactoring Path

### Current State (Mixed)
```
❌ IngestionAgent: Tools + embedded logic + direct DB calls
✅ RetrievalAgent: Uses external tools + proper tool structure
✅ HealingAgent: Uses external tools + proper tool structure
✅ MasterOrchestrator: Uses external tools
✅ Tools/*.py: Reusable tool functions with DB access
```

### What Should Happen

**Option A: Extract IngestionAgent's embedded logic into tools/**
```python
# Move from ingestion_agent.py to ingestion_tools.py
@tool
def ingest_document_from_file(doc_id, file_path, llm_service, vectordb_service, db_service):
    # Do all 5 steps here
    # Return result
    
# Then IngestionAgent just orchestrates:
class IngestionAgent:
    def _create_tools(self):
        from tools.ingestion_tools import ingest_document_from_file
        return [Tool(name="ingest", func=ingest_document_from_file)]
```

**Option B: Keep 5-step flow in agent (current), but organize better**
```python
# Current approach - tools defined inside agent
# This is OK for single-use logic that won't be reused
# But reusable logic (chunking, RBAC) should go to tools/
```

---

## Summary: When to Use Separate Tool Files vs Embedded Tools

### Use **SEPARATE tool files** (tools/*.py) for:
✅ Reusable logic (chunking, RBAC classification, embedding generation)
✅ Logic used by multiple agents
✅ Logic that might be tested independently
✅ Complex business logic (vector search, answer synthesis)
✅ Healing/optimization operations

### Use **EMBEDDED tools** (inside agent) for:
✅ Agent-specific workflows (e.g., IngestionAgent's 5-step flow)
✅ Simple wrapper logic
✅ Orchestration-level tools
✅ Single-use scenarios

### DB Calls:
- ✅ Belong inside tool functions (not agent logic)
- ✅ Each tool that needs DB access receives `db_service` as parameter
- ✅ Centralized in tools/*.py files for maintainability
- ✅ Logging and operations tracked consistently

---

## Current Tools Breakdown

| Tool File | Purpose | Reusable? | Used By |
|-----------|---------|-----------|---------|
| common_tools.py | System status, DB queries | Yes - ALL agents | RetrievalAgent, HealingAgent, MasterOrchestrator |
| retrieval_tools.py | Vector search, RBAC check, synthesis | Yes - retrievers | RetrievalAgent, could be used by others |
| ingestion_tools.py | Chunking, metadata, RBAC classification, embeddings | Yes - ingestion + healing | IngestionAgent, HealingAgent (reindexing) |
| healing_tools.py | Heatmap analysis, quality detection, reindexing | Yes - healing + monitoring | HealingAgent, MasterOrchestrator |

All have direct DB calls because they execute actual operations, not just orchestration.

