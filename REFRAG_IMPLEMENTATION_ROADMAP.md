# REFRAG Implementation Roadmap
## Autonomous Agentic RAG with Self-Healing using DeepAgents

**Date:** November 19, 2025  
**Goal:** Complete system rewrite using LangChain DeepAgents for autonomous, self-healing RAG with RBAC

---

## 🎯 Core Architecture Principles

### 1. DeepAgents Framework Integration
- **All agents** use `deepagents.create_deep_agent()` from LangChain
- **Built-in capabilities**: `write_todos` (task planning), `task` (subagent spawning), filesystem tools
- **Custom tools**: RAG-specific operations (search, permission check, embed, etc.)
- **Autonomous operation**: Agents make decisions, spawn subagents, track progress independently

### 2. Clean Separation of Concerns
```
rag_agent/
├── core/
│   ├── abstractions/      # Base classes and interfaces
│   ├── services/          # LLM, Vector DB, SQLite services
│   └── config/            # Configuration loaders
├── agents/
│   ├── master.py          # MasterOrchestrator (DeepAgent)
│   ├── ingestion.py       # IngestionAgent (DeepAgent)
│   ├── retrieval.py       # RetrievalAgent (DeepAgent)
│   └── healing.py         # HealingAgent (DeepAgent)
├── tools/
│   ├── ingestion_tools.py # Tools for IngestionAgent
│   ├── retrieval_tools.py # Tools for RetrievalAgent
│   └── healing_tools.py   # Tools for HealingAgent
├── schemas/
│   ├── metadata.py        # Metadata table schemas
│   ├── rbac.py           # RBAC schema and mappings
│   └── tracking.py       # Agent operation tracking
└── config/
    ├── agent_config.yaml  # Agent configurations
    ├── llm_config.yaml    # LLM provider configs
    ├── rbac_config.yaml   # RBAC role mappings
    └── system_config.yaml # System settings
```

---

## 🗄️ Metadata Schema Design

### Critical Tables for REFRAG

#### 1. **agent_operations** - Core operation log
```sql
CREATE TABLE agent_operations (
    operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    operation_type TEXT NOT NULL, -- 'ingestion', 'retrieval', 'healing'
    query TEXT,
    retrieved_chunks TEXT, -- JSON array of chunk IDs
    reranker_scores TEXT, -- JSON array of scores
    final_response TEXT,
    user_feedback INTEGER, -- 1-5 rating
    response_time_ms INTEGER,
    token_count INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON for additional context
);
```

#### 2. **embedding_metadata** - Track embedding versions
```sql
CREATE TABLE embedding_metadata (
    embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    chunk_strategy TEXT, -- 'recursive', 'semantic', 'fixed'
    chunk_size INTEGER,
    overlap INTEGER,
    embedding_model TEXT, -- 'text-embedding-3-small', etc.
    embedding_version TEXT,
    quality_score REAL, -- Computed by HealingAgent
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
    reindex_count INTEGER DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);
```

#### 3. **role_mappings** - RBAC CDR encoding
```sql
CREATE TABLE role_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    cdr_code TEXT NOT NULL, -- '112' = Company1-HR-Associate
    company_name TEXT,
    department_name TEXT, -- 'HR', 'Engineering', 'Finance'
    role_name TEXT, -- 'Associate', 'Manager', 'Director'
    access_level INTEGER, -- 1-5 hierarchy
    UNIQUE(company_id, department_id, role_id)
);
```

#### 4. **document_permissions** - Document access tags
```sql
CREATE TABLE document_permissions (
    doc_id TEXT NOT NULL,
    cdr_code TEXT NOT NULL, -- Required role to access
    sensitivity TEXT, -- 'public', 'internal', 'confidential', 'legal'
    subject TEXT, -- 'engineering', 'hr', 'finance'
    assigned_by TEXT, -- 'llm_inference' or 'manual'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (doc_id, cdr_code)
);
```

