# Quick Start Guide - RAG Agent System

Get the RAG Agent System up and running in **under 10 minutes**.

## Prerequisites

- Python 3.10+
- 8GB RAM
- Ollama installed (https://ollama.ai)

## 3-Step Setup

### Step 1: Run Initialization (5 minutes)

```bash
cd /path/to/rag-agent-system

# One command to set everything up
python initialize.py
```

**What it does:**
- ✅ Installs all dependencies from requirements.txt
- ✅ Creates directory structure
- ✅ Initializes SQLite database with RBAC
- ✅ Generates sample test data
- ✅ Creates .env configuration
- ✅ Verifies all imports

### Step 2: Start Services (2 terminals)

**Terminal 1 - Start Ollama:**
```bash
ollama serve

# (on first run, it will automatically pull llama3.2)
```

**Terminal 2 - Start Dashboard:**
```bash
streamlit run dashboard.py

# Opens: http://localhost:8501
```

### Step 3: Use the Dashboard

1. Open http://localhost:8501
2. Navigate to **"🔍 Retrieve"** tab
3. Enter query: "What is our company policy?"
4. Click "Search"
5. View results with reasoning

## Common Tasks

### Add Your Own Documents

```bash
# 1. Create a folder for your documents
mkdir data/my_docs

# 2. Copy your files (PDF, TXT, JSON, CSV)
cp /path/to/files/* data/my_docs/

# 3. Use Dashboard:
#    - Go to "📥 Ingest" tab
#    - Select "my_docs" folder
#    - Click "Ingest"
```

### Query Programmatically

```python
from src.orchestrator import MasterOrchestrator

orchestrator = MasterOrchestrator()

# Simple query
result = orchestrator.process_query(
    query="What is the API documentation?",
    user_role="engineer"
)

print(result["results"]["answer"])
```

### Check System Status

```bash
# Via Dashboard:
# 1. Click "⚙️ System" tab
# 2. View health status, database info, loaded documents

# Via Command Line:
python -c "
from src.storage import RAGDatabase
db = RAGDatabase()
count = db.connection.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
print(f'Loaded {count} documents')
"
```

## Architecture at a Glance

```
Your Question
    ↓
Orchestrator (MasterOrchestrator)
    ↓
5-Agent Pipeline:
  1. Analyzer    → Understand question
  2. Searcher    → Find relevant docs (with RBAC)
  3. Filter      → Apply access control
  4. Ranker      → Score relevance
  5. Synthesizer → Generate answer
    ↓
Answer + Reasoning
```

## Ingestion Workflow

```
Your Documents (PDF, TXT, JSON, CSV)
    ↓
Ingestion Subagents
    ↓
Classification (engineering, hr, general, security)
    ↓
Chunking & Metadata Extraction
    ↓
Vector Embeddings (sentence-transformers)
    ↓
ChromaDB Vector Store
    ↓
SQLite Metadata Database (with RBAC)
    ↓
Ready for Retrieval
```

## Performance

- **First query**: ~30-60 seconds (model loading)
- **Subsequent queries**: ~5-10 seconds
- **Document ingestion**: ~1-5 seconds per document
- **Vector search**: <100ms for retrieval

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Ollama connection failed | Run `ollama serve` in separate terminal |
| Out of memory | Reduce `LLM_MAX_TOKENS` in .env |
| Database locked | Delete `data/rag_system.db` and re-run `python initialize.py` |
| Port 8501 already in use | Run `streamlit run dashboard.py --server.port=8502` |

## Customization

### Change LLM Model

```bash
# .env file
OLLAMA_MODEL=mistral:latest

# Then restart dashboard
```

### Adjust Query Behavior

```python
# orchestrator.py configuration
{
    "temperature": 0.3,        # Lower = more deterministic
    "max_tokens": 2000,        # Longer = more detailed
    "top_k_retrieval": 5,      # More documents considered
    "similarity_threshold": 0.5 # Stricter filtering
}
```

### Add RBAC Rules

```python
from src.storage import RAGDatabase

db = RAGDatabase()

# Create user
db.create_user(
    user_id="john_doe",
    name="John Doe",
    email="john@company.com",
    role_id="engineer"
)

# Assign to department
db.add_user_to_department(
    user_id="john_doe",
    department_id="engineering"
)
```

## Next Steps

- 📖 Read [INSTALLATION.md](INSTALLATION.md) for detailed setup
- 🔧 Check [config/](config/) for advanced configuration
- 🧪 Run tests: `pytest tests/`
- 🚀 Deploy: See Docker section below

## Docker Deployment (Optional)

```bash
# Build image
docker build -t rag-agent:latest .

# Run container
docker run -p 8501:8501 -p 11434:11434 \
  -v rag-data:/app/data \
  rag-agent:latest

# Access at http://localhost:8501
```

## Need Help?

1. Check the logs: `tail -f logs/*.log`
2. Read detailed docs: [INSTALLATION.md](INSTALLATION.md)
3. Review configuration: `config/system_config.yaml`
4. Test imports: `python -c "from src.orchestrator import *; print('OK')"`

---

**Ready?** Run `python initialize.py` and start querying!

**Last Updated**: November 2024
