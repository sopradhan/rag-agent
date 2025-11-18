"""
Healing Subagents
Handles system monitoring, analysis, and optimization.
Includes history fetching, metadata search, and embedding reshuffling.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from ..agents.deep_agent import DeepAgent
from ..abstraction import LLMManager
from ..storage import RAGDatabase


class HeatmapAnalyzerSubagent(DeepAgent):
    """Analyzes system usage patterns and identifies issues."""
    
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        db: Optional[RAGDatabase] = None
    ):
        super().__init__(name=name, config=config, memory_backend="persistent")
        self.metrics = config.get("metrics", [])
        self.db = db or RAGDatabase()
    
    def _execute(self, time_range: str = "24h") -> Dict[str, Any]:
        """Analyze system metrics and generate heatmap."""
        # Parse time range
        hours = int(time_range.rstrip('h'))
        
        # Collect metrics from database
        analysis = {
            "time_range": time_range,
            "timestamp": datetime.now().isoformat(),
            "issues": []
        }
        
        # Analyze query history
        if "query_frequency" in self.metrics:
            query_analysis = self._analyze_query_history(hours)
            if query_analysis["issues"]:
                analysis["issues"].extend(query_analysis["issues"])
        
        # Analyze retrieval accuracy
        if "retrieval_accuracy" in self.metrics:
            accuracy_analysis = self._analyze_retrieval_accuracy(hours)
            if accuracy_analysis["issues"]:
                analysis["issues"].extend(accuracy_analysis["issues"])
        
        # Analyze response time
        if "response_time" in self.metrics:
            response_analysis = self._analyze_response_time(hours)
            if response_analysis["issues"]:
                analysis["issues"].extend(response_analysis["issues"])
        
        # Check for stale embeddings
        stale_docs = self.db.get_documents_for_reembedding()
        if stale_docs:
            analysis["issues"].append({
                "type": "stale_embeddings",
                "description": f"{len(stale_docs)} documents have stale or missing embeddings",
                "severity": "medium",
                "affected_documents": [doc["doc_id"] for doc in stale_docs[:10]]
            })
        
        self.memory.add({
            "type": "heatmap_analysis",
            "time_range": time_range,
            "issues_found": len(analysis["issues"])
        })
        
        return analysis
    
    def _analyze_query_history(self, hours: int) -> Dict[str, Any]:
        """Analyze query patterns from history."""
        queries = self.db.get_query_history(limit=1000)
        
        if not queries:
            return {"metric": "query_frequency", "issues": []}
        
        # Calculate success rate
        successful = sum(1 for q in queries if q.get("success"))
        success_rate = (successful / len(queries)) * 100 if queries else 100
        
        issues = []
        if success_rate < 70:
            issues.append({
                "type": "low_success_rate",
                "description": f"Query success rate is {success_rate:.1f}%",
                "severity": "high",
                "metric_value": success_rate
            })
        
        return {"metric": "query_frequency", "issues": issues}
    
    def _analyze_retrieval_accuracy(self, hours: int) -> Dict[str, Any]:
        """Analyze retrieval accuracy from query history."""
        queries = self.db.get_query_history(limit=500)
        
        issues = []
        
        # Check for queries with no documents retrieved
        no_results = [q for q in queries if q.get("documents_retrieved", 0) == 0]
        if len(no_results) > len(queries) * 0.2:  # More than 20% queries with no results
            issues.append({
                "type": "low_retrieval",
                "description": f"{len(no_results)} queries returned no results",
                "severity": "high",
                "affected_queries": [q["query"] for q in no_results[:5]]
            })
        
        return {"metric": "retrieval_accuracy", "issues": issues}
    
    def _analyze_response_time(self, hours: int) -> Dict[str, Any]:
        """Analyze response time performance."""
        queries = self.db.get_query_history(limit=500)
        
        if not queries:
            return {"metric": "response_time", "issues": []}
        
        # Calculate average response time
        avg_time = sum(q.get("response_time", 0) for q in queries) / len(queries)
        
        issues = []
        if avg_time > 5.0:  # Over 5 seconds
            issues.append({
                "type": "slow_retrieval",
                "description": f"Average response time is {avg_time:.2f}s",
                "severity": "medium",
                "metric_value": avg_time
            })
        
        return {"metric": "response_time", "issues": issues}


class OptimizationSubagent(DeepAgent):
    """Optimizes system based on identified issues with history-aware reshuffling."""
    
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        llm_manager: Optional[LLMManager] = None,
        db: Optional[RAGDatabase] = None
    ):
        super().__init__(name=name, config=config, memory_backend="persistent")
        self.llm_manager = llm_manager
        self.db = db or RAGDatabase()
        self.strategies = config.get("strategies", [])
    
    def _execute(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize system based on issues."""
        if not issues:
            return {
                "optimizations": [],
                "message": "No issues to optimize"
            }
        
        optimizations = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "low_accuracy" and "reindex_low_quality" in self.strategies:
                opt = self._optimize_low_accuracy(issue)
                optimizations.append(opt)
            
            elif issue_type == "slow_retrieval" and "adjust_chunk_size" in self.strategies:
                opt = self._optimize_chunk_size(issue)
                optimizations.append(opt)
            
            elif issue_type == "stale_embeddings" and "reshuffle_embeddings" in self.strategies:
                opt = self._reshuffle_stale_embeddings(issue)
                optimizations.append(opt)
            
            elif issue_type == "low_retrieval" and "improve_metadata" in self.strategies:
                opt = self._improve_metadata_tags(issue)
                optimizations.append(opt)
            
            elif "add_synthetic_questions" in self.strategies:
                opt = self._add_synthetic_questions(issue)
                optimizations.append(opt)
        
        self.memory.add({
            "type": "optimization_complete",
            "issues_processed": len(issues),
            "optimizations_applied": len(optimizations)
        })
        
        return {
            "optimizations": optimizations,
            "timestamp": datetime.now().isoformat()
        }
    
    def _reshuffle_stale_embeddings(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Re-generate embeddings for stale documents using history analysis."""
        affected_doc_ids = issue.get("affected_documents", [])
        
        reshuffled_count = 0
        failed_docs = []
        
        for doc_id in affected_doc_ids:
            try:
                # Fetch document
                doc = self.db.get_document(doc_id)
                if not doc:
                    failed_docs.append(doc_id)
                    continue
                
                # Fetch metadata for context
                metadata = self.db.get_metadata(doc_id)
                
                # Generate new embedding with LLM
                if self.llm_manager:
                    content = doc["content"]
                    # Optionally enhance with metadata
                    enhanced_content = f"{content}\n\nMetadata: {metadata}"
                    new_embedding = self.llm_manager.embed(enhanced_content)
                    
                    # Store new embedding
                    self.db.insert_embedding(doc_id, new_embedding, "reshuffled")
                    reshuffled_count += 1
                    
                    print(f"[OptimizationSubagent] Re-embedded document: {doc_id}")
                
            except Exception as e:
                print(f"[OptimizationSubagent] Failed to reshuffle {doc_id}: {e}")
                failed_docs.append(doc_id)
        
        return {
            "strategy": "reshuffle_embeddings",
            "issue": issue["type"],
            "action": f"Re-embedded {reshuffled_count} documents",
            "status": "completed",
            "reshuffled_count": reshuffled_count,
            "failed_docs": failed_docs
        }
    
    def _improve_metadata_tags(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Improve metadata tags based on query patterns."""
        # Fetch queries that had low retrieval
        failed_queries = issue.get("affected_queries", [])
        
        improvements = []
        
        for query in failed_queries[:10]:  # Process top 10
            # Search documents by content similarity
            docs = self.db.search_documents_by_metadata("keywords", query)
            
            if docs and self.llm_manager:
                # Generate additional metadata tags
                for doc in docs[:5]:
                    try:
                        # Use LLM to generate better tags
                        prompt = f"Generate relevant metadata tags for this document based on the query '{query}':\n\n{doc['content'][:500]}"
                        response = self.llm_manager.generate(prompt)
                        
                        # Store new metadata
                        self.db.insert_metadata(doc["doc_id"], "enhanced_tags", response)
                        improvements.append(doc["doc_id"])
                        
                    except Exception as e:
                        print(f"[OptimizationSubagent] Failed to improve metadata for {doc['doc_id']}: {e}")
        
        return {
            "strategy": "improve_metadata",
            "issue": issue["type"],
            "action": f"Enhanced metadata for {len(improvements)} documents",
            "status": "completed",
            "improved_docs": len(improvements)
        }
    
    def fetch_operation_history(self, operation_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all previous operation history for analysis."""
        return self.db.get_operation_history(limit=limit, operation_type=operation_type)
    
    def fetch_healing_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch previous healing operations to avoid repeating ineffective strategies."""
        return self.db.get_healing_history(limit=limit)
    
    def search_by_meta_tags(self, tag_key: str, tag_value: str) -> List[Dict[str, Any]]:
        """Search documents by metadata tags for targeted optimization."""
        return self.db.search_documents_by_metadata(tag_key, tag_value)
    
    def _execute(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize system based on issues."""
        if not issues:
            return {
                "optimizations": [],
                "message": "No issues to optimize"
            }
        
        optimizations = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "low_accuracy" and "reindex_low_quality" in self.strategies:
                opt = self._optimize_low_accuracy(issue)
                optimizations.append(opt)
            
            elif issue_type == "slow_retrieval" and "adjust_chunk_size" in self.strategies:
                opt = self._optimize_chunk_size(issue)
                optimizations.append(opt)
            
            elif "add_synthetic_questions" in self.strategies:
                opt = self._add_synthetic_questions(issue)
                optimizations.append(opt)
        
        self.memory.add({
            "type": "optimization_complete",
            "issues_processed": len(issues),
            "optimizations_applied": len(optimizations)
        })
        
        return {
            "optimizations": optimizations,
            "timestamp": datetime.now().isoformat()
        }
    
    def _optimize_low_accuracy(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize documents with low retrieval accuracy."""
        return {
            "strategy": "reindex_low_quality",
            "issue": issue["type"],
            "action": "Re-chunking and re-embedding affected documents",
            "status": "planned"
        }
    
    def _optimize_chunk_size(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize chunk size based on performance."""
        return {
            "strategy": "adjust_chunk_size",
            "issue": issue["type"],
            "action": "Adjusting chunk size from 1000 to 800 characters",
            "status": "planned"
        }
    
    def _add_synthetic_questions(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Generate synthetic questions to improve retrieval."""
        if not self.llm_manager:
            return {
                "strategy": "add_synthetic_questions",
                "issue": issue["type"],
                "action": "Skipped - no LLM manager available",
                "status": "skipped"
            }
        
        # Generate synthetic questions for documents
        return {
            "strategy": "add_synthetic_questions",
            "issue": issue["type"],
            "action": "Generating synthetic questions for low-performing documents",
            "status": "planned",
            "estimated_questions": 50
        }
