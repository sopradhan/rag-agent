"""
RBAC-Aware Healing Subagent
Optimizes embeddings by reshuffling, refragmenting, and reorganizing namespaces
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime
import logging
from ..storage.sqlite_storage import RAGDatabase
from ..storage.vector_store import ChromaVectorStore


logger = logging.getLogger(__name__)


class EmbeddingShuffler:
    """
    Reshuffles embeddings across namespaces based on access patterns.
    
    Capabilities:
    - Analyze namespace distribution
    - Move documents between namespaces
    - Rebalance for optimal retrieval
    """
    
    def __init__(self, rag_db: RAGDatabase, vector_store: ChromaVectorStore):
        self.rag_db = rag_db
        self.vector_store = vector_store
    
    def get_namespace_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get distribution statistics for each namespace."""
        cursor = self.rag_db.conn.cursor()
        
        namespaces = [
            "engineering_ns", "hr_ns", "security_ns", "finance_ns",
            "general_ns", "operations_ns", "product_ns"
        ]
        
        stats = {}
        for ns in namespaces:
            # Count documents in namespace
            cursor.execute("""
                SELECT COUNT(*) as doc_count FROM documents
                WHERE namespace = ?
            """, (ns,))
            
            doc_count = cursor.fetchone()["doc_count"]
            
            # Get average classification level
            cursor.execute("""
                SELECT AVG(min_access_level) as avg_level, 
                       MAX(min_access_level) as max_level
                FROM documents
                WHERE namespace = ?
            """, (ns,))
            
            level_row = cursor.fetchone()
            avg_level = level_row["avg_level"] or 0
            max_level = level_row["max_level"] or 0
            
            stats[ns] = {
                "doc_count": doc_count,
                "avg_access_level": avg_level,
                "max_access_level": max_level
            }
        
        return stats
    
    def analyze_access_patterns(self) -> Dict[str, Dict[str, float]]:
        """Analyze which departments access which namespaces."""
        cursor = self.rag_db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                d.namespace,
                dr.department_id,
                COUNT(*) as access_count
            FROM documents d
            LEFT JOIN document_rbac dr ON d.doc_id = dr.doc_id
            GROUP BY d.namespace, dr.department_id
        """)
        
        patterns = {}
        for row in cursor.fetchall():
            ns = row["namespace"]
            dept = row["department_id"]
            count = row["access_count"]
            
            if ns not in patterns:
                patterns[ns] = {}
            
            patterns[ns][f"dept_{dept}"] = count
        
        return patterns
    
    def calculate_namespace_affinity(self, doc_id: str) -> str:
        """
        Calculate which namespace a document should belong to.
        Based on access patterns and classification.
        
        Returns:
            Recommended namespace
        """
        cursor = self.rag_db.conn.cursor()
        
        # Get document info
        cursor.execute("""
            SELECT classification, namespace FROM documents
            WHERE doc_id = ?
        """, (doc_id,))
        
        doc_row = cursor.fetchone()
        if not doc_row:
            return "general_ns"
        
        classification = doc_row["classification"]
        
        # Map classification to namespace
        classification_ns_map = {
            "technical": "engineering_ns",
            "engineering": "engineering_ns",
            "architecture": "engineering_ns",
            "api": "engineering_ns",
            "hr": "hr_ns",
            "people": "hr_ns",
            "security": "security_ns",
            "compliance": "security_ns",
            "finance": "finance_ns",
            "budget": "finance_ns",
            "operations": "operations_ns",
            "procedure": "operations_ns",
            "product": "product_ns",
            "feature": "product_ns",
            "general": "general_ns",
            "incident": "general_ns"
        }
        
        recommended = classification_ns_map.get(classification.lower() if classification else "", "general_ns")
        
        # Get current namespace
        current = doc_row["namespace"]
        
        return recommended if recommended != current else current
    
    def move_document_to_namespace(self, doc_id: str, target_namespace: str):
        """Move a document to a different namespace."""
        cursor = self.rag_db.conn.cursor()
        
        # Update document namespace
        cursor.execute("""
            UPDATE documents
            SET namespace = ?
            WHERE doc_id = ?
        """, (target_namespace, doc_id))
        
        # Log the operation
        cursor.execute("""
            INSERT INTO healing_operations
            (operation_type, doc_id, operation_details, status)
            VALUES (?, ?, ?, ?)
        """, ("namespace_move", doc_id, f"Moved to {target_namespace}", "completed"))
        
        self.rag_db.conn.commit()
        logger.info(f"Moved document {doc_id} to {target_namespace}")
    
    def rebalance_namespaces(self) -> Dict[str, Any]:
        """Rebalance documents across namespaces."""
        cursor = self.rag_db.conn.cursor()
        
        # Get all documents
        cursor.execute("SELECT doc_id FROM documents")
        doc_ids = [row["doc_id"] for row in cursor.fetchall()]
        
        rebalance_count = 0
        moved_docs = []
        
        for doc_id in doc_ids:
            recommended_ns = self.calculate_namespace_affinity(doc_id)
            
            cursor.execute("SELECT namespace FROM documents WHERE doc_id = ?", (doc_id,))
            current_ns = cursor.fetchone()["namespace"]
            
            if recommended_ns != current_ns:
                self.move_document_to_namespace(doc_id, recommended_ns)
                rebalance_count += 1
                moved_docs.append({
                    "doc_id": doc_id,
                    "from": current_ns,
                    "to": recommended_ns
                })
        
        return {
            "rebalance_count": rebalance_count,
            "moved_documents": moved_docs,
            "timestamp": datetime.now().isoformat()
        }


class EmbeddingRefragmenter:
    """
    Refragments documents for better chunk distribution.
    
    Capabilities:
    - Analyze chunk sizes
    - Split large chunks
    - Merge small chunks
    - Maintain semantic coherence
    """
    
    def __init__(self, rag_db: RAGDatabase):
        self.rag_db = rag_db
    
    def analyze_chunk_distribution(self) -> Dict[str, Any]:
        """Analyze current chunk size distribution."""
        cursor = self.rag_db.conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                AVG(LENGTH(content)) as avg_size,
                MIN(LENGTH(content)) as min_size,
                MAX(LENGTH(content)) as max_size,
                STDDEV(LENGTH(content)) as std_dev
            FROM documents
        """)
        
        row = cursor.fetchone()
        
        return {
            "total_chunks": row["total_chunks"],
            "avg_chunk_size": row["avg_size"],
            "min_chunk_size": row["min_size"],
            "max_chunk_size": row["max_size"],
            "std_deviation": row["std_dev"]
        }
    
    def identify_large_chunks(self, threshold: int = 5000) -> List[Dict[str, Any]]:
        """Identify chunks larger than threshold."""
        cursor = self.rag_db.conn.cursor()
        
        cursor.execute("""
            SELECT doc_id, source, LENGTH(content) as content_size
            FROM documents
            WHERE LENGTH(content) > ?
            ORDER BY content_size DESC
        """, (threshold,))
        
        return [
            {
                "doc_id": row["doc_id"],
                "source": row["source"],
                "size": row["content_size"]
            }
            for row in cursor.fetchall()
        ]
    
    def identify_small_chunks(self, threshold: int = 200) -> List[Dict[str, Any]]:
        """Identify chunks smaller than threshold."""
        cursor = self.rag_db.conn.cursor()
        
        cursor.execute("""
            SELECT doc_id, source, LENGTH(content) as content_size
            FROM documents
            WHERE LENGTH(content) < ? AND LENGTH(content) > 0
            ORDER BY content_size ASC
        """, (threshold,))
        
        return [
            {
                "doc_id": row["doc_id"],
                "source": row["source"],
                "size": row["content_size"]
            }
            for row in cursor.fetchall()
        ]
    
    def recommend_refragmentation(self) -> Dict[str, Any]:
        """Generate refragmentation recommendations."""
        large = self.identify_large_chunks()
        small = self.identify_small_chunks()
        dist = self.analyze_chunk_distribution()
        
        return {
            "chunk_analysis": dist,
            "large_chunks": large,
            "small_chunks": small,
            "total_candidates_for_refragmentation": len(large) + len(small),
            "recommendation": {
                "should_split": len(large) > len(small),
                "should_merge": len(small) > len(large) * 2,
                "target_avg_size": 2000 if dist["avg_chunk_size"] > 5000 else 1500
            }
        }
    
    def split_document(self, doc_id: str, chunk_size: int = 2000) -> List[str]:
        """
        Split a large document into smaller chunks.
        
        Returns:
            List of new doc_ids created
        """
        cursor = self.rag_db.conn.cursor()
        
        # Get document
        cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
        doc = cursor.fetchone()
        if not doc:
            return []
        
        content = doc["content"]
        new_doc_ids = []
        
        # Split by sentences if possible
        sentences = content.split(". ")
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Insert new chunks
        import uuid
        for i, chunk in enumerate(chunks):
            new_id = str(uuid.uuid4())
            self.rag_db.insert_document(
                doc_id=new_id,
                content=chunk,
                source=f"{doc['source']} [part {i+1}/{len(chunks)}]",
                namespace=doc["namespace"],
                classification=doc["classification"]
            )
            new_doc_ids.append(new_id)
        
        # Mark original as fragmented
        cursor.execute("""
            INSERT INTO healing_operations
            (operation_type, doc_id, operation_details, status)
            VALUES (?, ?, ?, ?)
        """, ("document_split", doc_id, f"Split into {len(chunks)} chunks", "completed"))
        
        self.rag_db.conn.commit()
        logger.info(f"Split document {doc_id} into {len(chunks)} chunks")
        
        return new_doc_ids