#### 5. **user_roles** - User access mappings
```sql
CREATE TABLE user_roles (
    user_id TEXT NOT NULL,
    cdr_code TEXT NOT NULL,
    company_id INTEGER,
    department_id INTEGER,
    role_id INTEGER,
    granted_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, cdr_code)
);
```

#### 6. **query_heatmap** - For HealingAgent analysis
```sql
CREATE TABLE query_heatmap (
    heatmap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE, -- Hash of similar queries
    query_example TEXT,
    frequency INTEGER DEFAULT 1,
    avg_retrieval_accuracy REAL,
    avg_response_time_ms INTEGER,
    avg_user_feedback REAL,
    last_queried DATETIME DEFAULT CURRENT_TIMESTAMP,
    quality_category TEXT -- 'hot', 'warm', 'cold', 'poor'
);
```

#### 7. **llm_token_usage** - Cost tracking
```sql
CREATE TABLE llm_token_usage (
    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    operation_id INTEGER,
    provider TEXT, -- 'openai', 'anthropic', etc.
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operation_id) REFERENCES agent_operations(operation_id)
);
```

#### 8. **healing_operations** - Track REFRAG actions
```sql
CREATE TABLE healing_operations (
    healing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy TEXT NOT NULL, -- 'reindex_low_quality', 'add_synthetic_questions', etc.
    target_docs TEXT, -- JSON array of document IDs
    reason TEXT, -- Why healing was triggered
    actions_taken TEXT, -- JSON description of actions
    before_metrics TEXT, -- JSON snapshot before healing
    after_metrics TEXT, -- JSON snapshot after healing
    improvement_delta REAL, -- % improvement
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔐 RBAC Implementation Details

### CDR (Company-Department-Role) Encoding
**Format:** 3-digit code where:
- **C** (1st digit) = Company ID (1-9)
- **D** (2nd digit) = Department ID (1-9)
- **R** (3rd digit) = Role/Access Level (1-9)

**Example Mapping:**
```yaml
# config/rbac_config.yaml
role_mappings:
  "112": # Company 1, HR, Associate
    company: "Acme Corp"
    department: "HR"
    role: "Associate"
    access_level: 2
    can_access:
      - "public"
      - "internal_hr"
  
  "231": # Company 2, Finance, Manager
    company: "TechCo"
    department: "Finance"
    role: "Manager"
    access_level: 1
    can_access:
      - "public"
      - "internal_finance"
      - "confidential_finance"
  
  "123": # Company 1, Engineering, Director
    company: "Acme Corp"
    department: "Engineering"
    role: "Director"
    access_level: 3
    can_access:
      - "public"
      - "internal_engineering"
      - "confidential_engineering"
      - "technical_specs"
```

### RBAC Workflow

#### During Ingestion (RBACSubagent)
1. **LLM Context Extraction**
   ```python
   # Tool: classify_document_rbac
   prompt = """
   Analyze this document and extract:
   1. Subject area (engineering, hr, finance, legal, general)
   2. Sensitivity level (public, internal, confidential, legal)
   3. Required department access
   4. Minimum role level needed
   
   Document: {text}
   """
   ```

2. **Tag Generation**
   ```python
   # Map LLM output to CDR codes
   if subject == "hr" and sensitivity == "confidential":
       required_tags = ["112", "113", "114"]  # HR Associate, Senior, Manager
   ```

3. **Metadata Storage**
   ```python
   # Store in document_permissions table
   for tag in required_tags:
       db.insert_document_permission(doc_id, tag, sensitivity, subject)
   ```

#### During Retrieval (PermissionCheckerSubagent)
1. **User Role Lookup**
   ```python
   # Tool: get_user_permissions
   user_tags = db.get_user_roles(user_id)  # e.g., ['112', '123']
   ```

2. **Permission Filtering**
   ```python
   # Tool: filter_by_permissions
   allowed_chunks = []
   for chunk in retrieved_chunks:
       doc_tags = db.get_document_permissions(chunk.doc_id)
       if any(tag in user_tags for tag in doc_tags):
           allowed_chunks.append(chunk)
   ```

3. **Audit Logging**
   ```python
   # Log access attempts
   db.log_access_attempt(user_id, doc_id, granted=True/False)
   ```

---

## 🤖 Agent Implementation with DeepAgents

### 1. MasterOrchestrator (Top-Level Agent)

**Purpose:** Route tasks to specialized agents, coordinate multi-agent workflows

**Tools:**
- `route_to_ingestion` - Spawn IngestionAgent for new documents
- `route_to_retrieval` - Spawn RetrievalAgent for queries
- `route_to_healing` - Spawn HealingAgent for optimization
- `get_system_status` - Check overall system health
- `write_todos` - Plan complex multi-step operations

**Implementation:**
```python
# agents/master.py
from deepagents import create_deep_agent
from tools.orchestration_tools import (
    route_to_ingestion_tool,
    route_to_retrieval_tool,
    route_to_healing_tool,
    get_system_status_tool
)

