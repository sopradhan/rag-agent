"""
SQLite Storage Layer for RAG System
Stores documents, embeddings, operations history, and metadata for tracking and monitoring.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class RAGDatabase:
    """SQLite database for RAG system storage and tracking."""
    
    def __init__(self, db_path: str = "data/rag_system.db"):
        """Initialize database connection and create tables."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create all necessary tables."""
        cursor = self.conn.cursor()
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_id INTEGER,
                total_chunks INTEGER,
                classification TEXT,
                min_access_level INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Embeddings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                embedding_model TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)
        
        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)
        
        # Operations history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operations_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                error_message TEXT,
                duration_seconds REAL,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent spawn history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_spawns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_agent TEXT NOT NULL,
                child_agent TEXT NOT NULL,
                task_description TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Query history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_role TEXT,
                documents_retrieved INTEGER,
                answer TEXT,
                response_time REAL,
                success BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Healing operations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS healing_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                target_doc_ids TEXT,
                reason TEXT,
                status TEXT NOT NULL,
                results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Incident knowledge table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS incident_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                incident_description TEXT,
                incident_severity TEXT,
                resource_type TEXT,
                l1_triage TEXT,
                l2_triage TEXT,
                final_resolution TEXT,
                impacted_dollar REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Agent memory/state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                memory_key TEXT NOT NULL,
                memory_value TEXT,
                memory_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        
        # LLM Memory/Context table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                context_type TEXT NOT NULL,
                context_data TEXT NOT NULL,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
            )
        """)
        
        self.conn.commit()
    
    # ========================================================================
    # Document Operations
    # ========================================================================
    
    def insert_document(self, doc_data: Dict[str, Any]) -> int:
        """Insert a document into the database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO documents (doc_id, source, content, chunk_id, total_chunks, 
                                  classification, min_access_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_data.get("doc_id"),
            doc_data.get("source"),
            doc_data.get("content"),
            doc_data.get("chunk_id"),
            doc_data.get("total_chunks"),
            doc_data.get("classification"),
            doc_data.get("min_access_level")
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve all documents."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def search_documents_by_metadata(self, key: str, value: str) -> List[Dict[str, Any]]:
        """Search documents by metadata tags."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT d.* FROM documents d
            JOIN metadata m ON d.doc_id = m.doc_id
            WHERE m.key = ? AND m.value LIKE ?
        """, (key, f"%{value}%"))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Embedding Operations
    # ========================================================================
    
    def insert_embedding(self, doc_id: str, embedding: List[float], model: str):
        """Insert embedding for a document."""
        cursor = self.conn.cursor()
        embedding_blob = json.dumps(embedding).encode('utf-8')
        cursor.execute("""
            INSERT INTO embeddings (doc_id, embedding, embedding_model)
            VALUES (?, ?, ?)
        """, (doc_id, embedding_blob, model))
        self.conn.commit()
    
    def get_embedding(self, doc_id: str) -> Optional[List[float]]:
        """Retrieve embedding for a document."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT embedding FROM embeddings WHERE doc_id = ? ORDER BY created_at DESC LIMIT 1", (doc_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["embedding"].decode('utf-8'))
        return None
    
    def get_documents_for_reembedding(self, classification: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get documents that need re-embedding."""
        cursor = self.conn.cursor()
        if classification:
            cursor.execute("""
                SELECT d.* FROM documents d
                LEFT JOIN embeddings e ON d.doc_id = e.doc_id
                WHERE (e.doc_id IS NULL OR e.created_at < datetime('now', '-7 days'))
                AND d.classification = ?
            """, (classification,))
        else:
            cursor.execute("""
                SELECT d.* FROM documents d
                LEFT JOIN embeddings e ON d.doc_id = e.doc_id
                WHERE e.doc_id IS NULL OR e.created_at < datetime('now', '-7 days')
            """)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Metadata Operations
    # ========================================================================
    
    def insert_metadata(self, doc_id: str, key: str, value: str):
        """Insert metadata for a document."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO metadata (doc_id, key, value)
            VALUES (?, ?, ?)
        """, (doc_id, key, value))
        self.conn.commit()
    
    def get_metadata(self, doc_id: str) -> Dict[str, str]:
        """Retrieve all metadata for a document."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM metadata WHERE doc_id = ?", (doc_id,))
        return {row["key"]: row["value"] for row in cursor.fetchall()}
    
    # ========================================================================
    # Operations History
    # ========================================================================
    
    def log_operation(self, operation_type: str, agent_name: str, status: str,
                     input_data: Any = None, output_data: Any = None,
                     error_message: str = None, duration: float = None,
                     user_id: str = None) -> int:
        """Log an operation to history."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO operations_history 
            (operation_type, agent_name, status, input_data, output_data, 
             error_message, duration_seconds, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            operation_type,
            agent_name,
            status,
            json.dumps(input_data) if input_data else None,
            json.dumps(output_data) if output_data else None,
            error_message,
            duration,
            user_id
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_operation_history(self, limit: int = 100, operation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve operation history."""
        cursor = self.conn.cursor()
        if operation_type:
            cursor.execute("""
                SELECT * FROM operations_history 
                WHERE operation_type = ?
                ORDER BY created_at DESC LIMIT ?
            """, (operation_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM operations_history 
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Agent Spawn Tracking
    # ========================================================================
    
    def log_agent_spawn(self, parent_agent: str, child_agent: str, 
                       task_description: str, status: str = "started") -> int:
        """Log when an agent spawns another agent."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_spawns (parent_agent, child_agent, task_description, status)
            VALUES (?, ?, ?, ?)
        """, (parent_agent, child_agent, task_description, status))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_agent_spawn_status(self, spawn_id: int, status: str):
        """Update the status of an agent spawn."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE agent_spawns 
            SET status = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, spawn_id))
        self.conn.commit()
    
    def get_agent_spawn_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve agent spawn history."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM agent_spawns 
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Query History
    # ========================================================================
    
    def log_query(self, query: str, user_id: str, user_role: str,
                  documents_retrieved: int, answer: str,
                  response_time: float, success: bool) -> int:
        """Log a query to history."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO query_history 
            (query, user_id, user_role, documents_retrieved, answer, response_time, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (query, user_id, user_role, documents_retrieved, answer, response_time, success))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_query_history(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve query history."""
        cursor = self.conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT * FROM query_history 
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM query_history 
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # System Metrics
    # ========================================================================
    
    def log_metric(self, metric_name: str, metric_value: float, metric_type: str = "general"):
        """Log a system metric."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO system_metrics (metric_name, metric_value, metric_type)
            VALUES (?, ?, ?)
        """, (metric_name, metric_value, metric_type))
        self.conn.commit()
    
    def get_metrics(self, metric_name: Optional[str] = None, 
                    hours: int = 24) -> List[Dict[str, Any]]:
        """Retrieve system metrics."""
        cursor = self.conn.cursor()
        if metric_name:
            cursor.execute("""
                SELECT * FROM system_metrics 
                WHERE metric_name = ? 
                AND created_at >= datetime('now', '-' || ? || ' hours')
                ORDER BY created_at DESC
            """, (metric_name, hours))
        else:
            cursor.execute("""
                SELECT * FROM system_metrics 
                WHERE created_at >= datetime('now', '-' || ? || ' hours')
                ORDER BY created_at DESC
            """, (hours,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Healing Operations
    # ========================================================================
    
    def log_healing_operation(self, operation_type: str, target_doc_ids: List[str],
                              reason: str, status: str = "started") -> int:
        """Log a healing operation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO healing_operations (operation_type, target_doc_ids, reason, status)
            VALUES (?, ?, ?, ?)
        """, (operation_type, json.dumps(target_doc_ids), reason, status))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_healing_operation(self, operation_id: int, status: str, results: Dict[str, Any]):
        """Update a healing operation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE healing_operations 
            SET status = ?, results = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, json.dumps(results), operation_id))
        self.conn.commit()
    
    def get_healing_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve healing operation history."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM healing_operations 
            ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Analytics
    # ========================================================================
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for the dashboard."""
        cursor = self.conn.cursor()
        
        # Total documents
        cursor.execute("SELECT COUNT(*) as count FROM documents")
        total_docs = cursor.fetchone()["count"]
        
        # Total queries
        cursor.execute("SELECT COUNT(*) as count FROM query_history WHERE created_at >= datetime('now', '-24 hours')")
        queries_24h = cursor.fetchone()["count"]
        
        # Average response time
        cursor.execute("SELECT AVG(response_time) as avg_time FROM query_history WHERE created_at >= datetime('now', '-24 hours')")
        avg_response_time = cursor.fetchone()["avg_time"] or 0
        
        # Success rate
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN success = 1 THEN 1 END) * 100.0 / COUNT(*) as success_rate
            FROM query_history 
            WHERE created_at >= datetime('now', '-24 hours')
        """)
        success_rate = cursor.fetchone()["success_rate"] or 0
        
        # Agent spawns
        cursor.execute("SELECT COUNT(*) as count FROM agent_spawns WHERE created_at >= datetime('now', '-24 hours')")
        agent_spawns_24h = cursor.fetchone()["count"]
        
        # Healing operations
        cursor.execute("SELECT COUNT(*) as count FROM healing_operations WHERE created_at >= datetime('now', '-24 hours')")
        healing_ops_24h = cursor.fetchone()["count"]
        
        return {
            "total_documents": total_docs,
            "queries_24h": queries_24h,
            "avg_response_time": round(avg_response_time, 3),
            "success_rate": round(success_rate, 2),
            "agent_spawns_24h": agent_spawns_24h,
            "healing_ops_24h": healing_ops_24h
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    # ========================================================================
    # Incident Knowledge Operations
    # ========================================================================
    
    def insert_incident(self, incident_data: Dict[str, Any]) -> int:
        """Insert an incident into the incident_knowledge table."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO incident_knowledge (
                platform, incident_description, incident_severity, resource_type,
                l1_triage, l2_triage, final_resolution, impacted_dollar
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            incident_data.get("platform"),
            incident_data.get("incident_description"),
            incident_data.get("incident_severity"),
            incident_data.get("resource_type"),
            incident_data.get("l1_triage"),
            incident_data.get("l2_triage"),
            incident_data.get("final_resolution"),
            incident_data.get("impacted_dollar", 0.0)
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_incidents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all incidents from incident_knowledge table."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM incident_knowledge ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def search_incidents(self, **filters) -> List[Dict[str, Any]]:
        """Search incidents by filters (platform, severity, etc.)."""
        cursor = self.conn.cursor()
        where_clauses = []
        params = []
        
        for key, value in filters.items():
            if value:
                where_clauses.append(f"{key} = ?")
                params.append(value)
        
        query = "SELECT * FROM incident_knowledge"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========================================================================
    # Agent Memory Operations
    # ========================================================================
    
    def store_agent_memory(self, agent_name: str, key: str, value: str, 
                          memory_type: str = "state", expires_at: Optional[str] = None):
        """Store agent memory/state."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO agent_memory (agent_name, memory_key, memory_value, memory_type, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_name, key, value, memory_type, expires_at))
        self.conn.commit()
    
    def get_agent_memory(self, agent_name: str, key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve agent memory."""
        cursor = self.conn.cursor()
        if key:
            cursor.execute("""
                SELECT * FROM agent_memory 
                WHERE agent_name = ? AND memory_key = ?
                AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY created_at DESC
            """, (agent_name, key))
        else:
            cursor.execute("""
                SELECT * FROM agent_memory 
                WHERE agent_name = ?
                AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY created_at DESC
            """, (agent_name,))
        return [dict(row) for row in cursor.fetchall()]
    
    def clear_agent_memory(self, agent_name: str, key: Optional[str] = None):
        """Clear agent memory."""
        cursor = self.conn.cursor()
        if key:
            cursor.execute("DELETE FROM agent_memory WHERE agent_name = ? AND memory_key = ?", 
                         (agent_name, key))
        else:
            cursor.execute("DELETE FROM agent_memory WHERE agent_name = ?", (agent_name,))
        self.conn.commit()
