"""
RBAC Schema
Tables for role-based access control with CDR encoding
"""


def get_rbac_schema() -> str:
    """Get SQL schema for RBAC tables"""
    return """
-- ============================================================================
-- RBAC TABLES (CDR Encoding: Company-Department-Role)
-- ============================================================================

-- Role mappings (CDR code definitions)
CREATE TABLE IF NOT EXISTS role_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    department_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    cdr_code TEXT NOT NULL UNIQUE,
    company_name TEXT,
    department_name TEXT,
    role_name TEXT,
    access_level INTEGER,
    UNIQUE(company_id, department_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_role_cdr ON role_mappings(cdr_code);
CREATE INDEX IF NOT EXISTS idx_role_company ON role_mappings(company_id);

-- Document permissions (which CDR codes can access each document)
CREATE TABLE IF NOT EXISTS document_permissions (
    permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    cdr_code TEXT NOT NULL,
    sensitivity TEXT,
    subject TEXT,
    assigned_by TEXT DEFAULT 'llm_inference',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(doc_id, cdr_code),
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_doc_perms_doc ON document_permissions(doc_id);
CREATE INDEX IF NOT EXISTS idx_doc_perms_cdr ON document_permissions(cdr_code);

-- User roles (which CDR codes each user has)
CREATE TABLE IF NOT EXISTS user_roles (
    user_role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    cdr_code TEXT NOT NULL,
    company_id INTEGER,
    department_id INTEGER,
    role_id INTEGER,
    granted_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, cdr_code)
);

CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_cdr ON user_roles(cdr_code);

-- Access audit log (track all access attempts)
CREATE TABLE IF NOT EXISTS access_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    granted BOOLEAN,
    user_roles TEXT,
    required_roles TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_access_audit_user ON access_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_access_audit_doc ON access_audit(doc_id);
CREATE INDEX IF NOT EXISTS idx_access_audit_timestamp ON access_audit(timestamp);
"""