class MasterOrchestrator:
    def __init__(self, config):
        self.config = config
        self.llm = self._create_llm()
        
        # Define orchestration tools
        self.tools = [
            route_to_ingestion_tool,
            route_to_retrieval_tool,
            route_to_healing_tool,
            get_system_status_tool
        ]
        
        # Create DeepAgent
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=self.llm
        )
    
    def process_request(self, request: str, context: dict):
        """Main entry point for all system requests"""
        return self.agent.invoke({
            "messages": [{
                "role": "user",
                "content": f"Request: {request}\nContext: {context}"
            }]
        })
```

---

### 2. IngestionAgent (Document Processing)

**Purpose:** Autonomous document ingestion with chunking, metadata extraction, RBAC classification, embedding

**Tools:**
- `chunk_document` - Split document using configured strategy
- `extract_metadata` - LLM-based keyword/summary extraction
- `classify_rbac` - LLM-based sensitivity/subject classification
- `generate_embeddings` - Create vector embeddings
- `store_in_vectordb` - Push to ChromaDB
- `update_metadata_db` - Store metadata in SQLite
- `write_todos` - Break down complex ingestion workflows
- `task` - Spawn specialized subagents for parallel processing

**Implementation:**
```python
# agents/ingestion.py
from deepagents import create_deep_agent
from tools.ingestion_tools import (
    chunk_document_tool,
    extract_metadata_tool,
    classify_rbac_tool,
    generate_embeddings_tool,
    store_in_vectordb_tool,
    update_metadata_db_tool
)

class IngestionAgent:
    def __init__(self, config, services):
        self.config = config
        self.llm_service = services['llm']
        self.vectordb_service = services['vectordb']
        self.db_service = services['db']
        
        self.tools = [
            chunk_document_tool,
            extract_metadata_tool,
            classify_rbac_tool,
            generate_embeddings_tool,
            store_in_vectordb_tool,
            update_metadata_db_tool
        ]
        
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_ingestion_prompt(),
            model=self.llm_service.get_model()
        )
    
    def ingest_document(self, document_path: str, metadata: dict):
        """
        Autonomous document ingestion
        Agent will:
        1. Use write_todos to plan ingestion steps
        2. Chunk document with appropriate strategy
        3. Spawn subagents for parallel metadata extraction
        4. Classify RBAC requirements
        5. Generate and store embeddings
        6. Update all metadata tables
        """
        return self.agent.invoke({
            "messages": [{
                "role": "user",
                "content": f"Ingest document: {document_path}\nMetadata: {metadata}"
            }]
        })
```

**Key Tool Example:**
```python
# tools/ingestion_tools.py
from langchain.tools import tool
from typing import Dict, List

