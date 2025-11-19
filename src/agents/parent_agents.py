"""
Parent Agents
Orchestrates subagents for ingestion, retrieval, and healing.
"""

from typing import List, Dict, Any, Optional
import yaml
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..agents.deep_agent import DeepAgent
from ..abstraction import (
    Document, DataSourceManager, LLMManager, RBACManager
)
from ..subagents import (
    ChunkerSubagent, MetadataSubagent, RBACSubagent, EmbeddingSubagent,
    PermissionCheckerSubagent, GraphExpansionSubagent, AnswerSynthesisSubagent,
    HeatmapAnalyzerSubagent, OptimizationSubagent,
    # New RBAC-aware subagents for intelligent ingestion, retrieval, and healing
    RBACIntelligentIngestionSubagent,
    RBACSearchSubagent,
    RBACHealingSubagent
)
from ..storage import RAGDatabase, ChromaVectorStore


class IngestionAgent(DeepAgent):
    """Parent agent for document ingestion pipeline with RBAC support."""
    
    def __init__(
        self,
        config_path: str = "config/agent_config.yaml",
        llm_manager: Optional[LLMManager] = None,
        rbac_manager: Optional[RBACManager] = None,
        use_intelligent_rbac: bool = False
    ):
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        agent_config = config["ingestion_agent"]
        super().__init__(
            name=agent_config["name"],
            memory_backend=agent_config["memory_backend"],
            config=agent_config
        )
        
        self.llm_manager = llm_manager or LLMManager()
        self.rbac_manager = rbac_manager or RBACManager()
        self.parallel_processing = agent_config.get("parallel_processing", True)
        self.max_workers = agent_config.get("max_workers", 4)
        self.use_intelligent_rbac = use_intelligent_rbac
        
        # Initialize storage for intelligent RBAC ingestion
        if self.use_intelligent_rbac:
            self.rag_db = RAGDatabase()
            self.vector_store = ChromaVectorStore()
            self.intelligent_ingestion = RBACIntelligentIngestionSubagent(
                self.rag_db, self.vector_store, self.llm_manager
            )
            print(f"[{self.name}] Intelligent RBAC ingestion enabled")
        
        # Initialize subagents
        subagent_configs = agent_config["subagents"]
        
        self.chunker = ChunkerSubagent(
            name=subagent_configs["chunker"]["name"],
            config=subagent_configs["chunker"]
        )
        
        self.metadata_extractor = MetadataSubagent(
            name=subagent_configs["metadata"]["name"],
            config=subagent_configs["metadata"],
            llm_manager=self.llm_manager
        )
        
        self.rbac_classifier = RBACSubagent(
            name=subagent_configs["rbac"]["name"],
            config=subagent_configs["rbac"],
            rbac_manager=self.rbac_manager
        )
        
        self.embedder = EmbeddingSubagent(
            name=subagent_configs["embedding"]["name"],
            config=subagent_configs["embedding"],
            llm_manager=self.llm_manager
        )
    
    def _execute(self, documents: List[Document]) -> List[Document]:
        """Execute ingestion pipeline with optional intelligent RBAC."""
        print(f"[{self.name}] Starting ingestion of {len(documents)} documents")
        
        if self.use_intelligent_rbac:
            # Use intelligent RBAC-aware ingestion
            print(f"[{self.name}] Using intelligent RBAC ingestion pipeline...")
            return self._execute_intelligent(documents)
        else:
            # Use traditional ingestion pipeline
            return self._execute_traditional(documents)
    
    def execute(self, documents: List[Document]) -> List[Document]:
        """Public execute method - delegates to _execute."""
        return self._execute(documents)
    
    def _execute_traditional(self, documents: List[Document]) -> List[Document]:
        """Execute traditional ingestion pipeline."""
        # Step 1: Chunk documents
        print(f"[{self.name}] Step 1: Chunking documents...")
        chunked_docs = self.chunker.run(documents)
        print(f"[{self.name}] Created {len(chunked_docs)} chunks")
        
        # Step 2: Extract metadata
        print(f"[{self.name}] Step 2: Extracting metadata...")
        docs_with_metadata = self.metadata_extractor.run(chunked_docs)
        
        # Step 3: Apply RBAC classification
        print(f"[{self.name}] Step 3: Applying RBAC classification...")
        classified_docs = self.rbac_classifier.run(docs_with_metadata)
        
        # Step 4: Generate embeddings
        print(f"[{self.name}] Step 4: Generating embeddings...")
        if self.parallel_processing and len(classified_docs) > 10:
            final_docs = self._parallel_embed(classified_docs)
        else:
            final_docs = self.embedder.run(classified_docs)
        
        print(f"[{self.name}] Ingestion complete: {len(final_docs)} documents ready")
        
        return final_docs
    
    def _execute_intelligent(self, documents: List[Document]) -> List[Document]:
        """Execute intelligent RBAC-aware ingestion pipeline."""
        # Convert documents to paths for intelligent ingestion
        doc_paths = []
        for doc in documents:
            if hasattr(doc, 'path') and doc.path:
                doc_paths.append(doc.path)
        
        if not doc_paths:
            print(f"[{self.name}] Warning: No document paths available, using traditional pipeline")
            return self._execute_traditional(documents)
        
        print(f"[{self.name}] Processing {len(doc_paths)} documents with LLM context analysis...")
        
        ingested_count = 0
        for doc_path in doc_paths:
            try:
                result = self.intelligent_ingestion.ingest_with_rbac(
                    document_path=doc_path,
                    doc_type="general"
                )
                ingested_count += 1
                print(f"[{self.name}] ✓ {doc_path}: {result}")
            except Exception as e:
                print(f"[{self.name}] ✗ Failed to ingest {doc_path}: {e}")
        
        print(f"[{self.name}] Intelligent ingestion complete: {ingested_count}/{len(doc_paths)} documents")
        return documents
    
    def _parallel_embed(self, documents: List[Document]) -> List[Document]:
        """Parallel embedding generation."""
        batch_size = len(documents) // self.max_workers + 1
        batches = [
            documents[i:i + batch_size]
            for i in range(0, len(documents), batch_size)
        ]
        
        all_results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.embedder.run, batch): batch
                for batch in batches
            }
            
            for future in as_completed(futures):
                result = future.result()
                all_results.extend(result)
        
        return all_results


