# RAG Agent System - Installation Guide

## Overview

The RAG Agent System is a production-ready, enterprise-grade retrieval-augmented generation (RAG) system with:

- **LangChain DeepAgents V2**: 5-agent pipeline with chain-of-thought reasoning
- **Hierarchical RBAC**: Company → Department → Role → Users structure
- **Multi-Source Ingestion**: Support for PDF, JSON, CSV, TXT documents
- **Vector Search**: ChromaDB with sentence-transformers embeddings
- **Dashboard**: Streamlit-based UI with real-time monitoring
- **Easy Integration**: One-command initialization for any project/system

## System Requirements

### Minimum Requirements

- **Python**: 3.10+
- **RAM**: 8GB (16GB recommended)
- **Disk Space**: 20GB (for ChromaDB, logs, and test data)
- **OS**: Linux, macOS, or Windows (with WSL2)

### Required External Services

- **Ollama**: LLM backend (runs locally)
  - Download: https://ollama.ai
  - Model: llama3.2 (4.2GB)

### Optional Services

- **ChromaDB Server**: For distributed deployments
- **Postgres**: Alternative to SQLite for scaling

## Quick Start (5 minutes)

### 1. Clone/Download the Project

```bash
cd /path/to/your/project
git clone <repo-url> rag-agent-system
cd rag-agent-system
```

### 2. Run Initialization

```bash
# Full initialization (installs dependencies + sets up everything)
python initialize.py

# Or with specific path
python initialize.py --path /your/installation/path
```

### 3. Start Required Services

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Pull the model
ollama pull llama3.2:latest

# Terminal 3: Start the Dashboard
streamlit run dashboard.py
```

### 4. Access the System

- **Dashboard**: http://localhost:8501
- **API** (if running): http://localhost:8000

## Detailed Installation Steps

### Step 1: Install Python Dependencies

```bash
# Method 1: Using initialization script (recommended)
python initialize.py

# Method 2: Manual installation
pip install -r requirements.txt

# Method 3: For development
pip install -e .  # Installs as editable package
```

### Step 2: Install Ollama

```bash
# macOS
brew install ollama

# Linux (Ubuntu/Debian)
curl -sSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download

# Pull the required model
ollama pull llama3.2:latest
```

### Step 3: Configure Environment

The initialization script creates `.env` automatically, but you can customize:

```bash
# Copy default .env
cp .env.example .env

# Edit configuration
nano .env
```

Configuration options:

```env
# Ollama
OLLAMA_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434

# Database
DATABASE_PATH=./data/rag_system.db
CHROMADB_PERSISTENT_DIR=./data/chroma_db

# Embeddings
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# LLM Parameters
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000
```

### Step 4: Initialize Database

```bash
# Automatic (via initialize.py)
python initialize.py

# Manual initialization
python -c "
from src.storage.sqlite_storage import RAGDatabase
db = RAGDatabase()
print('Database initialized')
"
```

### Step 5: Generate Test Data

```bash
# Automatic (via initialize.py)
python initialize.py

# Manual generation
python -c "from scripts.generate_test_data import main; main()"
```

## Integration into Existing Projects

### Option 1: As a Package

```bash
# Install as pip package
pip install -e /path/to/rag-agent-system

# Use in your code
from src.orchestrator import MasterOrchestrator
from src.storage import RAGDatabase, ChromaVectorStore

orchestrator = MasterOrchestrator()
result = orchestrator.process_query("your query")
```

### Option 2: As a Service

```bash
# Run as API server
python src/orchestrator/orchestrator.py serve

# Query via HTTP
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "your question", "role": "engineer"}'
```

### Option 3: Embedded in Application

```python
# Import and use directly
import sys
sys.path.insert(0, '/path/to/rag-agent-system')

from src.orchestrator import MasterOrchestrator
from src.storage import RAGDatabase

# Initialize
db = RAGDatabase()
orchestrator = MasterOrchestrator()

# Use in your application
def search_knowledge_base(query: str):
    result = orchestrator.process_query(
        query=query,
        user_role="engineer",
        access_level=3
    )
    return result["results"]["answer"]
