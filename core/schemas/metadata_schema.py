"""
Metadata Schema
Tables for document and embedding metadata
"""


def get_metadata_schema() -> str:
    """Get SQL schema for metadata tables"""
    return """
-- ============================================================================
-- METADATA TABLES
-- ============================================================================

-- Documents table (core document information)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT,
    source TEXT,
    content TEXT,
    doc_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Document metadata (key-value pairs)
CREATE TABLE IF NOT EXISTS document_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(document_id, key)
);

-- Embedding metadata (track chunking and embedding info)
CREATE TABLE IF NOT EXISTS embedding_metadata (
    embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    chunk_id TEXT NOT NULL UNIQUE,
    chunk_strategy TEXT,
    chunk_size INTEGER,
    overlap INTEGER,
    embedding_model TEXT,
    embedding_version TEXT,
    quality_score REAL DEFAULT 0.5,
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP,
    reindex_count INTEGER DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embedding_document ON embedding_metadata(document_id);
CREATE INDEX IF NOT EXISTS idx_embedding_quality ON embedding_metadata(quality_score);

-- Agent operations log (all agent activities)
CREATE TABLE IF NOT EXISTS agent_operations (
    operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    query TEXT,
    retrieved_chunks TEXT,
    reranker_scores TEXT,
    final_response TEXT,
    user_feedback INTEGER CHECK(user_feedback BETWEEN 1 AND 5),
    response_time_ms INTEGER,
    token_count INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_ops_agent ON agent_operations(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_ops_type ON agent_operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_agent_ops_timestamp ON agent_operations(timestamp);

-- LLM token usage tracking
CREATE TABLE IF NOT EXISTS llm_token_usage (
    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    operation_id INTEGER,
    provider TEXT,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost REAL DEFAULT 0.0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operation_id) REFERENCES agent_operations(operation_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_token_usage_agent ON llm_token_usage(agent_name);
CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON llm_token_usage(timestamp);

-- Query heatmap (for REFRAG analysis)
CREATE TABLE IF NOT EXISTS query_heatmap (
    heatmap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT UNIQUE NOT NULL,
    query_example TEXT,
    frequency INTEGER DEFAULT 1,
    avg_retrieval_accuracy REAL,
    avg_response_time_ms INTEGER,
    avg_user_feedback REAL,
    last_queried DATETIME DEFAULT CURRENT_TIMESTAMP,
    quality_category TEXT DEFAULT 'warm'
);

CREATE INDEX IF NOT EXISTS idx_heatmap_frequency ON query_heatmap(frequency);
CREATE INDEX IF NOT EXISTS idx_heatmap_quality ON query_heatmap(quality_category);
"""
