"""
Database Abstraction Layer
Provides abstract interface for all database operations.
Decouples agents/orchestrators from direct SQL queries.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import sqlite3
from datetime import datetime


class OperationType(Enum):
    """Database operation types."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class DocumentStatus(Enum):
    """Document status enumeration."""
    PENDING = "pending"
    INDEXED = "indexed"
    FRAGMENTED = "fragmented"
    ARCHIVED = "archived"


@dataclass
class DBQuery:
    """Represents a database query."""
    operation: OperationType
    table: str
    conditions: Optional[Dict[str, Any]] = None
    values: Optional[Dict[str, Any]] = None
    joins: Optional[List[str]] = None
    order_by: Optional[List[str]] = None
    limit: Optional[int] = None


class BaseDatabase(ABC):
    """Abstract base class for database implementations."""
    
    @abstractmethod
    def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query."""
        pass
    
    @abstractmethod
    def execute(self, sql: str, params: Optional[Tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE query."""
        pass
    
    @abstractmethod
    def commit(self):
        """Commit transaction."""
        pass
    
    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        pass
    
    @abstractmethod
    def get_documents_by_department(self, department_id: int) -> List[Dict[str, Any]]:
        """Get documents by department."""
        pass
    
    @abstractmethod
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        pass
    
    @abstractmethod
    def get_department_by_name(self, company_id: int, dept_name: str) -> Optional[Dict[str, Any]]:
        """Get department by name."""
        pass
    
    @abstractmethod
    def get_documents_with_rbac(self, user_id: int, operation: str = "read") -> List[Dict[str, Any]]:
        """Get documents user can access."""
        pass


class SQLiteDatabase(BaseDatabase):
    """SQLite database implementation."""
    
    def __init__(self, db_path: str = "data/rag_system.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
    
    def query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query."""
        cursor = self.conn.cursor()
        cursor.execute(sql, params or ())
        return [dict(row) for row in cursor.fetchall()]
    
    def execute(self, sql: str, params: Optional[Tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE query."""
        cursor = self.conn.cursor()
        cursor.execute(sql, params or ())
        self.commit()
        return cursor.lastrowid
    
    def commit(self):
        """Commit transaction."""
        self.conn.commit()
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID."""
        sql = "SELECT * FROM documents WHERE doc_id = ?"
        results = self.query(sql, (doc_id,))
        return results[0] if results else None
    
    def get_documents_by_department(self, department_id: int) -> List[Dict[str, Any]]:
        """Get documents accessible to department."""
        sql = """
            SELECT DISTINCT d.* FROM documents d
            JOIN document_rbac dr ON d.doc_id = dr.doc_id
            WHERE dr.department_id = ?
        """
        return self.query(sql, (department_id,))
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        sql = """
            SELECT u.*, c.name as company_name, d.name as department_name, r.role_name
            FROM users u
            LEFT JOIN company c ON u.company_id = c.company_id
            LEFT JOIN department d ON u.department_id = d.department_id
            LEFT JOIN role r ON u.role_id = r.role_id
            WHERE u.user_id = ?
        """
        results = self.query(sql, (user_id,))
        return results[0] if results else None
    
    def get_department_by_name(self, company_id: int, dept_name: str) -> Optional[Dict[str, Any]]:
        """Get department by name."""
        sql = "SELECT * FROM department WHERE company_id = ? AND name = ?"
        results = self.query(sql, (company_id, dept_name))
        return results[0] if results else None
    
    def get_documents_with_rbac(self, user_id: int, operation: str = "read") -> List[Dict[str, Any]]:
        """Get documents user can access based on RBAC."""
        sql = """
            SELECT DISTINCT d.* FROM documents d
            JOIN document_rbac dr ON d.doc_id = dr.doc_id
            JOIN users u ON u.user_id = ?
            WHERE dr.department_id = u.department_id
            AND d.min_access_level <= (
                SELECT access_level FROM role WHERE role_id = u.role_id
            )
        """
        return self.query(sql, (user_id,))
    
    def get_company(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company by ID."""
        sql = "SELECT * FROM company WHERE company_id = ?"
        results = self.query(sql, (company_id,))
        return results[0] if results else None
    
    def get_all_departments(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all departments for company."""
        sql = "SELECT * FROM department WHERE company_id = ? ORDER BY level"
        return self.query(sql, (company_id,))
    
    def get_all_roles(self, department_id: int) -> List[Dict[str, Any]]:
        """Get all roles for department."""
        sql = "SELECT * FROM role WHERE department_id = ? ORDER BY role_id"
        return self.query(sql, (department_id,))
    
    def count_documents(self, department_id: Optional[int] = None) -> int:
        """Count documents."""
        if department_id:
            sql = """
                SELECT COUNT(DISTINCT d.doc_id) as count FROM documents d
                JOIN document_rbac dr ON d.doc_id = dr.doc_id
                WHERE dr.department_id = ?
            """
            results = self.query(sql, (department_id,))
        else:
            sql = "SELECT COUNT(*) as count FROM documents"
            results = self.query(sql)
        
        return results[0]["count"] if results else 0
    
    def get_namespace_statistics(self, namespace: str) -> Dict[str, Any]:
        """Get statistics for a namespace."""
        sql = """
            SELECT 
                COUNT(*) as doc_count,
                AVG(LENGTH(content)) as avg_size,
                MIN(LENGTH(content)) as min_size,
                MAX(LENGTH(content)) as max_size
            FROM documents
            WHERE namespace = ?
        """
        results = self.query(sql, (namespace,))
        return results[0] if results else {}
    
    def get_document_metadata(self, doc_id: str) -> Dict[str, Any]:
        """Get all metadata for a document."""
        sql = "SELECT key, value FROM metadata WHERE doc_id = ?"
        results = self.query(sql, (doc_id,))
        return {row["key"]: row["value"] for row in results}


class DatabaseManager:
    """Manages database abstraction and query building."""
    
    def __init__(self, db_type: str = "sqlite", db_path: str = "data/rag_system.db"):
        if db_type.lower() == "sqlite":
            self.db = SQLiteDatabase(db_path)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    # Document operations
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document."""
        return self.db.get_document(doc_id)
    
    def get_documents_by_department(self, department_id: int) -> List[Dict[str, Any]]:
        """Get documents for department."""
        return self.db.get_documents_by_department(department_id)
    
    # User operations
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user."""
        return self.db.get_user_by_id(user_id)
    
    # RBAC operations
    def get_accessible_documents(self, user_id: int, operation: str = "read") -> List[Dict[str, Any]]:
        """Get documents user can access."""
        return self.db.get_documents_with_rbac(user_id, operation)
    
    # Organizational operations
    def get_company(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company."""
        return self.db.get_company(company_id)
    
    def get_department(self, company_id: int, dept_name: str) -> Optional[Dict[str, Any]]:
        """Get department."""
        return self.db.get_department_by_name(company_id, dept_name)
    
    def get_departments(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all departments."""
        return self.db.get_all_departments(company_id)
    
    def get_roles(self, department_id: int) -> List[Dict[str, Any]]:
        """Get roles for department."""
        return self.db.get_all_roles(department_id)
    
    # Statistics operations
    def get_document_count(self, department_id: Optional[int] = None) -> int:
        """Get document count."""
        return self.db.count_documents(department_id)
    
    def get_namespace_stats(self, namespace: str) -> Dict[str, Any]:
        """Get namespace statistics."""
        return self.db.get_namespace_statistics(namespace)
    
    def get_document_metadata(self, doc_id: str) -> Dict[str, Any]:
        """Get document metadata."""
        return self.db.get_document_metadata(doc_id)
    
    # Raw query access (for complex queries not covered above)
    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """Execute custom SELECT query."""
        return self.db.query(sql, params)
    
    def execute_update(self, sql: str, params: Optional[Tuple] = None) -> int:
        """Execute custom INSERT/UPDATE/DELETE query."""
        return self.db.execute(sql, params)