@tool
def classify_rbac_tool(text: str, db_service) -> Dict[str, any]:
    """
    Use LLM to classify document for RBAC
    Returns: {
        'subject': 'engineering' | 'hr' | 'finance' | 'legal',
        'sensitivity': 'public' | 'internal' | 'confidential' | 'legal',
        'required_roles': ['112', '113'],
        'reasoning': 'Document contains salary information...'
    }
    """
    prompt = f"""
    Analyze this document for access control classification.
    
    Document: {text[:2000]}
    
    Provide:
    1. Subject area (engineering, hr, finance, legal, general)
    2. Sensitivity level (public, internal, confidential, legal)
    3. Minimum role required (associate, senior, manager, director)
    4. Department restriction (if any)
    5. Reasoning for classification
    
    Format as JSON.
    """
    
    # LLM call for classification
    result = llm_service.generate_json(prompt)
    
    # Map to CDR codes using rbac_config.yaml
    cdr_codes = map_to_cdr_codes(
        subject=result['subject'],
        sensitivity=result['sensitivity'],
        min_role=result['min_role'],
        department=result.get('department')
    )
    
    return {
        'subject': result['subject'],
        'sensitivity': result['sensitivity'],
        'required_roles': cdr_codes,
        'reasoning': result['reasoning']
    }
```

---

### 3. RetrievalAgent (Query Processing)

**Purpose:** Retrieve relevant documents with RBAC enforcement, reranking, answer synthesis

**Tools:**
- `permission_check` - Verify user access rights
- `vector_search` - Query ChromaDB for similar chunks
- `graph_expand` - Find related entities/documents
- `rerank_results` - Cross-encoder reranking
- `synthesize_answer` - Generate final response
- `log_operation` - Track query metadata
- `write_todos` - Plan complex multi-hop queries
- `task` - Spawn specialized retrieval subagents

**Implementation:**
```python
# agents/retrieval.py
from deepagents import create_deep_agent
from tools.retrieval_tools import (
    permission_check_tool,
    vector_search_tool,
    graph_expand_tool,
    rerank_results_tool,
    synthesize_answer_tool,
    log_operation_tool
)

class RetrievalAgent:
    def __init__(self, config, services):
        self.config = config
        self.services = services
        
        self.tools = [
            permission_check_tool,
            vector_search_tool,
            graph_expand_tool,
            rerank_results_tool,
            synthesize_answer_tool,
            log_operation_tool
        ]
        
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_retrieval_prompt(),
            model=services['llm'].get_model()
        )
    
    def process_query(self, query: str, user_id: str):
        """
        Autonomous query processing with RBAC
        Agent will:
        1. Use write_todos for complex queries
        2. Check user permissions
        3. Search vector database
        4. Filter results by RBAC
        5. Expand context if needed
        6. Rerank results
        7. Synthesize answer
        8. Log operation for healing analysis
        """
        return self.agent.invoke({
            "messages": [{
                "role": "user",
                "content": f"Query: {query}\nUser: {user_id}"
            }]
        })
```

**Key Tool Example:**
```python
# tools/retrieval_tools.py
@tool
def permission_check_tool(user_id: str, chunk_ids: List[str], db_service) -> List[str]:
    """
    Filter chunks based on user's RBAC permissions
    Returns: List of allowed chunk IDs
    """
    # Get user's CDR codes
    user_roles = db_service.query(
        "SELECT cdr_code FROM user_roles WHERE user_id = ?",
        (user_id,)
    )
    user_cdr_codes = [row['cdr_code'] for row in user_roles]
    
    allowed_chunks = []
    denied_count = 0
    
    for chunk_id in chunk_ids:
        # Get document ID from chunk
        doc_id = get_doc_id_from_chunk(chunk_id)
        
        # Get required permissions
        required_perms = db_service.query(
            "SELECT cdr_code FROM document_permissions WHERE doc_id = ?",
            (doc_id,)
        )
        required_codes = [row['cdr_code'] for row in required_perms]
        
        # Check if user has any matching role
        if any(code in user_cdr_codes for code in required_codes):
            allowed_chunks.append(chunk_id)
        else:
            denied_count += 1
            # Log access denial
            db_service.execute(
                "INSERT INTO access_audit (user_id, doc_id, granted, timestamp) VALUES (?, ?, 0, ?)",
                (user_id, doc_id, datetime.now())
            )
    
    print(f"[RBAC] Allowed: {len(allowed_chunks)}, Denied: {denied_count}")
    return allowed_chunks