```

## Project Structure

```
rag-agent-system/
├── src/
│   ├── orchestrator/           # Master orchestrator
│   │   └── orchestrator.py     # Main orchestration engine
│   ├── storage/                # Data layer
│   │   ├── sqlite_storage.py   # SQLite + RBAC
│   │   └── vector_store.py     # ChromaDB integration
│   ├── subagents/              # LangChain agents
│   │   └── langchain_subagents.py
│   └── utils/                  # Utilities
├── config/                     # Configuration files
│   ├── system_config.yaml
│   ├── llm_config.yaml
│   └── data_sources.yaml
├── data/                       # Data directory (auto-created)
│   ├── rag_system.db          # SQLite database
│   ├── chroma_db/             # Vector store
│   └── test_sources/          # Test data
├── dashboard.py               # Streamlit UI
├── initialize.py              # Initialization script
├── requirements.txt           # Dependencies
├── setup.py                   # Package setup
└── README.md                  # Documentation
```

## Ingestion: Adding Your Own Data

### 1. Prepare Data

Supported formats:
- **Text**: `.txt`, `.md`
- **PDF**: `.pdf`
- **JSON**: `.json`, `.jsonl`
- **CSV**: `.csv`
- **Documents**: `.docx`, `.pptx`

### 2. Place in Data Directory

```bash
# Create source directory
mkdir -p data/my_documents

# Add your files
cp /path/to/documents/* data/my_documents/
```

### 3. Ingest via Dashboard

1. Go to Dashboard → "📥 Ingest"
2. Select source directory
3. Choose classification (engineering, hr, general, security)
4. Click "Ingest Documents"

### 4. Ingest via Code

```python
from src.orchestrator import MasterOrchestrator
from src.storage import ChromaVectorStore

orchestrator = MasterOrchestrator()
vector_store = ChromaVectorStore()

# Add documents
vector_store.add_documents(
    doc_ids=["doc1", "doc2"],
    texts=["content1", "content2"],
    metadatas=[
        {"source": "file1.txt", "classification": "engineering"},
        {"source": "file2.txt", "classification": "hr"}
    ]
)
```

## Usage Examples

### Query with RBAC

```python
from src.orchestrator import MasterOrchestrator

orchestrator = MasterOrchestrator()

# Engineer querying
result = orchestrator.process_query(
    query="What is the database rollback procedure?",
    user_role="engineer",
    access_level=3
)

print(result["results"]["answer"])
# Shows engineering documents only
```

### View Execution History

```python
# Get last 5 queries
history = orchestrator.get_execution_history(limit=5)

for execution in history:
    print(f"Query: {execution['query']}")
    print(f"Status: {execution['status']}")
    print(f"Agents: {execution['agents_executed']}")
```

### Dashboard Features

- **🔍 Retrieve**: Query with RBAC enforcement
- **📥 Ingest**: Add documents from multiple sources
- **📊 Analytics**: View COT reasoning and performance metrics
- **👥 RBAC**: Manage users, roles, and permissions
- **⚙️ System**: Configuration and status

## Troubleshooting

### Issue: Ollama Connection Failed

```bash
# Check if Ollama is running
curl http://localhost:11434

# Start Ollama
ollama serve

# Pull model if needed
ollama pull llama3.2:latest
```

### Issue: Database Lock Error

```bash
# Delete corrupted database
rm data/rag_system.db

# Reinitialize
python initialize.py
```

### Issue: Out of Memory

```bash
# Reduce batch size in config
OLLAMA_NUM_THREAD=2
OLLAMA_NUM_GPU=0  # Use CPU instead

# Or use smaller model
ollama pull mistral:latest
```

### Issue: Import Errors

```bash
# Ensure Python path is correct
export PYTHONPATH="${PYTHONPATH}:/path/to/rag-agent-system"

# Reinstall package
pip install -e .
```

## Performance Optimization

### For Production

```python
# Use connection pooling
from src.storage import RAGDatabase
db = RAGDatabase(pool_size=20)

# Enable caching
from src.orchestrator import MasterOrchestrator
orchestrator = MasterOrchestrator(enable_cache=True)
```

### For Large Datasets

```python
# Batch ingestion
for batch in document_batches:
    vector_store.add_documents(
        doc_ids=batch["ids"],
        texts=batch["texts"],
        metadatas=batch["metadatas"]
    )
```

## Security Considerations

1. **RBAC Enforcement**: All queries enforced by company:department:role
2. **Database Encryption**: SQLite encryption recommended for production
3. **API Authentication**: Add API keys for external access
4. **Network Isolation**: Run on private VPC/network

## Support & Documentation

- **README.md**: Overview and quick start
- **API Docs**: `/api/docs` when running server
- **GitHub Issues**: Report bugs and feature requests
- **Contributing**: See CONTRIBUTING.md

## License

See LICENSE file for details.

---

**Last Updated**: November 2024
**Version**: 1.0.0
