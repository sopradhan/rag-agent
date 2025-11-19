# REFRAG Agent Testing Guide

## Test Files Created

1. **test_ingestion_agent.py** - Document processing with RBAC classification
2. **test_retrieval_agent.py** - Query processing with permission enforcement
3. **test_healing_agent.py** - REFRAG self-healing and optimization
4. **test_orchestrator.py** - Multi-agent coordination
5. **run_all_tests.py** - Master test runner

## Quick Start

### Run Individual Tests

```bash
# Test 1: Ingestion
python test_ingestion_agent.py

# Test 2: Retrieval  
python test_retrieval_agent.py

# Test 3: Healing
python test_healing_agent.py

# Test 4: Orchestrator
python test_orchestrator.py
```

### Run All Tests

```bash
python run_all_tests.py
```

## What Each Test Demonstrates

### test_ingestion_agent.py
- Document chunking (recursive/character/token strategies)
- Metadata extraction via LLM
- RBAC classification (automatic CDR code assignment)
- Embedding generation
- Storage in vector database
- **DeepAgents features:**
  - `write_todos` for planning multi-file ingestion
  - `read_file` for loading documents
  - Custom tools integration

### test_retrieval_agent.py
- Permission checking based on user roles
- Vector similarity search
- RBAC filtering (strict enforcement)
- Result reranking
- Answer synthesis with citations
- **DeepAgents features:**
  - `write_todos` for complex query decomposition
  - `task` for spawning sub-queries
  - Query heatmap tracking

### test_healing_agent.py
- System health analysis
- Low quality chunk detection
- Synthetic question generation
- Document reindexing
- Chunk strategy optimization
- **DeepAgents features:**
  - `write_todos` for planning healing strategies
  - `read_file`/`write_file` for analysis reports
  - Improvement measurement

### test_orchestrator.py
- Intelligent agent routing
- Multi-agent workflows
- System status monitoring
- Complex task coordination
- **DeepAgents features:**
  - `task` for spawning specialized agents
  - `write_todos` for multi-step workflows
  - Agent spawn tracking

## Test Sequence

Run tests in order for best results:

1. **Ingestion** → Creates documents and embeddings
2. **Retrieval** → Queries the ingested data
3. **Healing** → Optimizes based on query patterns
4. **Orchestrator** → Coordinates all agents

## Database

Tests use:
- **SQLite**: `data/rag_system.db` (cleared before each run)
- **ChromaDB**: `data/chroma_db/` (cleared before each run)

## Configuration

Tests use **Ollama** by default:
- LLM: `gemma3:4b`
- Embeddings: `nomic-embed-text`

HuggingFace provider available (disabled by default):
- Set `HUGGINGFACE_API_KEY` in `.env` file to use

## Verification Points

Each test shows:
- ✓ Agent initialization
- ✓ Tool availability
- ✓ Database operations
- ✓ RBAC enforcement
- ✓ DeepAgents features (write_todos, task, file tools)
- ✓ Results and metrics

## Expected Output

Each test prints:
1. Initialization status
2. Test scenarios with descriptions
3. Agent decisions and planning (write_todos)
4. Results with metrics
5. Verification queries
6. Summary of features used

## Cleanup

Old files removed:
- ✓ `demo_deepagents_features.py`
- ✓ `example_usage.py`
- ✓ `init_refrag.py`
- ✓ `examples/` folder
- ✓ `scripts/` folder
- ✓ Old databases

## Next Steps

After running tests:
1. Check `data/rag_system.db` for stored data
2. Review agent operation logs
3. Inspect query heatmap
4. Monitor healing operations
5. Verify RBAC permissions

## Troubleshooting

**No documents found**: Run `test_ingestion_agent.py` first

**No query history**: Run `test_retrieval_agent.py` after ingestion

**Ollama connection error**: 
```bash
# Start Ollama
ollama serve

# Pull required models
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

**Import errors**: Install dependencies
```bash
pip install -r requirements.txt
```