```

---

### 4. HealingAgent (REFRAG - Self-Healing)

**Purpose:** Autonomous system optimization through heatmap analysis and targeted improvements

**Tools:**
- `analyze_heatmap` - Query operation logs for patterns
- `detect_low_quality` - Find poorly performing documents
- `generate_synthetic_questions` - Create training queries
- `reindex_documents` - Trigger re-chunking and re-embedding
- `optimize_chunk_strategy` - Test different chunking approaches
- `update_embeddings` - Re-embed with better models
- `measure_improvement` - Compare before/after metrics
- `write_todos` - Plan multi-phase healing operations
- `task` - Spawn optimization subagents

**Implementation:**
```python
# agents/healing.py
from deepagents import create_deep_agent
from tools.healing_tools import (
    analyze_heatmap_tool,
    detect_low_quality_tool,
    generate_synthetic_questions_tool,
    reindex_documents_tool,
    optimize_chunk_strategy_tool,
    update_embeddings_tool,
    measure_improvement_tool
)

class HealingAgent:
    def __init__(self, config, services):
        self.config = config
        self.services = services
        
        self.tools = [
            analyze_heatmap_tool,
            detect_low_quality_tool,
            generate_synthetic_questions_tool,
            reindex_documents_tool,
            optimize_chunk_strategy_tool,
            update_embeddings_tool,
            measure_improvement_tool
        ]
        
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_healing_prompt(),
            model=services['llm'].get_model()
        )
    
    def run_healing_cycle(self):
        """
        Autonomous system healing
        Agent will:
        1. Use write_todos to plan healing strategy
        2. Analyze query heatmap for cold/poor spots
        3. Detect low-quality embeddings
        4. Spawn subagents for different optimization strategies:
           - Reindexing subagent
           - Synthetic question generator
           - Chunk optimizer
           - Embedding updater
        5. Measure improvements
        6. Log healing operations
        """
        return self.agent.invoke({
            "messages": [{
                "role": "user",
                "content": "Run comprehensive healing cycle on RAG system"
            }]
        })
```

**Key Tool Examples:**
```python
# tools/healing_tools.py
@tool
def analyze_heatmap_tool(db_service) -> Dict[str, any]:
    """
    Analyze query patterns to find optimization opportunities
    Returns: {
        'cold_spots': [...],  # Low frequency queries
        'poor_quality': [...],  # Low accuracy/feedback
        'high_cost': [...],  # High token usage
        'recommendations': [...]
    }
    """
    # Query aggregated metrics
    heatmap = db_service.query("""
        SELECT 
            query_hash,
            query_example,
            frequency,
            avg_retrieval_accuracy,
            avg_user_feedback,
            avg_response_time_ms,
            CASE 
                WHEN frequency > 100 THEN 'hot'
                WHEN frequency > 50 THEN 'warm'
                WHEN avg_user_feedback < 3.0 THEN 'poor'
                ELSE 'cold'
            END as category
        FROM query_heatmap
        ORDER BY frequency DESC, avg_user_feedback ASC
    """)
    
    # Categorize findings
    cold_spots = [q for q in heatmap if q['category'] == 'cold']
    poor_quality = [q for q in heatmap if q['category'] == 'poor']
    
    # Find expensive operations
    high_cost = db_service.query("""
        SELECT agent_name, AVG(total_tokens) as avg_tokens, COUNT(*) as count
        FROM llm_token_usage
        GROUP BY agent_name
        HAVING avg_tokens > 5000
    """)
    
    return {
        'cold_spots': cold_spots[:10],
        'poor_quality': poor_quality[:10],
        'high_cost': high_cost,
        'total_queries': len(heatmap),
        'recommendations': generate_recommendations(cold_spots, poor_quality, high_cost)
    }