class RBACHealingSubagent:
    """
    Master healing subagent orchestrating all optimization operations.
    """
    
    def __init__(self, rag_db: RAGDatabase, vector_store: ChromaVectorStore):
        self.rag_db = rag_db
        self.vector_store = vector_store
        self.shuffler = EmbeddingShuffler(rag_db, vector_store)
        self.refragmenter = EmbeddingRefragmenter(rag_db)
    
    def run_full_healing(self) -> Dict[str, Any]:
        """
        Run complete healing pipeline:
        1. Analyze namespace distribution
        2. Rebalance documents across namespaces
        3. Analyze chunk distribution
        4. Recommend refragmentation
        5. Generate optimization report
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "operations": {}
        }
        
        # Step 1: Namespace analysis
        logger.info("Starting RBAC healing process...")
        ns_stats = self.shuffler.get_namespace_statistics()
        results["operations"]["namespace_analysis"] = ns_stats
        
        # Step 2: Rebalance
        logger.info("Rebalancing namespaces...")
        rebalance = self.shuffler.rebalance_namespaces()
        results["operations"]["rebalance"] = rebalance
        
        # Step 3: Access pattern analysis
        logger.info("Analyzing access patterns...")
        patterns = self.shuffler.analyze_access_patterns()
        results["operations"]["access_patterns"] = patterns
        
        # Step 4: Chunk analysis
        logger.info("Analyzing chunk distribution...")
        chunk_dist = self.refragmenter.analyze_chunk_distribution()
        results["operations"]["chunk_distribution"] = chunk_dist
        
        # Step 5: Refragmentation recommendations
        logger.info("Generating refragmentation recommendations...")
        refrag_rec = self.refragmenter.recommend_refragmentation()
        results["operations"]["refragmentation_recommendations"] = refrag_rec
        
        results["status"] = "completed"
        logger.info("RBAC healing process completed")
        
        return results
    
    def run_namespace_optimization(self) -> Dict[str, Any]:
        """Run only namespace optimization."""
        logger.info("Running namespace optimization...")
        
        ns_stats = self.shuffler.get_namespace_statistics()
        rebalance = self.shuffler.rebalance_namespaces()
        patterns = self.shuffler.analyze_access_patterns()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "namespace_stats": ns_stats,
            "rebalance_results": rebalance,
            "access_patterns": patterns,
            "status": "completed"
        }
    
    def run_chunk_optimization(self) -> Dict[str, Any]:
        """Run only chunk optimization."""
        logger.info("Running chunk optimization...")
        
        analysis = self.refragmenter.analyze_chunk_distribution()
        large = self.refragmenter.identify_large_chunks()
        small = self.refragmenter.identify_small_chunks()
        recommendations = self.refragmenter.recommend_refragmentation()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "chunk_analysis": analysis,
            "large_chunks": large,
            "small_chunks": small,
            "recommendations": recommendations,
            "status": "completed"
        }
    
    def apply_refragmentation(self, auto_split_threshold: int = 5000) -> Dict[str, Any]:
        """Apply automatic refragmentation to large chunks."""
        logger.info(f"Applying refragmentation (threshold: {auto_split_threshold})...")
        
        large_chunks = self.refragmenter.identify_large_chunks(auto_split_threshold)
        split_operations = []
        
        for chunk_info in large_chunks:
            new_ids = self.refragmenter.split_document(
                chunk_info["doc_id"],
                chunk_size=auto_split_threshold // 2
            )
            split_operations.append({
                "original_doc_id": chunk_info["doc_id"],
                "new_doc_ids": new_ids,
                "original_size": chunk_info["size"]
            })
        
        logger.info(f"Split {len(split_operations)} documents")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "split_operations": split_operations,
            "total_split": len(split_operations),
            "status": "completed"
        }
    
    def get_healing_status(self) -> Dict[str, Any]:
        """Get current system health status."""
        cursor = self.rag_db.conn.cursor()
        
        # Count healing operations
        cursor.execute("""
            SELECT operation_type, COUNT(*) as count
            FROM healing_operations
            GROUP BY operation_type
        """)
        
        operations = {row["operation_type"]: row["count"] for row in cursor.fetchall()}
        
        # Namespace stats
        ns_stats = self.shuffler.get_namespace_statistics()
        
        # Chunk stats
        chunk_stats = self.refragmenter.analyze_chunk_distribution()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "healing_operations": operations,
            "namespace_statistics": ns_stats,
            "chunk_statistics": chunk_stats,
            "system_health": "optimal" if chunk_stats["std_deviation"] < 3000 else "needs_optimization"
        }
