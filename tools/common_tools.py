"""
Common Tools
Shared utility tools for all agents
"""
import json
from typing import Dict, Any
from langchain_core.tools import tool


@tool
def get_system_status_tool(db_service, vectordb_service) -> str:
    """
    Get comprehensive system status.
    
    Args:
        db_service: Database service instance
        vectordb_service: Vector DB service instance
        
    Returns:
        JSON string with system status
    """
    try:
        # Document counts
        total_docs = db_service.query("SELECT COUNT(*) as count FROM documents")[0]['count']
        total_chunks = db_service.query("SELECT COUNT(*) as count FROM embedding_metadata")[0]['count']
        vector_count = vectordb_service.count()
        
        # Operation stats
        total_ops = db_service.query("SELECT COUNT(*) as count FROM agent_operations")[0]['count']
        recent_ops = db_service.query("""
            SELECT COUNT(*) as count FROM agent_operations 
            WHERE timestamp > datetime('now', '-24 hours')
        """)[0]['count']
        
        # Token usage
        total_tokens = db_service.query("""
            SELECT SUM(total_tokens) as total FROM llm_token_usage
        """)
        tokens = total_tokens[0]['total'] if total_tokens and total_tokens[0]['total'] else 0
        
        # Query stats
        total_queries = db_service.query("SELECT COUNT(*) as count FROM query_history")[0]['count']
        avg_time = db_service.query("""
            SELECT AVG(execution_time_ms) as avg FROM query_history
        """)
        avg_exec_time = avg_time[0]['avg'] if avg_time and avg_time[0]['avg'] else 0
        
        # RBAC stats
        total_roles = db_service.query("SELECT COUNT(*) as count FROM role_mappings")[0]['count']
        total_users = db_service.query("SELECT COUNT(DISTINCT user_id) as count FROM user_roles")[0]['count']
        
        # Healing stats
        total_healing = db_service.query("SELECT COUNT(*) as count FROM healing_operations")[0]['count']
        
        return json.dumps({
            "success": True,
            "documents": {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "vector_embeddings": vector_count
            },
            "operations": {
                "total_operations": total_ops,
                "recent_operations_24h": recent_ops,
                "total_tokens_used": tokens
            },
            "queries": {
                "total_queries": total_queries,
                "avg_execution_time_ms": round(avg_exec_time, 2) if avg_exec_time else 0
            },
            "rbac": {
                "total_roles": total_roles,
                "total_users": total_users
            },
            "healing": {
                "total_healing_operations": total_healing
            }
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


@tool
def query_database_tool(sql_query: str, db_service) -> str:
    """
    Execute a SQL query on the database (read-only).
    
    Args:
        sql_query: SQL SELECT query
        db_service: Database service instance
        
    Returns:
        JSON string with query results
    """
    try:
        # Security: Only allow SELECT queries
        if not sql_query.strip().upper().startswith('SELECT'):
            return json.dumps({
                "success": False,
                "error": "Only SELECT queries are allowed"
            })
        
        results = db_service.query(sql_query)
        
        return json.dumps({
            "success": True,
            "num_rows": len(results),
            "results": results[:100]  # Limit to 100 rows
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })
