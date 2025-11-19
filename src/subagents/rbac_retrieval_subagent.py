"""
RBAC-Aware Retrieval Subagents with Tag Management
Retrieves documents with proper RBAC filtering and tag association
"""

from typing import List, Dict, Any, Optional
from ..storage.sqlite_storage import RAGDatabase
from ..storage.vector_store import ChromaVectorStore


class RBACFilteringSubagent:
    """
    Filters search results based on user's RBAC permissions.
    
    Capabilities:
    - Query user's company, department, role
    - Filter documents by access level
    - Enforce departmental boundaries
    - Include/exclude based on classification
    """
    
    def __init__(self, rag_db: RAGDatabase):
        self.rag_db = rag_db
    
    def get_user_rbac_context(self, user_id: int) -> Dict[str, Any]:
        """Get RBAC context for a user."""
        cursor = self.rag_db.conn.cursor()
        
        cursor.execute("""
            SELECT u.user_id, u.company_id, u.department_id, u.role_id,
                   c.name as company_name, d.name as department_name, r.role_name,
                   r.grade
            FROM users u
            JOIN company c ON u.company_id = c.company_id
            JOIN department d ON u.department_id = d.department_id
            JOIN role r ON u.role_id = r.role_id
            WHERE u.user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        # Calculate access level from role grade
        grade_levels = {
            "intern": 1,
            "junior": 2,
            "senior": 3,
            "lead": 4,
            "manager": 4,
            "director": 5,
            "executive": 5
        }
        
        access_level = grade_levels.get(row["grade"].lower() if row["grade"] else "", 1)
        
        return {
            "user_id": row["user_id"],
            "company_id": row["company_id"],
            "department_id": row["department_id"],
            "role_id": row["role_id"],
            "company_name": row["company_name"],
            "department_name": row["department_name"],
            "role_name": row["role_name"],
            "access_level": access_level
        }
    
    def filter_by_rbac(self, doc_ids: List[str], user_rbac: Dict[str, Any]) -> List[str]:
        """
        Filter documents the user can access.
        
        Args:
            doc_ids: Document IDs from search
            user_rbac: User's RBAC context
        
        Returns:
            Filtered list of accessible doc_ids
        """
        if not user_rbac:
            return []
        
        cursor = self.rag_db.conn.cursor()
        accessible_docs = []
        
        for doc_id in doc_ids:
            # Check document classification
            cursor.execute("""
                SELECT d.min_access_level, d.classification
                FROM documents d
                WHERE d.doc_id = ?
            """, (doc_id,))
            
            doc_row = cursor.fetchone()
            if not doc_row:
                continue
            
            min_access = doc_row["min_access_level"] or 1
            classification = doc_row["classification"]
            
            # Check access level
            if user_rbac["access_level"] < min_access:
                continue
            
            # Check RBAC mapping
            cursor.execute("""
                SELECT 1 FROM document_rbac
                WHERE doc_id = ? AND department_id = ?
            """, (doc_id, user_rbac["department_id"]))
            
            if cursor.fetchone():
                accessible_docs.append(doc_id)
        
        return accessible_docs
    
    def get_document_rbac_info(self, doc_id: str) -> Dict[str, Any]:
        """Get RBAC information for a document."""
        cursor = self.rag_db.conn.cursor()
        
        cursor.execute("""
            SELECT d.doc_id, d.classification, d.min_access_level,
                   GROUP_CONCAT(r.department_id, ',') as allowed_departments
            FROM documents d
            LEFT JOIN document_rbac r ON d.doc_id = r.doc_id
            WHERE d.doc_id = ?
            GROUP BY d.doc_id
        """, (doc_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "doc_id": row["doc_id"],
            "classification": row["classification"],
            "min_access_level": row["min_access_level"],
            "allowed_departments": [int(x) for x in row["allowed_departments"].split(",") if x]
        }


class TagRetrievalSubagent:
    """
    Retrieves documents with associated tags.
    
    Capabilities:
    - Extract tags from metadata
    - Search by tags
    - Tag-based faceted search
    - Tag suggestions based on search
    """
    
    def __init__(self, rag_db: RAGDatabase):
        self.rag_db = rag_db
    
    def get_document_tags(self, doc_id: str) -> List[str]:
        """Get all tags associated with a document."""
        cursor = self.rag_db.conn.cursor()
        
        cursor.execute("""
            SELECT value FROM metadata
            WHERE doc_id = ? AND key = 'tag'
            ORDER BY value
        """, (doc_id,))
        
        return [row["value"] for row in cursor.fetchall()]
    
    def search_by_tags(self, tags: List[str], match_all: bool = False) -> List[str]:
        """
        Search documents by tags.
        
        Args:
            tags: List of tags to search for
            match_all: If True, document must have ALL tags. If False, ANY tag.
        
        Returns:
            List of matching doc_ids
        """
        cursor = self.rag_db.conn.cursor()
        
        if match_all:
            # Document must have ALL specified tags
            placeholders = ','.join(['?' for _ in tags])
            cursor.execute(f"""
                SELECT doc_id FROM metadata
                WHERE key = 'tag' AND value IN ({placeholders})
                GROUP BY doc_id
                HAVING COUNT(DISTINCT value) = ?
            """, tags + [len(tags)])
        else:
            # Document must have ANY of the tags
            placeholders = ','.join(['?' for _ in tags])
            cursor.execute(f"""
                SELECT DISTINCT doc_id FROM metadata
                WHERE key = 'tag' AND value IN ({placeholders})
            """, tags)
        
        return [row["doc_id"] for row in cursor.fetchall()]
    
    def get_tag_suggestions(self, search_query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get tag suggestions based on search context.
        
        Args:
            search_query: Search query text
            limit: Number of suggestions
        
        Returns:
            List of tags with frequency
        """
        cursor = self.rag_db.conn.cursor()
        
        # Find documents matching query words
        cursor.execute("""
            SELECT DISTINCT d.doc_id FROM documents d
            WHERE d.content LIKE ? OR d.source LIKE ?
            LIMIT 100
        """, (f"%{search_query}%", f"%{search_query}%"))
        
        doc_ids = [row["doc_id"] for row in cursor.fetchall()]
        
        if not doc_ids:
            return []
        
        # Get top tags from matching documents
        placeholders = ','.join(['?' for _ in doc_ids])
        cursor.execute(f"""
            SELECT value, COUNT(*) as frequency
            FROM metadata
            WHERE doc_id IN ({placeholders}) AND key = 'tag'
            GROUP BY value
            ORDER BY frequency DESC
            LIMIT ?
        """, doc_ids + [limit])
        
        return [{"tag": row["value"], "frequency": row["frequency"]} for row in cursor.fetchall()]
    
    def add_tag_to_document(self, doc_id: str, tag: str):
        """Add a tag to a document."""
        self.rag_db.insert_metadata(doc_id, "tag", tag)
    
    def remove_tag_from_document(self, doc_id: str, tag: str):
        """Remove a tag from a document."""
        cursor = self.rag_db.conn.cursor()
        cursor.execute("""
            DELETE FROM metadata
            WHERE doc_id = ? AND key = 'tag' AND value = ?
        """, (doc_id, tag))
        self.rag_db.conn.commit()


class RBACSearchSubagent:
    """
    Combines RBAC filtering and tag retrieval for comprehensive search.
    """
    
    def __init__(self, rag_db: RAGDatabase, vector_store: ChromaVectorStore):
        self.rag_db = rag_db
        self.vector_store = vector_store
        self.rbac_filter = RBACFilteringSubagent(rag_db)
        self.tag_retriever = TagRetrievalSubagent(rag_db)
    
    def search_with_rbac_and_tags(
        self,
        query: str,
        user_id: int,
        top_k: int = 10,
        tags_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search with RBAC enforcement and tag association.
        
        Args:
            query: Search query
            user_id: User performing search
            top_k: Number of results
            tags_filter: Optional tags to filter by
        
        Returns:
            List of documents with tags and RBAC info
        """
        # 1. Get user RBAC context
        user_rbac = self.rbac_filter.get_user_rbac_context(user_id)
        if not user_rbac:
            return []
        
        # 2. Search in ChromaDB
        results = self.vector_store.search(query, top_k=top_k * 2)  # Get extra for filtering
        
        # 3. Apply RBAC filter
        accessible_doc_ids = self.rbac_filter.filter_by_rbac(
            [doc_id for doc_id, _ in results],
            user_rbac
        )
        
        # 4. Apply tag filter if specified
        if tags_filter:
            tagged_docs = self.tag_retriever.search_by_tags(tags_filter, match_all=False)
            accessible_doc_ids = [d for d in accessible_doc_ids if d in tagged_docs]
        
        # 5. Enrich results with tags and metadata
        enriched_results = []
        for doc_id in accessible_doc_ids[:top_k]:
            # Find similarity score
            score = next((s for d, s in results if d == doc_id), 0)
            
            # Get document
            doc = self.rag_db.get_document(doc_id)
            if not doc:
                continue
            
            # Get tags
            tags = self.tag_retriever.get_document_tags(doc_id)
            
            # Get RBAC info
            rbac_info = self.rbac_filter.get_document_rbac_info(doc_id)
            
            enriched_results.append({
                "doc_id": doc_id,
                "content": doc["content"],
                "source": doc["source"],
                "classification": doc["classification"],
                "similarity_score": score,
                "tags": tags,
                "min_access_level": rbac_info["min_access_level"] if rbac_info else 1,
                "user_access_level": user_rbac["access_level"]
            })
        
        return enriched_results
