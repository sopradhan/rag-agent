"""
Hierarchical RBAC Schema
Company → Department → Role hierarchy for proper access control
"""

RBAC_SCHEMA = """
-- Company Table
CREATE TABLE IF NOT EXISTS company (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    domain VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Department Table (supports unlimited hierarchy)
CREATE TABLE IF NOT EXISTS department (
    department_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    parent_department_id INTEGER,  -- For nested departments
    name VARCHAR(255) NOT NULL,
    level INTEGER DEFAULT 0,  -- 0=HQ, 1=Division, 2=Function, 3=Team, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES company(company_id),
    FOREIGN KEY (parent_department_id) REFERENCES department(department_id),
    UNIQUE(company_id, parent_department_id, name)
);

-- Role Table
CREATE TABLE IF NOT EXISTS role (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL,
    role_name VARCHAR(255) NOT NULL,
    role_type VARCHAR(100),  -- Full-time, Contractor, etc.
    grade VARCHAR(50),  -- L1, L2, M1, Director, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES department(department_id),
    UNIQUE(department_id, role_name, grade)
);

-- User Table (maps users to company:department:role)
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255),
    company_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES company(company_id),
    FOREIGN KEY (department_id) REFERENCES department(department_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id)
);

-- Document RBAC Mapping (which company:dept:role can access which document)
CREATE TABLE IF NOT EXISTS document_rbac (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    company_id INTEGER,  -- NULL = all companies
    department_id INTEGER,  -- NULL = all departments
    role_id INTEGER,  -- NULL = all roles
    access_level INTEGER DEFAULT 0,  -- 0=general, 1=internal, 2=confidential, 3=secret
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
    FOREIGN KEY (company_id) REFERENCES company(company_id),
    FOREIGN KEY (department_id) REFERENCES department(department_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id)
);

-- Agent Memory Table
CREATE TABLE IF NOT EXISTS agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    memory_type TEXT NOT NULL,  -- cot_step, decision, observation, etc.
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Spawn Tracking (enriched)
CREATE TABLE IF NOT EXISTS agent_spawns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_agent_id TEXT NOT NULL,
    parent_agent_name TEXT NOT NULL,
    child_agent_id TEXT NOT NULL,
    child_agent_name TEXT NOT NULL,
    task_description TEXT,
    status TEXT NOT NULL,  -- spawned, running, completed, failed
    input_data TEXT,  -- JSON
    output_data TEXT,  -- JSON
    error_message TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_cents DECIMAL(10, 4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Healing Operations Tracking
CREATE TABLE IF NOT EXISTS healing_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT UNIQUE NOT NULL,
    operation_type TEXT NOT NULL,  -- index_repair, reindex_low_quality, etc.
    target_agent TEXT,
    status TEXT NOT NULL,  -- pending, running, completed, failed
    metrics TEXT,  -- JSON with metrics
    issues_found INTEGER DEFAULT 0,
    issues_fixed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Agent Performance Tracking
CREATE TABLE IF NOT EXISTS agent_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    query_id TEXT,
    execution_time_ms INTEGER,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_cents DECIMAL(10, 4) DEFAULT 0,
    quality_score DECIMAL(3, 2),  -- 0.0 to 1.0
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query History (enriched with cost tracking)
CREATE TABLE IF NOT EXISTS query_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT UNIQUE NOT NULL,
    query TEXT NOT NULL,
    user_id INTEGER,
    company_id INTEGER,
    department_id INTEGER,
    role_id INTEGER,
    status TEXT NOT NULL,
    total_documents_found INTEGER,
    documents_returned_after_rbac INTEGER,
    answer_generated TEXT,
    confidence DECIMAL(3, 2),
    total_tokens_used INTEGER DEFAULT 0,
    total_cost_cents DECIMAL(10, 4) DEFAULT 0,
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (company_id) REFERENCES company(company_id),
    FOREIGN KEY (department_id) REFERENCES department(department_id),
    FOREIGN KEY (role_id) REFERENCES role(role_id)
);

-- COT Step Tracking (for visualization)
CREATE TABLE IF NOT EXISTS cot_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    phase TEXT NOT NULL,  -- think, evaluate, rethink, converged, complete
    iteration INTEGER,
    output TEXT,  -- JSON
    score DECIMAL(3, 2),
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES query_history(query_id)
);

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_document_rbac_doc_id ON document_rbac(doc_id);
CREATE INDEX IF NOT EXISTS idx_document_rbac_company ON document_rbac(company_id);
CREATE INDEX IF NOT EXISTS idx_document_rbac_dept ON document_rbac(department_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_spawns_parent ON agent_spawns(parent_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_performance_agent ON agent_performance(agent_id);
CREATE INDEX IF NOT EXISTS idx_query_history_user ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_cot_steps_query ON cot_steps(query_id);
CREATE INDEX IF NOT EXISTS idx_cot_steps_agent ON cot_steps(agent_id);
"""

print("[OK] Hierarchical RBAC Schema defined")
print("Tables:")
print("  - company: Root organization")
print("  - department: Hierarchical departments")
print("  - role: Roles within departments")
print("  - users: User-to-company:dept:role mapping")
print("  - document_rbac: Fine-grained document access control")
print("  - agent_memory: Agent memory persistence")
print("  - agent_spawns: Enhanced spawn tracking with costs")
print("  - healing_operations: Healing agent tracking")
print("  - agent_performance: Per-agent metrics")
print("  - query_history: Query tracking with costs")
print("  - cot_steps: COT step visualization")