class RetrievalAgent(DeepAgent):
    """Parent agent for document retrieval with intelligent RBAC filtering."""
    
    def __init__(
        self,
        config_path: str = "config/agent_config.yaml",
        llm_manager: Optional[LLMManager] = None,
        rbac_manager: Optional[RBACManager] = None,
        vector_store: Optional[Any] = None,
        graph_store: Optional[Any] = None,
        use_intelligent_rbac: bool = False
    ):
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        agent_config = config["retrieval_agent"]
        super().__init__(
            name=agent_config["name"],
            memory_backend=agent_config["memory_backend"],
            config=agent_config
        )
        
        self.llm_manager = llm_manager or LLMManager()
        self.rbac_manager = rbac_manager or RBACManager()
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.use_intelligent_rbac = use_intelligent_rbac
        
        self.top_k = agent_config.get("top_k", 5)
        self.similarity_threshold = agent_config.get("similarity_threshold", 0.7)
        
        # Initialize storage and intelligent RBAC search if enabled
        if self.use_intelligent_rbac:
            self.rag_db = RAGDatabase()
            if not self.vector_store:
                self.vector_store = ChromaVectorStore()
            self.rbac_search = RBACSearchSubagent(
                self.rag_db, self.vector_store
            )
            print(f"[{self.name}] Intelligent RBAC search enabled")
        
        # Initialize subagents
        subagent_configs = agent_config["subagents"]
        
        self.permission_checker = PermissionCheckerSubagent(
            name=subagent_configs["permission_checker"]["name"],
            config=subagent_configs["permission_checker"],
            rbac_manager=self.rbac_manager
        )
        
        self.graph_expander = GraphExpansionSubagent(
            name=subagent_configs["graph_expansion"]["name"],
            config=subagent_configs["graph_expansion"]
        )
        
        self.synthesizer = AnswerSynthesisSubagent(
            name=subagent_configs["answer_synthesis"]["name"],
            config=subagent_configs["answer_synthesis"],
            llm_manager=self.llm_manager
        )
    
    def _execute(self, query: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Execute retrieval pipeline with optional intelligent RBAC."""
        print(f"[{self.name}] Processing query: {query}")
        
        if self.use_intelligent_rbac:
            return self._execute_intelligent(query, user)
        else:
            return self._execute_traditional(query, user)
    
    def execute(self, query: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Public execute method - delegates to _execute."""
        return self._execute(query, user)
    
    def _execute_intelligent(self, query: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Execute intelligent RBAC-aware retrieval pipeline."""
        print(f"[{self.name}] Using intelligent RBAC search...")
        
        user_id = user.get("id", 1)
        top_k = user.get("top_k", self.top_k)
        tags_filter = user.get("tags_filter", None)
        
        try:
            # Search with RBAC and tags
            results = self.rbac_search.search_with_rbac_and_tags(
                query=query,
                user_id=user_id,
                top_k=top_k,
                tags_filter=tags_filter
            )
            
            if not results:
                return {
                    "query": query,
                    "answer": "No documents found that match your query and access permissions.",
                    "sources": [],
                    "documents_used": 0
                }
            
            # Prepare context from results
            context = "\n---\n".join([
                f"[{r['source']}] {r['content'][:500]}" 
                for r in results[:3]
            ])
            
            # Synthesize answer using context
            answer = self._synthesize_answer(query, context, results)
            
            return {
                "query": query,
                "answer": answer,
                "sources": [r["source"] for r in results],
                "documents_used": len(results),
                "tags": [tag for r in results for tag in r["tags"]]
            }
        
        except Exception as e:
            print(f"[{self.name}] Error in intelligent search: {e}")
            return {
                "query": query,
                "answer": f"Error processing query: {str(e)}",
                "sources": [],
                "documents_used": 0
            }
    
    def _execute_traditional(self, query: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Execute traditional retrieval pipeline."""
        # Step 1: Check permissions
        print(f"[{self.name}] Step 1: Checking permissions...")
        permission_result = self.permission_checker.run(query, user)
        user_obj = permission_result["user"]
        
        # Step 2: Vector search
        print(f"[{self.name}] Step 2: Performing vector search...")
        candidate_docs = self._vector_search(query)
        print(f"[{self.name}] Found {len(candidate_docs)} candidate documents")
        
        # Step 3: Filter by permissions
        print(f"[{self.name}] Step 3: Filtering by permissions...")
        accessible_docs = self.rbac_manager.filter_documents_by_access(
            user_obj, candidate_docs, operation="read"
        )
        print(f"[{self.name}] User has access to {len(accessible_docs)} documents")
        
        if not accessible_docs:
            return {
                "query": query,
                "answer": "I don't have access to any documents that can answer your question.",
                "sources": []
            }
        
        # Step 4: Graph expansion
        print(f"[{self.name}] Step 4: Expanding context with graph...")
        expanded_docs = self.graph_expander.run(accessible_docs, self.graph_store)
        
        # Step 5: Synthesize answer
        print(f"[{self.name}] Step 5: Synthesizing answer...")
        result = self.synthesizer.run(expanded_docs, query)
        
        print(f"[{self.name}] Retrieval complete")
        return result
    
    def _synthesize_answer(self, query: str, context: str, documents: List[Dict]) -> str:
        """Synthesize answer from context."""
        answer = f"Based on the search results, here's what I found about '{query}':\n\n"
        answer += f"Found {len(documents)} relevant documents:\n"
        for doc in documents[:3]:
            answer += f"- {doc['source']}: {doc['content'][:200]}...\n"
        return answer
    
    def _vector_search(self, query: str) -> List[Document]:
        """Perform vector search."""
        if not self.vector_store:
            print(f"[{self.name}] Warning: No vector store configured")
            return []
        
        # Placeholder - return empty for now
        return []


class HealingAgent(DeepAgent):
    """Parent agent for system health monitoring and embedding optimization."""
    
    def __init__(
        self,
        config_path: str = "config/agent_config.yaml",
        llm_manager: Optional[LLMManager] = None,
        use_intelligent_rbac: bool = False
    ):
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        agent_config = config["healing_agent"]
        super().__init__(
            name=agent_config["name"],
            memory_backend=agent_config["memory_backend"],
            config=agent_config
        )
        
        self.llm_manager = llm_manager or LLMManager()
        self.run_interval = agent_config.get("run_interval", "24h")
        self.auto_optimize = agent_config.get("auto_optimize", True)
        self.use_intelligent_rbac = use_intelligent_rbac
        
        # Initialize storage and intelligent RBAC healing if enabled
        if self.use_intelligent_rbac:
            self.rag_db = RAGDatabase()
            self.vector_store = ChromaVectorStore()
            self.rbac_healing = RBACHealingSubagent(
                self.rag_db, self.vector_store
            )
            print(f"[{self.name}] Intelligent RBAC healing enabled")
        
        # Initialize subagents
        subagent_configs = agent_config["subagents"]
        
        self.heatmap_analyzer = HeatmapAnalyzerSubagent(
            name=subagent_configs["heatmap_analyzer"]["name"],
            config=subagent_configs["heatmap_analyzer"]
        )
        
        self.optimizer = OptimizationSubagent(
            name=subagent_configs["optimization"]["name"],
            config=subagent_configs["optimization"],
            llm_manager=self.llm_manager
        )
    
    def _execute(self, time_range: Optional[str] = None, healing_mode: str = "full") -> Dict[str, Any]:
        """Execute healing pipeline with optional intelligent RBAC."""
        time_range = time_range or self.run_interval
        print(f"[{self.name}] Starting health check for {time_range}")
        
        if self.use_intelligent_rbac:
            return self._execute_intelligent(healing_mode)
        else:
            return self._execute_traditional(time_range)
    
    def execute(self, time_range: Optional[str] = None, healing_mode: str = "full") -> Dict[str, Any]:
        """Public execute method - delegates to _execute."""
        return self._execute(time_range, healing_mode)
    
    def _execute_intelligent(self, healing_mode: str = "full") -> Dict[str, Any]:
        """Execute intelligent RBAC-aware healing pipeline."""
        print(f"[{self.name}] Using intelligent RBAC healing (mode: {healing_mode})...")
        
        try:
            if healing_mode == "full":
                result = self.rbac_healing.run_full_healing()
            elif healing_mode == "namespace":
                result = self.rbac_healing.run_namespace_optimization()
            elif healing_mode == "chunk":
                result = self.rbac_healing.run_chunk_optimization()
            elif healing_mode == "refragment":
                result = self.rbac_healing.apply_refragmentation()
            else:
                result = self.rbac_healing.get_healing_status()
            
            print(f"[{self.name}] Healing complete: {result.get('status', 'success')}")
            return result
        
        except Exception as e:
            print(f"[{self.name}] Error in intelligent healing: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat() if hasattr(datetime, 'now') else None
            }
    
    def _execute_traditional(self, time_range: str) -> Dict[str, Any]:
        """Execute traditional healing pipeline."""
        # Step 1: Analyze system metrics
        print(f"[{self.name}] Step 1: Analyzing system metrics...")
        analysis = self.heatmap_analyzer.run(time_range)
        issues = analysis.get("issues", [])
        
        print(f"[{self.name}] Found {len(issues)} issues")
        
        if not issues:
            print(f"[{self.name}] System is healthy!")
            return {
                "status": "healthy",
                "issues": [],
                "optimizations": []
            }
        
        # Step 2: Optimize if auto_optimize is enabled
        optimizations = []
        if self.auto_optimize:
            print(f"[{self.name}] Step 2: Applying optimizations...")
            opt_result = self.optimizer.run(issues)
            optimizations = opt_result.get("optimizations", [])
            print(f"[{self.name}] Applied {len(optimizations)} optimizations")
        
        return {
            "status": "issues_found",
            "issues": issues,
            "optimizations": optimizations,
            "timestamp": analysis.get("timestamp")
        }
        
        print(f"[{self.name}] Found {len(issues)} issues")
        
        if not issues:
            print(f"[{self.name}] System is healthy!")
            return {
                "status": "healthy",
                "issues": [],
                "optimizations": []
            }
        
        # Step 2: Optimize if auto_optimize is enabled
        optimizations = []
        if self.auto_optimize:
            print(f"[{self.name}] Step 2: Applying optimizations...")
            opt_result = self.optimizer.run(issues)
            optimizations = opt_result.get("optimizations", [])
            print(f"[{self.name}] Applied {len(optimizations)} optimizations")
        
        return {
            "status": "issues_found",
            "issues": issues,
            "optimizations": optimizations,
            "timestamp": analysis.get("timestamp")
        }
