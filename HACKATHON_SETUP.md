# 🚀 Hackathon Quick Setup Guide

## When You Get Azure OpenAI Key at Hackathon

### Step 1: Set Environment Variables

Create a `.env` file in the project root:

```bash
# Azure OpenAI Configuration (they will give you these)
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Optional: If they give you a different deployment name
# AZURE_DEPLOYMENT_NAME=gpt-4o-mini
```

### Step 2: Update Config

Edit `config/llm_config.yaml`:

```yaml
# Change these two lines:
default_provider: "azure_openai"  # Change from "ollama"

llm_providers:
  azure_openai:
    enabled: true  # Change from false
```

### Step 3: Test It

```bash
# Check status
python orchestrator.py --command status

# Quick test
python orchestrator.py --command ingest-dir --directory data/test_sources/hr

# Query test
python orchestrator.py --command retrieve --query "vacation policy" --role hr
```

---

## Current Setup (No Internet Needed)

✅ **LLM**: Ollama qwen2.5:3b (local)
✅ **Embeddings**: sentence-transformers (local)
✅ **Database**: SQLite (local)
✅ **Vector DB**: ChromaDB (local)

### Test Current Setup

```bash
# Wait for qwen2.5:3b to finish downloading
ollama list

# Then test
python test_sqlite_ingestion.py
```

---

## Azure OpenAI Models Support Tool Calling

✅ **gpt-4o-mini** (Lite model - recommended for hackathon)
✅ **gpt-4o** (Full model if available)
✅ **gpt-4** (Older but reliable)
✅ **gpt-3.5-turbo** (Fast and cheap)

All support DeepAgents tool calling!

---

## Quick Commands Reference

```bash
# System status
python orchestrator.py --command status

# Ingest directory
python orchestrator.py --command ingest-dir --directory data/test_sources/hr --subject HR --sensitivity internal

# Ingest SQLite tables
python orchestrator.py --command batch-ingest --tables knowledge_base incidents procedures

# Query with RBAC
python orchestrator.py --command retrieve --query "What incidents?" --role engineer

# Run healing
python orchestrator.py --command heal

# Check learning metrics
python orchestrator.py --command learning
```

---

## Troubleshooting at Hackathon

### If Azure OpenAI fails:
1. Check environment variables are set
2. Verify endpoint URL format: `https://{resource-name}.openai.azure.com/`
3. Check deployment name matches what they gave you
4. Verify API version is compatible

### Fallback to Ollama:
```yaml
# In llm_config.yaml
default_provider: "ollama"  # Switch back to local
```

### Memory issues:
- qwen2.5:3b uses ~2GB RAM
- If still too much, switch to gemma3:4b (but NO tool calling)
- Or use Azure OpenAI (cloud-based, no local RAM needed)

---

## Environment Variable Loading

The system checks for environment variables in this order:
1. `.env` file in project root
2. System environment variables
3. Direct values in config (not recommended for keys)

Create `.env` file:
```bash
echo "AZURE_OPENAI_API_KEY=your-key" > .env
echo "AZURE_OPENAI_ENDPOINT=your-endpoint" >> .env
```

---

## Data Sources Available

✅ Text files (`.txt`, `.md`)
✅ PDF documents
✅ Word documents (`.docx`)
✅ CSV/Excel files
✅ JSON files
✅ SQLite databases
✅ Web pages

---

## SQLite Test Database

Located: `data/test_sources/sqlite_sources/knowledge_base.db`

Tables:
- **knowledge_base** (5 records) - Technical documentation
- **incidents** (3 records) - Production incidents
- **procedures** (3 records) - Operational procedures

---

## RBAC Roles

Configured roles:
- **engineer**: Engineering department access
- **hr**: Human resources access
- **executive**: Executive level access
- **admin**: Full system access

User mapping (for testing):
- engineer → alice@acmecorp.com
- hr → bob@acmecorp.com
- executive → carol@acmecorp.com
- admin → admin@acmecorp.com

---

## Performance Tips

### For Hackathon Demo:
1. Pre-ingest all documents before demo
2. Use `--command status` to verify data loaded
3. Test queries beforehand
4. Have fallback queries ready
5. Show RBAC by testing same query with different roles

### Speed Optimization:
- Azure OpenAI: Fastest (cloud-based)
- qwen2.5:3b: Medium (local but small)
- Larger models: Slowest but more accurate

---

## What to Bring to Hackathon

📋 **Checklist:**
- [ ] This codebase on USB/laptop
- [ ] Ollama installed (backup if no internet)
- [ ] Models pre-downloaded (qwen2.5:3b)
- [ ] Test data ingested
- [ ] `.env.example` file ready to fill in
- [ ] This setup guide printed/accessible

📝 **Info They'll Give You:**
- Azure OpenAI API Key
- Azure OpenAI Endpoint URL
- Deployment name(s)
- API version (probably latest)

---

## Demo Flow Suggestion

1. **Show status**: `python orchestrator.py --command status`
2. **Ingest data**: `python orchestrator.py --command ingest-dir --directory data/test_sources/engineering`
3. **Query as engineer**: `python orchestrator.py --command retrieve --query "API documentation" --role engineer`
4. **Show RBAC**: Same query as HR user (should have different/no results)
5. **Show learning**: `python orchestrator.py --command learning`
6. **Show healing**: `python orchestrator.py --command heal`

---

## Success Criteria

✅ Documents ingested successfully
✅ Queries return relevant results
✅ RBAC enforces permissions correctly
✅ Tool calling works (write_todos visible in logs)
✅ System learns from queries
✅ Healing improves performance

Good luck! 🎉
