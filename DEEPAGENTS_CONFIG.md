# REFRAG System - DeepAgents Configuration

## ✅ Configuration Complete

### HuggingFace API Key
- **Key**: Get from https://huggingface.co/settings/tokens
- **Location**: Set in `.env` file as `HUGGINGFACE_API_KEY`
- **Usage**: Available for HuggingFace provider (currently disabled, using Ollama)

### LLM Providers
- **Default**: Ollama (gemma3:4b)
- **Embedding**: Ollama (nomic-embed-text)
- **Available**: OpenAI, Anthropic, HuggingFace, Ollama

## ✅ DeepAgents Library Integration

All agents use the **official LangChain DeepAgents library** via `create_deep_agent()`.

### Built-in Tools (Automatic)

These tools are **automatically included** by DeepAgents and don't need to be added to custom tools:

#### 1. **write_todos** - Planning & Task Decomposition
- Breaks complex tasks into discrete steps
- Tracks progress through multi-step operations
- Adapts plans as new information emerges

**Example Usage:**
```python
# Agent automatically uses write_todos when given complex tasks
orchestrator.ingest_directory('data/test_sources/hr')
# Agent creates todo list:
# □ List all files in directory
# □ Process each file
# □ Extract metadata
# □ Classify RBAC
# □ Generate embeddings
# □ Store in database
```

#### 2. **task** - Subagent Spawning
- Spawns specialized subagents for context isolation
- Keeps main agent's context clean
- Enables deep focus on specific subtasks

**Example Usage:**
```python
# MasterOrchestrator spawns specialized agents
orchestrator.query("Complex multi-step question", user_id="alice@acmecorp.com")
# Orchestrator uses task tool to:
# 1. Spawn RetrievalAgent for permission check
# 2. Spawn RetrievalAgent for vector search
# 3. Aggregate results
```

#### 3. **File System Tools** - Context Management
- **ls**: List directory contents
- **read_file**: Read file content (with line ranges)
- **write_file**: Create new files
- **edit_file**: Modify existing files

**Example Usage:**
```python
# Agent uses file tools to prevent context overflow
# 1. ls to find documents
# 2. read_file for each document (in chunks if large)
# 3. write_file to save analysis results
# 4. edit_file to update configs based on findings
```

## Agent Architecture

### IngestionAgent
**Purpose**: Autonomous document processing with RBAC classification

**Custom Tools**:
- chunk_document_tool
- extract_metadata_tool
- classify_rbac_tool
- generate_embeddings_tool
- store_embeddings_tool
- get_system_status_tool

**Built-in Tools** (from DeepAgents):
- write_todos (for planning multi-document ingestion)
- task (for parallel processing)
- ls, read_file, write_file, edit_file

**Workflow**:
1. Agent receives document path
2. Uses write_todos to plan processing steps
3. Uses read_file to load document
4. Chunks, extracts metadata, classifies RBAC
5. Generates embeddings and stores
6. Uses write_file to save processing report

### RetrievalAgent
**Purpose**: Query processing with strict RBAC enforcement

**Custom Tools**:
- permission_check_tool
- vector_search_tool
- rerank_results_tool
- synthesize_answer_tool
- graph_expand_tool
- get_system_status_tool
- query_database_tool

**Built-in Tools** (from DeepAgents):
- write_todos (for multi-step query decomposition)
- task (for spawning focused sub-queries)
- read_file (for accessing documents)

**Workflow**:
1. Receives user query + user_id
2. Uses write_todos to break down complex queries
3. Checks permissions for user
4. Searches vector database
5. Filters by RBAC permissions
6. Synthesizes answer with citations

### HealingAgent
**Purpose**: REFRAG self-healing and system optimization

**Custom Tools**:
- analyze_heatmap_tool
- detect_low_quality_tool
- generate_synthetic_questions_tool
- reindex_documents_tool
- optimize_chunk_strategy_tool
- get_system_status_tool

**Built-in Tools** (from DeepAgents):
- write_todos (for planning optimization strategies)
- task (for parallel healing operations)
- read_file, write_file (for analysis reports)

**Workflow**:
1. Analyzes query heatmap for cold spots
2. Uses write_todos to plan healing strategies
3. Detects low-quality chunks
4. Generates synthetic questions
5. Reindexes problematic documents
6. Measures improvement delta

### MasterOrchestrator
**Purpose**: Top-level coordinator routing to specialized agents

**Custom Tools**:
- route_to_ingestion
- route_to_retrieval
- route_to_healing
- analyze_system_health
- get_system_status

**Built-in Tools** (from DeepAgents):
- task (for spawning specialized agents)
- write_todos (for complex multi-agent workflows)

**Workflow**:
1. Receives request + context
2. Uses write_todos to plan multi-agent workflow
3. Uses task to spawn appropriate agent(s)
4. Aggregates results
5. Returns response

## Verification

### Check DeepAgents Installation
```bash
pip show deepagents
```

### Verify Built-in Tools
The write_todos, task, and file system tools are NOT in your custom tools list - they are automatically added by `create_deep_agent()`.

### Run Demos
```bash
# Initialize system
python quick_start.py

# Full demonstration
python example_usage.py

# DeepAgents features demo
python demo_deepagents_features.py
```

### Monitor Agent Behavior
1. **LangSmith Traces**: See write_todos and task calls
2. **agent_spawns table**: Track subagent spawning
3. **agent_operations table**: Monitor all agent actions
4. **Logs**: Watch for planning and task decomposition

## Quick Start

```python
from init_refrag import initialize_refrag_system

# Initialize
orchestrator, services = initialize_refrag_system()

# Complex ingestion (agent will use write_todos)
orchestrator.ingest_directory('data/test_sources/hr')

# Multi-step query (agent will use write_todos + task)
result = orchestrator.query(
    "Compare vacation policies across all documents",
    user_id="alice@acmecorp.com"
)

# Healing (agent will use write_todos to plan optimization)
orchestrator.heal()
```

## Key Benefits

✅ **Autonomous Planning**: Agents break down complex tasks automatically
✅ **Context Management**: File tools prevent context window overflow
✅ **Subagent Isolation**: Clean context via specialized agents
✅ **Official Library**: Using LangChain's production-ready DeepAgents
✅ **Full RBAC**: Enterprise-grade permission enforcement
✅ **Self-Healing**: REFRAG continuous improvement

## Next Steps

1. ✅ System initialized with Ollama
2. ✅ HuggingFace key configured
3. ✅ DeepAgents library verified
4. ⏭️ Run first ingestion with write_todos
5. ⏭️ Test multi-step queries with task spawning
6. ⏭️ Monitor LangSmith for agent traces
7. ⏭️ Run healing cycle and measure improvements
