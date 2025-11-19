"""
Database Service - SQLite abstraction layer
Provides unified interface for all database operations
"""
import sqlite3
import json
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class DatabaseService:
    """Unified SQLite database service for REFRAG system"""
    
    def __init__(self, db_path: str):
        """
        Initialize database service
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema on first run
        self._initialize_schema()
        
        print(f"[DatabaseService] Connected to: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def query(self, sql: str, params: Tuple = ()) -> List[Dict]:
        """
        Execute SELECT query and return results as list of dicts
        
        Args:
            sql: SQL SELECT query
            params: Query parameters tuple
            
        Returns:
            List of dictionaries representing rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def execute(self, sql: str, params: Tuple = ()) -> int:
        """
        Execute INSERT/UPDATE/DELETE query
        
        Args:
            sql: SQL query
            params: Query parameters tuple
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount
    
    def insert_and_get_id(self, sql: str, params: Tuple = ()) -> int:
        """
        Execute INSERT and return last inserted row ID
        
        Args:
            sql: INSERT SQL query
            params: Query parameters tuple
            
        Returns:
            Last inserted row ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
    
    def executemany(self, sql: str, params_list: List[Tuple]) -> int:
        """
        Execute multiple queries with parameter lists
        
        Args:
            sql: SQL query
            params_list: List of parameter tuples
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.executemany(sql, params_list)
            conn.commit()
            return cursor.rowcount
    
    def _initialize_schema(self):
        """Initialize database schema if not exists"""
        with self.get_connection() as conn:
            # Import schema definitions
            from core.schemas.metadata_schema import get_metadata_schema
            from core.schemas.rbac_schema import get_rbac_schema
            from core.schemas.tracking_schema import get_tracking_schema
            
            # Execute schema creation
            conn.executescript(get_metadata_schema())
            conn.executescript(get_rbac_schema())
            conn.executescript(get_tracking_schema())
            conn.commit()
    
    # ============================================================================
    # Agent Operations Logging
    # ============================================================================
    
    def log_agent_operation(self, agent_name: str, operation_type: str,
                           query: Optional[str] = None,
                           retrieved_chunks: Optional[List[str]] = None,
                           reranker_scores: Optional[List[float]] = None,
                           final_response: Optional[str] = None,
                           user_feedback: Optional[int] = None,
                           response_time_ms: Optional[int] = None,
                           token_count: Optional[int] = None,
                           metadata: Optional[Dict] = None) -> int:
        """Log agent operation for tracking and healing analysis"""
        return self.insert_and_get_id("""
            INSERT INTO agent_operations 
            (agent_name, operation_type, query, retrieved_chunks, reranker_scores,
             final_response, user_feedback, response_time_ms, token_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            operation_type,
            query,
            json.dumps(retrieved_chunks) if retrieved_chunks else None,
            json.dumps(reranker_scores) if reranker_scores else None,
            final_response,
            user_feedback,
            response_time_ms,
            token_count,
            json.dumps(metadata) if metadata else None
        ))
    
    def log_token_usage(self, agent_name: str, operation_id: Optional[int],
                       provider: str, model: str,
                       prompt_tokens: int, completion_tokens: int,
                       estimated_cost: float = 0.0) -> int:
        """Log LLM token usage for cost tracking"""
        return self.insert_and_get_id("""
            INSERT INTO llm_token_usage
            (agent_name, operation_id, provider, model, prompt_tokens,
             completion_tokens, total_tokens, estimated_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            operation_id,
            provider,
            model,
            prompt_tokens,
            completion_tokens,
            prompt_tokens + completion_tokens,
            estimated_cost
        ))
    
    # ============================================================================
    # RBAC Operations
    # ============================================================================
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get all CDR codes for a user"""
        rows = self.query(
            "SELECT cdr_code FROM user_roles WHERE user_id = ?",
            (user_id,)
        )
        return [row['cdr_code'] for row in rows]
    
    def get_document_permissions(self, doc_id: str) -> List[str]:
        """Get required CDR codes for document access"""
        rows = self.query(
            "SELECT cdr_code FROM document_permissions WHERE doc_id = ?",
            (doc_id,)
        )
        return [row['cdr_code'] for row in rows]
    
    def check_permission(self, user_id: str, doc_id: str) -> bool:
        """Check if user has permission to access document"""
        user_roles = set(self.get_user_roles(user_id))
        required_roles = set(self.get_document_permissions(doc_id))
        
        # User needs at least one matching role
        has_access = bool(user_roles & required_roles)
        
        # Log access attempt
        self.log_access_attempt(user_id, doc_id, has_access, user_roles, required_roles)
        
        return has_access
    
    def log_access_attempt(self, user_id: str, doc_id: str, granted: bool,
                          user_roles: set, required_roles: set):
        """Log access attempt for audit trail"""
        self.execute("""
            INSERT INTO access_audit 
            (user_id, doc_id, granted, user_roles, required_roles)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            doc_id,
            1 if granted else 0,
            json.dumps(list(user_roles)),
            json.dumps(list(required_roles))
        ))
    
    def assign_document_permission(self, doc_id: str, cdr_code: str,
                                   sensitivity: str, subject: str,
                                   assigned_by: str = 'llm_inference'):
        """Assign RBAC permission to document"""
        self.execute("""
            INSERT OR REPLACE INTO document_permissions
            (doc_id, cdr_code, sensitivity, subject, assigned_by)
            VALUES (?, ?, ?, ?, ?)
        """, (doc_id, cdr_code, sensitivity, subject, assigned_by))
    
    # ============================================================================
    # Embedding Metadata
    # ============================================================================
    
    def insert_embedding_metadata(self, document_id: str, chunk_id: str,
                                  chunk_strategy: str, chunk_size: int,
                                  overlap: int, embedding_model: str,
                                  embedding_version: str) -> int:
        """Insert embedding metadata for tracking"""
        return self.insert_and_get_id("""
            INSERT INTO embedding_metadata
            (document_id, chunk_id, chunk_strategy, chunk_size, overlap,
             embedding_model, embedding_version, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0.5)
        """, (
            document_id, chunk_id, chunk_strategy, chunk_size, overlap,
            embedding_model, embedding_version
        ))
    
    def update_chunk_quality(self, chunk_id: str, quality_score: float):
        """Update quality score for a chunk (used by HealingAgent)"""
        self.execute("""
            UPDATE embedding_metadata
            SET quality_score = ?, last_modified = CURRENT_TIMESTAMP
            WHERE chunk_id = ?
        """, (quality_score, chunk_id))
    
    # ============================================================================
    # Query Heatmap (for REFRAG)
    # ============================================================================
    
    def update_query_heatmap(self, query_hash: str, query_example: str,
                            retrieval_accuracy: float, response_time_ms: int,
                            user_feedback: Optional[int] = None):
        """Update query heatmap for healing analysis"""
        existing = self.query(
            "SELECT * FROM query_heatmap WHERE query_hash = ?",
            (query_hash,)
        )
        
        if existing:
            # Update existing entry
            row = existing[0]
            new_freq = row['frequency'] + 1
            new_accuracy = (row['avg_retrieval_accuracy'] * row['frequency'] + retrieval_accuracy) / new_freq
            new_time = (row['avg_response_time_ms'] * row['frequency'] + response_time_ms) / new_freq
            
            if user_feedback:
                if row['avg_user_feedback']:
                    new_feedback = (row['avg_user_feedback'] * row['frequency'] + user_feedback) / new_freq
                else:
                    new_feedback = user_feedback
            else:
                new_feedback = row['avg_user_feedback']
            
            self.execute("""
                UPDATE query_heatmap
                SET frequency = ?, avg_retrieval_accuracy = ?,
                    avg_response_time_ms = ?, avg_user_feedback = ?,
                    last_queried = CURRENT_TIMESTAMP
                WHERE query_hash = ?
            """, (new_freq, new_accuracy, new_time, new_feedback, query_hash))
        else:
            # Insert new entry
            self.execute("""
                INSERT INTO query_heatmap
                (query_hash, query_example, frequency, avg_retrieval_accuracy,
                 avg_response_time_ms, avg_user_feedback, quality_category)
                VALUES (?, ?, 1, ?, ?, ?, 'warm')
            """, (query_hash, query_example, retrieval_accuracy, response_time_ms, user_feedback))
    
    def get_heatmap_analysis(self) -> Dict[str, List[Dict]]:
        """Get heatmap analysis for HealingAgent"""
        return {
            'cold_spots': self.query("""
                SELECT * FROM query_heatmap
                WHERE frequency < 10
                ORDER BY frequency ASC
                LIMIT 20
            """),
            'poor_quality': self.query("""
                SELECT * FROM query_heatmap
                WHERE avg_user_feedback IS NOT NULL AND avg_user_feedback < 3.0
                ORDER BY avg_user_feedback ASC
                LIMIT 20
            """),
            'slow_queries': self.query("""
                SELECT * FROM query_heatmap
                WHERE avg_response_time_ms > 5000
                ORDER BY avg_response_time_ms DESC
                LIMIT 20
            """)
        }
    
    # ============================================================================
    # Healing Operations
    # ============================================================================
    
    def log_healing_operation(self, strategy: str, target_docs: List[str],
                             reason: str, actions_taken: Dict,
                             before_metrics: Dict, after_metrics: Dict,
                             improvement_delta: float) -> int:
        """Log healing operation for tracking system improvements"""
        return self.insert_and_get_id("""
            INSERT INTO healing_operations
            (strategy, target_docs, reason, actions_taken, before_metrics,
             after_metrics, improvement_delta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            strategy,
            json.dumps(target_docs),
            reason,
            json.dumps(actions_taken),
            json.dumps(before_metrics),
            json.dumps(after_metrics),
            improvement_delta
        ))
