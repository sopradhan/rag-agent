"""
Tracking Schema
Tables for agent tracking and system monitoring
"""


def get_tracking_schema() -> str:
    """Get SQL schema for tracking tables"""
    return """
-- ============================================================================
-- TRACKING TABLES
-- ============================================================================

-- Agent spawns (track parent-child agent relationships)
CREATE TABLE IF NOT EXISTS agent_spawns (
    spawn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_agent TEXT NOT NULL,
    child_agent TEXT NOT NULL,
    spawn_reason TEXT,
    spawn_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    completion_timestamp DATETIME,
    status TEXT DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS idx_spawns_parent ON agent_spawns(parent_agent);
CREATE INDEX IF NOT EXISTS idx_spawns_timestamp ON agent_spawns(spawn_timestamp);

-- Query history (detailed query logs)
CREATE TABLE IF NOT EXISTS query_history (
    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    query_text TEXT NOT NULL,
    query_type TEXT,
    response TEXT,
    execution_time_ms INTEGER,
    num_chunks_retrieved INTEGER,
    num_chunks_filtered INTEGER,
    status TEXT DEFAULT 'completed',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_query_user ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_query_timestamp ON query_history(timestamp);

-- Healing operations (REFRAG self-healing logs)
CREATE TABLE IF NOT EXISTS healing_operations (
    healing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy TEXT NOT NULL,
    target_docs TEXT,
    reason TEXT,
    actions_taken TEXT,
    before_metrics TEXT,
    after_metrics TEXT,
    improvement_delta REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_healing_strategy ON healing_operations(strategy);
CREATE INDEX IF NOT EXISTS idx_healing_timestamp ON healing_operations(timestamp);

-- Synthetic queries (generated for testing/improvement)
CREATE TABLE IF NOT EXISTS synthetic_queries (
    synthetic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    question TEXT NOT NULL,
    expected_answer TEXT,
    generated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_tested DATETIME,
    test_accuracy REAL,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_synthetic_doc ON synthetic_queries(doc_id);

-- Agent memory (execution logs for agents)
CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    memory_value TEXT,
    memory_type TEXT DEFAULT 'execution_result',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memory_agent ON agent_memory(agent_name);
CREATE INDEX IF NOT EXISTS idx_memory_timestamp ON agent_memory(timestamp);
"""
