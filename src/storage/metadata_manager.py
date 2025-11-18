"""
Enhanced Metadata Manager for RAG System
Efficiently stores and retrieves metadata for agent learning
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class MetadataManager:
    """
    Manages rich metadata for documents and chunks.
    Enables agents to learn from query patterns, feedback, and usage.
    """
    
    def __init__(self, db):
        """
        Initialize MetadataManager.
        
        Args:
            db: RAGDatabase instance
        """
        self.db = db
    
    def store_document_metadata(
        self,
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Store rich metadata for a document.
        
        Args:
            doc_id: Document ID
            metadata: Dictionary of metadata key-value pairs
        """
        for key, value in metadata.items():
            # Convert complex types to JSON string
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)
            
            self.db.insert_with_timestamp("metadata", {
                "doc_id": doc_id,
                "key": key,
                "value": value
            })
    
    def get_document_metadata(
        self,
        doc_id: str,
        keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve metadata for a document.
        
        Args:
            doc_id: Document ID
            keys: Optional list of specific keys to retrieve
        
        Returns:
            Dictionary of metadata
        """
        where = {"doc_id": doc_id}
        if keys:
            # SQLite doesn't support IN with parameterized queries easily
            # Fetch all and filter in Python
            pass
        
        rows = self.db.select("metadata", where=where)
        
        metadata = {}
        for row in rows:
            if keys and row["key"] not in keys:
                continue
            
            # Try to parse JSON values
            try:
                metadata[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                metadata[row["key"]] = row["value"]
        
        return metadata
    
    def update_document_metadata(
        self,
        doc_id: str,
        key: str,
        value: Any
    ) -> None:
        """Update a specific metadata key for a document."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        elif not isinstance(value, str):
            value = str(value)
        
        # Check if exists
        existing = self.db.select("metadata", where={"doc_id": doc_id, "key": key})
        
        if existing:
            # Update existing
            conn = self.db._create_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE metadata SET value = ? WHERE doc_id = ? AND key = ?",
                (value, doc_id, key)
            )
            conn.commit()
            conn.close()
        else:
            # Insert new
            self.store_document_metadata(doc_id, {key: value})
    
    def track_query_feedback(
        self,
        query_id: int,
        doc_ids: List[str],
        relevance_scores: List[float],
        user_feedback: Optional[str] = None
    ) -> None:
        """
        Track query feedback for agent learning.
        
        Args:
            query_id: Query history ID
            doc_ids: Retrieved document IDs
            relevance_scores: Relevance score for each document
            user_feedback: Optional user feedback
        """
        feedback_data = {
            "query_id": query_id,
            "doc_relevance": dict(zip(doc_ids, relevance_scores)),
            "user_feedback": user_feedback,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in agent_memory for learning
        self.db.store_agent_memory(
            agent_name="retrieval_feedback",
            memory_key=f"query_{query_id}",
            memory_value=json.dumps(feedback_data),
            memory_type="feedback"
        )
        
        # Update document usage statistics
        for doc_id, score in zip(doc_ids, relevance_scores):
            self._increment_usage_count(doc_id, score)
    
    def _increment_usage_count(self, doc_id: str, relevance: float) -> None:
        """Increment usage statistics for a document."""
        # Get current stats
        metadata = self.get_document_metadata(doc_id, keys=["usage_count", "avg_relevance", "last_accessed"])
        
        usage_count = int(metadata.get("usage_count", 0)) + 1
        
        # Calculate running average of relevance
        avg_relevance = float(metadata.get("avg_relevance", 0.0))
        avg_relevance = ((avg_relevance * (usage_count - 1)) + relevance) / usage_count
        
        # Update metadata
        updates = {
            "usage_count": usage_count,
            "avg_relevance": round(avg_relevance, 3),
            "last_accessed": datetime.now().isoformat()
        }
        
        for key, value in updates.items():
            self.update_document_metadata(doc_id, key, value)
    
    def get_popular_documents(
        self,
        limit: int = 10,
        classification: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently accessed documents.
        
        Args:
            limit: Number of documents to return
            classification: Filter by classification
        
        Returns:
            List of document dictionaries with usage stats
        """
        # Get all usage_count metadata
        conn = self.db._create_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT m.doc_id, m.value as usage_count, d.source, d.classification
            FROM metadata m
            JOIN documents d ON m.doc_id = d.doc_id
            WHERE m.key = 'usage_count'
        """
        
        if classification:
            query += f" AND d.classification = '{classification}'"
        
        query += " ORDER BY CAST(m.value AS INTEGER) DESC LIMIT ?"
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_learning_insights(self, agent_name: str = None) -> Dict[str, Any]:
        """
        Get aggregated learning insights from agent memory.
        
        Args:
            agent_name: Filter by specific agent
        
        Returns:
            Dictionary with learning insights
        """
        where = {}
        if agent_name:
            where["agent_name"] = agent_name
        
        memories = self.db.select("agent_memory", where=where, limit=1000)
        
        insights = {
            "total_memories": len(memories),
            "memory_by_type": {},
            "memory_by_agent": {},
            "recent_feedback": []
        }
        
        for memory in memories:
            # Count by type
            mem_type = memory.get("memory_type", "unknown")
            insights["memory_by_type"][mem_type] = insights["memory_by_type"].get(mem_type, 0) + 1
            
            # Count by agent
            agent = memory.get("agent_name", "unknown")
            insights["memory_by_agent"][agent] = insights["memory_by_agent"].get(agent, 0) + 1
            
            # Collect recent feedback
            if mem_type == "feedback":
                try:
                    feedback_data = json.loads(memory.get("memory_value", "{}"))
                    insights["recent_feedback"].append({
                        "query_id": feedback_data.get("query_id"),
                        "timestamp": feedback_data.get("timestamp"),
                        "user_feedback": feedback_data.get("user_feedback")
                    })
                except:
                    pass
        
        # Limit recent feedback
        insights["recent_feedback"] = insights["recent_feedback"][-20:]
        
        return insights
    
    def store_chunk_metadata(
        self,
        doc_id: str,
        chunk_id: int,
        chunk_metadata: Dict[str, Any]
    ) -> None:
        """
        Store metadata for individual chunks.
        
        Args:
            doc_id: Document ID
            chunk_id: Chunk index
            chunk_metadata: Chunk-specific metadata
        """
        chunk_key = f"chunk_{chunk_id}"
        
        # Store as nested metadata
        chunk_data = {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            **chunk_metadata
        }
        
        self.db.insert_with_timestamp("metadata", {
            "doc_id": doc_id,
            "key": chunk_key,
            "value": json.dumps(chunk_data)
        })
    
    def get_chunk_metadata(
        self,
        doc_id: str,
        chunk_id: int
    ) -> Dict[str, Any]:
        """Retrieve metadata for a specific chunk."""
        chunk_key = f"chunk_{chunk_id}"
        metadata = self.get_document_metadata(doc_id, keys=[chunk_key])
        return metadata.get(chunk_key, {})
    
    def enrich_retrieval_results(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich retrieval results with metadata for better agent understanding.
        
        Args:
            documents: List of retrieved documents
        
        Returns:
            Enriched documents with full metadata
        """
        enriched = []
        
        for doc in documents:
            doc_id = doc.get("doc_id")
            if not doc_id:
                enriched.append(doc)
                continue
            
            # Get all metadata
            metadata = self.get_document_metadata(doc_id)
            
            # Merge with document
            enriched_doc = {**doc, **metadata}
            
            # Add computed fields
            enriched_doc["is_popular"] = int(metadata.get("usage_count", 0)) > 10
            enriched_doc["is_reliable"] = float(metadata.get("avg_relevance", 0.0)) > 0.7
            
            enriched.append(enriched_doc)
        
        return enriched
    
    def store_agent_learning(
        self,
        agent_name: str,
        learning_type: str,
        learning_data: Dict[str, Any]
    ) -> None:
        """
        Store agent learning experiences.
        
        Args:
            agent_name: Name of the agent
            learning_type: Type of learning (pattern, optimization, error, success)
            learning_data: Learning data dictionary
        """
        memory_key = f"{learning_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.db.store_agent_memory(
            agent_name=agent_name,
            memory_key=memory_key,
            memory_value=json.dumps(learning_data),
            memory_type=learning_type
        )
    
    def get_agent_patterns(
        self,
        agent_name: str,
        pattern_type: str = "pattern"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve learned patterns for an agent.
        
        Args:
            agent_name: Agent name
            pattern_type: Type of pattern to retrieve
        
        Returns:
            List of learned patterns
        """
        memories = self.db.get_agent_memory(agent_name)
        
        patterns = []
        for memory in memories:
            if memory.get("memory_type") == pattern_type:
                try:
                    pattern_data = json.loads(memory.get("memory_value", "{}"))
                    patterns.append({
                        "memory_key": memory.get("memory_key"),
                        "created_at": memory.get("created_at"),
                        **pattern_data
                    })
                except:
                    pass
        
        return patterns
    
    def get_metadata_stats(self) -> Dict[str, Any]:
        """Get overall metadata statistics."""
        conn = self.db._create_connection()
        cursor = conn.cursor()
        
        # Count unique documents with metadata
        cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM metadata")
        docs_with_metadata = cursor.fetchone()[0]
        
        # Count metadata entries
        cursor.execute("SELECT COUNT(*) FROM metadata")
        total_metadata = cursor.fetchone()[0]
        
        # Count by key
        cursor.execute("""
            SELECT key, COUNT(*) as count 
            FROM metadata 
            GROUP BY key 
            ORDER BY count DESC 
            LIMIT 10
        """)
        top_keys = [{"key": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Agent memory stats
        cursor.execute("SELECT COUNT(*) FROM agent_memory")
        total_memories = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT agent_name, COUNT(*) as count 
            FROM agent_memory 
            GROUP BY agent_name
        """)
        memory_by_agent = [{"agent": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "documents_with_metadata": docs_with_metadata,
            "total_metadata_entries": total_metadata,
            "avg_metadata_per_doc": round(total_metadata / max(docs_with_metadata, 1), 2),
            "top_metadata_keys": top_keys,
            "total_agent_memories": total_memories,
            "memory_by_agent": memory_by_agent
        }