@tool
def reindex_documents_tool(doc_ids: List[str], new_strategy: str, services) -> Dict:
    """
    Re-chunk and re-embed documents with new strategy
    Returns: {
        'reindexed_count': int,
        'new_chunk_count': int,
        'quality_improvement': float
    }
    """
    results = {
        'reindexed_count': 0,
        'new_chunk_count': 0,
        'before_quality': [],
        'after_quality': []
    }
    
    for doc_id in doc_ids:
        # Get original quality score
        original = services['db'].query(
            "SELECT quality_score FROM embedding_metadata WHERE document_id = ? LIMIT 1",
            (doc_id,)
        )[0]
        results['before_quality'].append(original['quality_score'])
        
        # Delete old embeddings
        services['vectordb'].delete_by_document(doc_id)
        
        # Re-chunk with new strategy
        document = services['db'].get_document(doc_id)
        chunks = chunk_with_strategy(document['content'], new_strategy)
        
        # Re-embed
        embeddings = services['llm'].generate_embeddings(chunks)
        
        # Store new embeddings
        services['vectordb'].insert_embeddings(doc_id, chunks, embeddings)
        
        # Update metadata
        services['db'].execute("""
            UPDATE embedding_metadata 
            SET chunk_strategy = ?, 
                reindex_count = reindex_count + 1,
                last_modified = ?
            WHERE document_id = ?
        """, (new_strategy, datetime.now(), doc_id))
        
        results['reindexed_count'] += 1
        results['new_chunk_count'] += len(chunks)
    
    # Measure new quality (would need evaluation queries)
    results['quality_improvement'] = calculate_improvement(
        results['before_quality'], 
        results['after_quality']
    )
    
    return results

@tool
def generate_synthetic_questions_tool(doc_id: str, count: int, llm_service) -> List[str]:
    """
    Generate synthetic questions for a document to improve retrieval
    Uses LLM to create diverse, relevant queries
    """
    document = db_service.get_document(doc_id)
    
    prompt = f"""
    Generate {count} diverse, realistic questions that this document could answer.
    Make questions vary in:
    - Complexity (simple facts to multi-hop reasoning)
    - Specificity (broad overview to specific details)
    - Phrasing (different ways to ask the same thing)
    
    Document: {document['content'][:2000]}
    
    Return as JSON array of questions.
    """
    
    questions = llm_service.generate_json(prompt)['questions']
    
    # Store synthetic questions for testing
    for q in questions:
        db_service.execute("""
            INSERT INTO synthetic_queries (doc_id, question, generated_date)
            VALUES (?, ?, ?)
        """, (doc_id, q, datetime.now()))
    
    return questions
```

---

## 🔄 Complete REFRAG Workflow

### Scenario: System detects poor retrieval quality for engineering documents

1. **HealingAgent Autonomous Trigger** (scheduled run)
   ```
   HealingAgent.run_healing_cycle()
   └─> write_todos: "Analyze system, identify issues, implement fixes"
       ├─> Task 1: Analyze query heatmap
       ├─> Task 2: Detect low-quality documents
       ├─> Task 3: Generate optimization plan
       └─> Task 4: Execute improvements
   ```

2. **Heatmap Analysis**
   ```python
   heatmap = analyze_heatmap_tool()
   # Finds: "Engineering API docs have 2.1/5 avg feedback"
   ```

3. **Agent Decision via write_todos**
   ```
   Agent creates plan:
   1. Reindex engineering docs with semantic chunking
   2. Generate 50 synthetic questions
   3. Update embeddings with newer model
   4. Test improvements with synthetic queries
   ```

4. **Parallel Subagent Spawning via task tool**
   ```python
   # Agent spawns specialized subagents
   task("ReindexSubagent", doc_ids=engineering_docs, strategy="semantic")
   task("QuestionGenerator", doc_ids=engineering_docs, count=50)
   task("EmbeddingUpdater", doc_ids=engineering_docs, model="v2")
   ```

5. **Measurement & Logging**
   ```python
   improvements = measure_improvement_tool(doc_ids, before, after)
   # Logs to healing_operations table
   ```

6. **Continuous Learning**
   - Synthetic questions used to test new chunking
   - User feedback on new retrievals updates heatmap
   - Quality scores improve → system learns optimal chunking strategy

---

## 📋 Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Design new directory structure
- [ ] Create `core/services/` abstraction layer
  - [ ] `LLMService` (multi-provider)
  - [ ] `VectorDBService` (ChromaDB wrapper)
  - [ ] `SQLiteDB` (database abstraction)
- [ ] Implement configuration loaders
- [ ] Design metadata schemas (8 tables)
- [ ] Create RBAC config and mapping system

### Phase 2: Agent Implementation (Week 2-3)
- [ ] Implement MasterOrchestrator with DeepAgents
- [ ] Create IngestionAgent + tools
  - [ ] chunk_document_tool
  - [ ] extract_metadata_tool
  - [ ] classify_rbac_tool
  - [ ] generate_embeddings_tool
- [ ] Create RetrievalAgent + tools
  - [ ] permission_check_tool
  - [ ] vector_search_tool
  - [ ] graph_expand_tool
  - [ ] rerank_results_tool
  - [ ] synthesize_answer_tool

### Phase 3: REFRAG Implementation (Week 4)
- [ ] Implement HealingAgent + tools
  - [ ] analyze_heatmap_tool
  - [ ] detect_low_quality_tool
  - [ ] generate_synthetic_questions_tool
  - [ ] reindex_documents_tool
  - [ ] optimize_chunk_strategy_tool
- [ ] Create scheduled healing triggers
- [ ] Implement improvement measurement

### Phase 4: Testing & Refinement (Week 5)
- [ ] End-to-end ingestion tests
- [ ] RBAC enforcement tests
- [ ] Retrieval accuracy tests
- [ ] Healing cycle tests
- [ ] Multi-agent coordination tests
- [ ] Performance benchmarking

### Phase 5: Production Hardening (Week 6)
- [ ] Error handling and recovery
- [ ] Monitoring and alerting
- [ ] Cost optimization
- [ ] Documentation
- [ ] Deployment automation

---

## 🎓 Key Insights for DeepAgents Success

### 1. Let Agents Make Decisions
- Don't hardcode workflows - let `write_todos` plan steps
- Trust `task` tool for autonomous subagent spawning
- Provide tools, not instructions

### 2. Rich Tool Context
- Tools should return structured data (JSON)
- Include reasoning/confidence in tool outputs
- Log all tool calls for debugging

### 3. Iterative Improvement
- Start with basic tools, add sophistication over time
- Let HealingAgent discover optimization strategies
- User feedback drives continuous learning

### 4. RBAC as First-Class Concern
- Every operation checks permissions
- Audit all access attempts
- LLM-based classification with human override

### 5. Metadata is Intelligence
- Comprehensive logging enables self-healing
- Heatmap analysis reveals optimization opportunities
- Quality scores guide reindexing decisions

---

## 🚀 Quick Start Commands

```bash
# 1. Install dependencies
pip install deepagents langchain langchain-openai langchain-anthropic chromadb sentence-transformers

# 2. Configure providers
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"  # optional
export HUGGINGFACEHUB_API_TOKEN="hf_..."  # optional

# 3. Initialize system
python -m rag_agent.init_system

# 4. Ingest documents
python -m rag_agent.agents.ingestion --path data/documents/

# 5. Query system
python -m rag_agent.agents.retrieval --query "What is our API rate limit?" --user "user@company.com"

# 6. Run healing cycle
python -m rag_agent.agents.healing --cycle

# 7. Monitor system
python -m rag_agent.monitor --dashboard
```

---

## 📚 References

- **DeepAgents Documentation**: https://github.com/langchain-ai/deepagents
- **LangChain Tools**: https://python.langchain.com/docs/modules/agents/tools/
- **ChromaDB**: https://docs.trychroma.com/
- **RBAC Best Practices**: https://www.nist.gov/publications/role-based-access-control

---

## ✅ Success Metrics

After full implementation, your system should achieve:

- **Autonomous Ingestion**: No manual chunking/embedding configuration
- **RBAC Enforcement**: 100% access control coverage with audit trail
- **Self-Healing**: Weekly quality improvements via REFRAG cycles
- **Cost Efficiency**: Token usage reduced through optimization
- **User Satisfaction**: >4.0/5.0 average feedback on retrievals
- **System Intelligence**: Heatmap-driven continuous learning

---

**Next Step:** Review this roadmap, then we'll start with Phase 1 foundation implementation.
