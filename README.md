# 🤖 RAG System - Config-Driven Architecture

> **Production-Ready RAG System with Intelligent Retrieval, Department-Based RBAC, and Multi-Step Reasoning**

## 🌟 Key Features

✅ **100% Config-Driven** - No hardcoding, all settings in `config/system_config.yaml`  
✅ **Dynamic Database Schema** - Tables auto-created from configuration  
✅ **Department-Based RBAC** - 6 departments with granular access control  
✅ **Multi-Step Reasoning** - AI thinking process visible (Think → Evaluate → Respond → Rethink)  
✅ **Intelligent Query Classification** - Greetings, help requests, specific queries  
✅ **Faithfulness Scoring** - Prevents hallucination with confidence levels  
✅ **Live Chat Interface** - Real-time testing with role/department selection  
✅ **Unified Database** - Single SQLite file for all operations  
✅ **One-Command Setup** - Initialize entire system with `python initialize.py`  
✅ **Enterprise Integration** - Easily embed into any project or system  

---

## 🚀 Quick Start (5 Minutes)

### 1. One-Command Installation

```bash
# This will:
# - Install all dependencies (skip with --skip-dependencies)
# - Create database with hierarchical RBAC
# - Generate sample test data (TXT, JSON, CSV)
# - Create .env configuration
# - Verify installation

python initialize.py
```

### 2. Start Services

```bash
# Terminal 1: Start Ollama (LLM backend)
ollama serve

# Terminal 2: Start Dashboard
streamlit run dashboard.py
```

### 3. Access Dashboard

Open **http://localhost:8501** and start querying!

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | 3-step quick start guide |
| [INSTALLATION.md](INSTALLATION.md) | Detailed installation & integration guide |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design & components |

---

## ⚙️ Configuration-First Design

**Everything is configured in `config/system_config.yaml`**

### To add a new database table:
1. Edit `config/system_config.yaml`
2. Add table definition under `database.tables`
3. Restart - table auto-created!

### To add a new department:
1. Add entry under `departments` in config
2. Define keywords, access level, roles
3. Restart - active immediately!

### To add a new role:
1. Add under `roles` in config
2. Set access level and description
3. Restart - appears in dropdown!

### To modify retrieval behavior:
1. Edit `retrieval` section in config
2. Change thresholds, faithfulness settings
3. Restart - new behavior active!

**No code changes needed - just edit the YAML config file!**

---

## 📊 Database Tables

All tables defined in config. Current tables:

- **documents** - RAG document storage
- **embeddings** - Vector embeddings  
- **metadata** - Document metadata
- **operations_history** - Operation tracking
- **agent_spawns** - Agent genealogy
- **query_history** - User queries
- **system_metrics** - Performance metrics
- **healing_operations** - Self-healing ops
- **incident_knowledge** - Incident data
- **agent_memory** - Agent state

---

## 🧠 Multi-Step Reasoning

The AI shows its thinking process:

```
1. 💭 THINK      → Analyze query intent
2. 🔍 EVALUATE   → Check access permissions
3. 🎯 ATTENTION  → Focus on key terms
4. 📚 RETRIEVE   → Get relevant documents
5. 💬 RESPOND    → Generate answer
6. 🔄 RETHINK    → Validate and refine
```

Each step shows confidence: 🟢 High | 🟡 Medium | 🟠 Low

---

## 🔐 Department-Based RBAC

- **Engineering** can't see Finance data
- **HR** can't see Security data
- **Employees** can't see Compliance data
- **Own department** data always accessible
- **Admins** see everything

Example:
```
Role: engineer
Department: engineering
Query: "security incidents"
Result: ❌ BLOCKED

Query: "deployment issues" 
Result: ✅ ALLOWED (3 docs)
```

---

## 🧪 Testing

```bash
# Test config system
python test_config_system.py

# Test intelligent retriever
python test_intelligent_chat.py

# Run demo with sample data
python demo_incident.py
```

---

## 📁 Key Files

- **`config/system_config.yaml`** - Main configuration (edit this!)
- **`src/storage/config_driven_db.py`** - Config-driven database
- **`src/utils/config_loader.py`** - Centralized config access
- **`src/utils/intelligent_retriever.py`** - Multi-step reasoning
- **`dashboard.py`** - Unified dashboard with all pages
- **`test_config_system.py`** - Validates config system

---

## 💡 Quick Tips

✨ **Everything configurable via YAML**  
✨ **No hardcoded table schemas**  
✨ **Add tables without touching code**  
✨ **Modify RBAC by editing config**  
✨ **All operations logged automatically**  
✨ **Generic CRUD works on any table**  

---

## 📖 Full Documentation

See `UNIFIED_DATABASE.md` for database architecture details.

---

**Tomorrow you only need to edit the config file - the code handles the rest!** 🚀
