"""
Config-Driven Database Manager
Automatically creates and manages tables based on system_config.yaml
No hardcoding - all table definitions come from configuration
"""

import sqlite3
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class ConfigDrivenDatabase:
    """Database manager that reads all table definitions from config."""
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """Initialize database from configuration."""
        self.config = self._load_config(config_path)
        self.db_config = self.config.get("database", {})
        self.db_path = self.db_config.get("path", "data/rag_system.db")
        
        # Create database directory if needed
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection
        self.conn = self._create_connection()
        
        # Create all tables from config
        self._create_tables_from_config()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create database connection."""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.db_config.get("connection_timeout", 30),
            check_same_thread=self.db_config.get("check_same_thread", False)
        )
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_tables_from_config(self):
        """Create all tables defined in configuration."""
        tables = self.db_config.get("tables", {})
        
        for table_name, table_def in tables.items():
            self._create_table(table_name, table_def)
            self._create_indexes(table_name, table_def.get("indexes", []))
    
    def _create_table(self, table_name: str, table_def: Dict[str, Any]):
        """Create a single table from definition."""
        columns = table_def.get("columns", [])
        
        # Build column definitions
        col_defs = []
        for col in columns:
            col_name = col.get("name")
            col_type = col.get("type")
            col_constraints = col.get("constraints", "")
            
            col_def = f"{col_name} {col_type}"
            if col_constraints:
                col_def += f" {col_constraints}"
            
            col_defs.append(col_def)
        
        # Add foreign keys if defined
        foreign_keys = table_def.get("foreign_keys", [])
        for fk in foreign_keys:
            fk_cols = ", ".join(fk["columns"])
            fk_ref = fk["references"]
            col_defs.append(f"FOREIGN KEY ({fk_cols}) REFERENCES {fk_ref}")
        
        # Create table SQL
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        create_sql += ",\n".join(f"    {col_def}" for col_def in col_defs)
        create_sql += "\n)"
        
        # Execute
        cursor = self.conn.cursor()
        cursor.execute(create_sql)
        self.conn.commit()
    
    def _create_indexes(self, table_name: str, indexes: List[Dict[str, Any]]):
        """Create indexes for a table."""
        cursor = self.conn.cursor()
        
        for idx in indexes:
            idx_name = idx.get("name")
            idx_cols = ", ".join(idx.get("columns", []))
            
            create_idx_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({idx_cols})"
            cursor.execute(create_idx_sql)
        
        self.conn.commit()
    
    # Generic CRUD Operations
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """Generic insert into any table."""
        columns = list(data.keys())
        placeholders = ["?" for _ in columns]
        values = [data[col] for col in columns]
        
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        
        cursor = self.conn.cursor()
        cursor.execute(sql, values)
        self.conn.commit()
        
        return cursor.lastrowid
    
    def update(self, table_name: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        """Generic update for any table."""
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        where_clause = " AND ".join([f"{col} = ?" for col in where.keys()])
        
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
        
        values = list(data.values()) + list(where.values())
        
        cursor = self.conn.cursor()
        cursor.execute(sql, values)
        self.conn.commit()
        
        return cursor.rowcount
    
    def select(
        self, 
        table_name: str, 
        columns: List[str] = None,
        where: Dict[str, Any] = None,
        order_by: str = None,
        limit: int = None,
        offset: int = None
    ) -> List[Dict[str, Any]]:
        """Generic select from any table."""
        col_str = ", ".join(columns) if columns else "*"
        sql = f"SELECT {col_str} FROM {table_name}"
        
        values = []
        if where:
            where_clause = " AND ".join([f"{col} = ?" for col in where.keys()])
            sql += f" WHERE {where_clause}"
            values = list(where.values())
        
        if order_by:
            sql += f" ORDER BY {order_by}"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        if offset:
            sql += f" OFFSET {offset}"
        
        cursor = self.conn.cursor()
        cursor.execute(sql, values)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def delete(self, table_name: str, where: Dict[str, Any]) -> int:
        """Generic delete from any table."""
        where_clause = " AND ".join([f"{col} = ?" for col in where.keys()])
        sql = f"DELETE FROM {table_name} WHERE {where_clause}"
        
        values = list(where.values())
        
        cursor = self.conn.cursor()
        cursor.execute(sql, values)
        self.conn.commit()
        
        return cursor.rowcount
    
    def execute(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute custom SQL query."""
        cursor = self.conn.cursor()
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        self.conn.commit()
        
        if cursor.description:
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
            return []
    
    # Helper methods with timestamp handling
    
    def insert_with_timestamp(self, table_name: str, data: Dict[str, Any]) -> int:
        """Insert with automatic created_at timestamp."""
        data["created_at"] = datetime.now().isoformat()
        return self.insert(table_name, data)
    
    def update_with_timestamp(self, table_name: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
        """Update with automatic updated_at timestamp."""
        data["updated_at"] = datetime.now().isoformat()
        return self.update(table_name, data, where)
    
    # Statistics and monitoring
    
    def get_table_stats(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        tables = self.db_config.get("tables", {})
        stats = {}
        
        cursor = self.conn.cursor()
        for table_name in tables.keys():
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            result = cursor.fetchone()
            stats[table_name] = result["count"]
        
        return stats
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema for a specific table."""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def vacuum(self):
        """Optimize database."""
        cursor = self.conn.cursor()
        cursor.execute("VACUUM")
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Backward compatibility wrapper for existing RAGDatabase usage
class RAGDatabase(ConfigDrivenDatabase):
    """Wrapper to maintain compatibility with existing code."""
    
    def __init__(self, db_path: str = None, config_path: str = "config/system_config.yaml"):
        """Initialize with optional db_path override."""
        super().__init__(config_path)
        
        # Override db_path if provided (for backward compatibility)
        if db_path:
            self.db_path = db_path
            self.conn = self._create_connection()
    
    # Specialized methods for common operations
    
    def insert_document(self, doc_id: str, source: str, content: str, **kwargs) -> int:
        """Insert document into documents table."""
        data = {
            "doc_id": doc_id,
            "source": source,
            "content": content,
            **kwargs
        }
        return self.insert_with_timestamp("documents", data)
    
    def get_all_documents(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all documents."""
        return self.select("documents", limit=limit, order_by="created_at DESC")
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get single document by ID."""
        results = self.select("documents", where={"doc_id": doc_id})
        return results[0] if results else None
    
    def insert_metadata(self, doc_id: str, metadata: Dict[str, str]):
        """Insert metadata for a document."""
        for key, value in metadata.items():
            self.insert_with_timestamp("metadata", {
                "doc_id": doc_id,
                "key": key,
                "value": str(value)
            })
    
    def get_metadata(self, doc_id: str) -> Dict[str, str]:
        """Get metadata for a document."""
        rows = self.select("metadata", where={"doc_id": doc_id})
        return {row["key"]: row["value"] for row in rows}
    
    def log_operation(
        self, 
        operation_type: str, 
        agent_name: str, 
        status: str,
        input_data: str = None,
        output_data: str = None,
        error_message: str = None,
        duration: float = 0.0,
        user_id: str = None
    ) -> int:
        """Log an operation to history."""
        data = {
            "operation_type": operation_type,
            "agent_name": agent_name,
            "status": status,
            "input_data": input_data,
            "output_data": output_data,
            "error_message": error_message,
            "duration_seconds": duration,
            "user_id": user_id
        }
        return self.insert_with_timestamp("operations_history", data)
    
    def get_operation_history(self, limit: int = 100, operation_type: str = None) -> List[Dict[str, Any]]:
        """Get operation history, optionally filtered by operation type."""
        where = {}
        if operation_type:
            where["operation_type"] = operation_type
        return self.select("operations_history", where=where if where else None, limit=limit, order_by="created_at DESC")
    
    def log_query(
        self,
        query: str,
        user_id: str,
        user_role: str = None,
        documents_retrieved: int = 0,
        answer: str = None,
        response_time: float = 0.0,
        success: bool = True
    ) -> int:
        """Log a query to history."""
        data = {
            "query": query,
            "user_id": user_id,
            "user_role": user_role,
            "documents_retrieved": documents_retrieved,
            "answer": answer,
            "response_time": response_time,
            "success": success
        }
        return self.insert_with_timestamp("query_history", data)
    
    def get_query_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get query history."""
        return self.select("query_history", limit=limit, order_by="created_at DESC")
    
    def log_agent_spawn(
        self,
        parent_agent: str,
        child_agent: str,
        task_description: str = None,
        status: str = "pending"
    ) -> int:
        """Log agent spawn."""
        data = {
            "parent_agent": parent_agent,
            "child_agent": child_agent,
            "task_description": task_description,
            "status": status
        }
        return self.insert_with_timestamp("agent_spawns", data)
    
    def get_agent_spawn_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get agent spawn history."""
        return self.select("agent_spawns", limit=limit, order_by="created_at DESC")
    
    def insert_incident(self, incident_data: Dict[str, Any]) -> int:
        """Insert incident into incident_knowledge table."""
        return self.insert_with_timestamp("incident_knowledge", incident_data)
    
    def get_all_incidents(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all incidents."""
        return self.select("incident_knowledge", limit=limit, order_by="created_at DESC")
    
    def search_incidents(self, **filters) -> List[Dict[str, Any]]:
        """Search incidents with filters."""
        return self.select("incident_knowledge", where=filters)
    
    def store_agent_memory(
        self,
        agent_name: str,
        memory_key: str,
        memory_value: str,
        memory_type: str = "state",
        expires_at: str = None
    ) -> int:
        """Store agent memory."""
        data = {
            "agent_name": agent_name,
            "memory_key": memory_key,
            "memory_value": memory_value,
            "memory_type": memory_type,
            "expires_at": expires_at
        }
        return self.insert_with_timestamp("agent_memory", data)
    
    def get_agent_memory(self, agent_name: str, memory_key: str = None) -> List[Dict[str, Any]]:
        """Get agent memory."""
        where = {"agent_name": agent_name}
        if memory_key:
            where["memory_key"] = memory_key
        return self.select("agent_memory", where=where)
    
    def clear_agent_memory(self, agent_name: str, memory_key: str = None):
        """Clear agent memory."""
        where = {"agent_name": agent_name}
        if memory_key:
            where["memory_key"] = memory_key
        self.delete("agent_memory", where)
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        stats = self.get_table_stats()
        
        # Add recent operations
        recent_ops = self.get_operation_history(limit=10)
        
        # Add recent queries
        recent_queries = self.get_query_history(limit=10)
        
        return {
            "table_counts": stats,
            "recent_operations": recent_ops,
            "recent_queries": recent_queries
        }
    
    def get_dashboard_statistics(self) -> Dict[str, Any]:
        """Get dashboard statistics with proper key names."""
        conn = self._create_connection()
        cursor = conn.cursor()
        
        try:
            # Count documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_documents = cursor.fetchone()[0]
            
            # Count queries in last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM query_history 
                WHERE datetime(created_at) >= datetime('now', '-1 day')
            """)
            queries_24h = cursor.fetchone()[0]
            
            # Get average response time
            cursor.execute("""
                SELECT AVG(response_time) FROM query_history 
                WHERE response_time IS NOT NULL
            """)
            avg_response_time = cursor.fetchone()[0] or 0.0
            
            # Count active agents
            cursor.execute("""
                SELECT COUNT(DISTINCT parent_agent) FROM agent_spawns
            """)
            active_agents = cursor.fetchone()[0]
            
            return {
                "total_documents": total_documents,
                "queries_24h": queries_24h,
                "avg_response_time": round(avg_response_time, 2),
                "active_agents": active_agents
            }
        finally:
            conn.close()
    
    def get_healing_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get healing operations history."""
        return self.select("healing_operations", limit=limit, order_by="created_at DESC")

