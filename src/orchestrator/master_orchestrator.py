"""
Master Orchestrator
Coordinates all agents (Ingestion, Retrieval, Healing) in the DeepAgent RAG system.
Supports agent spawning and tracks all operations in SQLite.
"""

from typing import List, Dict, Any, Optional
import yaml
from datetime import datetime
import time

from ..agents import IngestionAgent, RetrievalAgent, HealingAgent
from ..abstraction import (
    DataSourceManager, LLMManager, RBACManager, Document
)
from ..storage import RAGDatabase


class MasterOrchestrator:
    """Master agent that orchestrates all RAG operations."""
    
    def __init__(
        self,
        config_path: str = "config/agent_config.yaml",
        llm_config_path: str = "config/llm_config.yaml",
        data_config_path: str = "config/data_sources.yaml",
        rbac_config_path: str = "config/rbac_config.yaml",
        db_path: str = "data/rag_system.db"
    ):
        # Load master config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.config = config.get("master_agent", {})
        self.name = self.config.get("name", "MasterOrchestrator")
        self.max_iterations = self.config.get("max_iterations", 10)
        
        print(f"[{self.name}] Initializing DeepAgent RAG System...")
        
        # Initialize database
        print(f"[{self.name}] Initializing SQLite database at {db_path}...")
        self.db = RAGDatabase(db_path)
        
        # Initialize abstraction layers
        print(f"[{self.name}] Loading LLM Manager...")
        self.llm_manager = LLMManager(llm_config_path)
        
        print(f"[{self.name}] Loading Data Source Manager...")
        self.data_source_manager = DataSourceManager(data_config_path)
        
        print(f"[{self.name}] Loading RBAC Manager...")
        self.rbac_manager = RBACManager(rbac_config_path)
        
        # Initialize parent agents
        print(f"[{self.name}] Initializing Ingestion Agent...")
        self.ingestion_agent = IngestionAgent(
            config_path=config_path,
            llm_manager=self.llm_manager,
            rbac_manager=self.rbac_manager
        )
        
        print(f"[{self.name}] Initializing Retrieval Agent...")
        self.retrieval_agent = RetrievalAgent(
            config_path=config_path,
            llm_manager=self.llm_manager,
            rbac_manager=self.rbac_manager
        )
        
        print(f"[{self.name}] Initializing Healing Agent...")
        self.healing_agent = HealingAgent(
            config_path=config_path,
            llm_manager=self.llm_manager
        )
        
        # Storage
        self.vector_store = None  # Initialize with actual vector store
        self.graph_store = None   # Initialize with actual graph store
        
        # Agent registry for dynamic spawning
        self._spawned_agents = {}
        
        print(f"[{self.name}] Initialization complete!")

    
    def ingest_documents(
        self,
        sources: List[str],
        store: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest documents from various sources.
        
        Args:
            sources: List of file paths or data sources
            store: Whether to store in vector/graph databases
        
        Returns:
            Dictionary with ingestion results
        """
        print(f"\n{'='*60}")
        print(f"[{self.name}] INGESTION PHASE")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Load documents from sources
            print(f"[{self.name}] Loading documents from {len(sources)} source(s)...")
            documents = self.data_source_manager.load_documents(sources)
            print(f"[{self.name}] Loaded {len(documents)} raw documents")
            
            # Process through ingestion agent
            processed_docs = self.ingestion_agent.run(documents)
            
            # Store in database
            for doc in processed_docs:
                doc_data = {
                    "doc_id": doc.id,
                    "source": doc.source or "unknown",
                    "content": doc.content,
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "total_chunks": doc.metadata.get("total_chunks"),
                    "classification": getattr(doc, 'classification', doc.metadata.get("classification", "unclassified")),
                    "min_access_level": getattr(doc, 'min_access_level', doc.metadata.get("min_access_level", 5))
                }
                self.db.insert_document(doc_data)
                
                # Store metadata
                for key, value in doc.metadata.items():
                    if key not in ["chunk_id", "total_chunks"]:
                        self.db.insert_metadata(doc.id, key, str(value))
                
                # Store embedding if available
                embedding = getattr(doc, 'embedding', doc.metadata.get("embedding"))
                if embedding:
                    self.db.insert_embedding(doc.id, embedding, "default")
            
            # Store in vector and graph databases
            if store:
                print(f"[{self.name}] Storing documents in vector/graph stores...")
                self._store_documents(processed_docs)
            
            duration = time.time() - start_time
            
            # Log operation
            result = {
                "status": "success",
                "documents_loaded": len(documents),
                "chunks_created": len(processed_docs),
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }
            
            self.db.log_operation(
                operation_type="ingestion",
                agent_name="IngestionAgent",
                status="success",
                input_data={"sources": sources},
                output_data=result,
                duration=duration
            )
            
            # Log metrics
            self.db.log_metric("documents_ingested", len(documents), "ingestion")
            self.db.log_metric("chunks_created", len(processed_docs), "ingestion")
            
            print(f"[{self.name}] Ingestion complete in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.db.log_operation(
                operation_type="ingestion",
                agent_name="IngestionAgent",
                status="failed",
                input_data={"sources": sources},
                error_message=str(e),
                duration=duration
            )
            raise
    
    def retrieve_and_answer(
        self,
        query: str,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve documents and generate answer for query.
        
        Args:
            query: User's question
            user: User information dict with id, role, etc.
        
        Returns:
            Dictionary with answer and sources
        """
        print(f"\n{'='*60}")
        print(f"[{self.name}] RETRIEVAL PHASE")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Process through retrieval agent
            result = self.retrieval_agent.run(query, user)
            
            duration = time.time() - start_time
            result["duration_seconds"] = duration
            result["timestamp"] = datetime.now().isoformat()
            
            # Log query
            self.db.log_query(
                query=query,
                user_id=user.get("user_id", "unknown"),
                user_role=user.get("role", "unknown"),
                documents_retrieved=len(result.get("sources", [])),
                answer=result.get("answer", ""),
                response_time=duration,
                success=result.get("status") == "success"
            )
            
            # Log operation
            self.db.log_operation(
                operation_type="retrieval",
                agent_name="RetrievalAgent",
                status="success",
                input_data={"query": query, "user": user},
                output_data=result,
                duration=duration,
                user_id=user.get("user_id")
            )
            
            # Log metrics
            self.db.log_metric("query_response_time", duration, "retrieval")
            self.db.log_metric("documents_retrieved", len(result.get("sources", [])), "retrieval")
            
            print(f"[{self.name}] Retrieval complete in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.db.log_query(
                query=query,
                user_id=user.get("user_id", "unknown"),
                user_role=user.get("role", "unknown"),
                documents_retrieved=0,
                answer="",
                response_time=duration,
                success=False
            )
            self.db.log_operation(
                operation_type="retrieval",
                agent_name="RetrievalAgent",
                status="failed",
                input_data={"query": query, "user": user},
                error_message=str(e),
                duration=duration,
                user_id=user.get("user_id")
            )
            raise
    
    def heal_system(self, time_range: Optional[str] = None) -> Dict[str, Any]:
        """
        Run system health check and optimization.
        
        Args:
            time_range: Time range for analysis (e.g., "24h", "7d")
        
        Returns:
            Dictionary with health status and optimizations
        """
        print(f"\n{'='*60}")
        print(f"[{self.name}] HEALING PHASE")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            # Get documents needing re-embedding
            docs_to_reembed = self.db.get_documents_for_reembedding()
            
            # Log healing operation
            operation_id = self.db.log_healing_operation(
                operation_type="system_optimization",
                target_doc_ids=[doc["doc_id"] for doc in docs_to_reembed],
                reason="Scheduled system healing check"
            )
            
            # Process through healing agent
            result = self.healing_agent.run(time_range)
            
            duration = time.time() - start_time
            result["duration_seconds"] = duration
            result["documents_to_reembed"] = len(docs_to_reembed)
            
            # Update healing operation
            self.db.update_healing_operation(operation_id, "completed", result)
            
            # Log operation
            self.db.log_operation(
                operation_type="healing",
                agent_name="HealingAgent",
                status="success",
                input_data={"time_range": time_range},
                output_data=result,
                duration=duration
            )
            
            # Log metrics
            self.db.log_metric("healing_operations", 1, "healing")
            self.db.log_metric("documents_reembedded", len(docs_to_reembed), "healing")
            
            print(f"[{self.name}] Healing complete in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.db.log_operation(
                operation_type="healing",
                agent_name="HealingAgent",
                status="failed",
                input_data={"time_range": time_range},
                error_message=str(e),
                duration=duration
            )
            raise
    
    def spawn_agent(
        self,
        parent_agent: str,
        child_agent_type: str,
        task_description: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Dynamically spawn a new agent for a specific task.
        
        Args:
            parent_agent: Name of the parent agent spawning this agent
            child_agent_type: Type of agent to spawn ("ingestion", "retrieval", "healing", "custom")
            task_description: Description of the task for this agent
            config: Optional configuration for the new agent
        
        Returns:
            Agent ID of the spawned agent
        """
        import uuid
        agent_id = f"{child_agent_type}_{uuid.uuid4().hex[:8]}"
        
        print(f"[{self.name}] Spawning {child_agent_type} agent: {agent_id}")
        print(f"[{self.name}] Task: {task_description}")
        
        # Log spawn
        spawn_id = self.db.log_agent_spawn(
            parent_agent=parent_agent,
            child_agent=agent_id,
            task_description=task_description
        )
        
        try:
            # Create agent instance based on type
            if child_agent_type == "ingestion":
                agent = IngestionAgent(
                    config_path="config/agent_config.yaml",
                    llm_manager=self.llm_manager,
                    rbac_manager=self.rbac_manager
                )
            elif child_agent_type == "retrieval":
                agent = RetrievalAgent(
                    config_path="config/agent_config.yaml",
                    llm_manager=self.llm_manager,
                    rbac_manager=self.rbac_manager
                )
            elif child_agent_type == "healing":
                agent = HealingAgent(
                    config_path="config/agent_config.yaml",
                    llm_manager=self.llm_manager
                )
            else:
                raise ValueError(f"Unknown agent type: {child_agent_type}")
            
            # Register agent
            self._spawned_agents[agent_id] = {
                "agent": agent,
                "type": child_agent_type,
                "task": task_description,
                "parent": parent_agent,
                "spawn_id": spawn_id,
                "spawned_at": datetime.now().isoformat()
            }
            
            # Update spawn status
            self.db.update_agent_spawn_status(spawn_id, "active")
            
            # Log metric
            self.db.log_metric("agents_spawned", 1, "agent_spawn")
            
            print(f"[{self.name}] Agent {agent_id} spawned successfully")
            return agent_id
            
        except Exception as e:
            self.db.update_agent_spawn_status(spawn_id, "failed")
            raise
    
    def get_spawned_agent(self, agent_id: str) -> Optional[Any]:
        """Get a spawned agent by ID."""
        return self._spawned_agents.get(agent_id, {}).get("agent")
    
    def list_spawned_agents(self) -> List[Dict[str, Any]]:
        """List all spawned agents."""
        return [
            {
                "agent_id": agent_id,
                "type": info["type"],
                "task": info["task"],
                "parent": info["parent"],
                "spawned_at": info["spawned_at"]
            }
            for agent_id, info in self._spawned_agents.items()
        ]
    
    def terminate_spawned_agent(self, agent_id: str):
        """Terminate a spawned agent."""
        if agent_id in self._spawned_agents:
            spawn_id = self._spawned_agents[agent_id]["spawn_id"]
            self.db.update_agent_spawn_status(spawn_id, "terminated")
            del self._spawned_agents[agent_id]
            print(f"[{self.name}] Agent {agent_id} terminated")
    
    def _store_documents(self, documents: List[Document]):
        """Store documents in vector and graph databases."""
        # Placeholder for actual storage implementation
        vector_config = self.data_source_manager.get_vector_store_config()
        graph_config = self.data_source_manager.get_graph_store_config()
        
        print(f"[{self.name}] Vector store: {vector_config.get('type')}")
        print(f"[{self.name}] Graph store: {graph_config.get('type')}")
        print(f"[{self.name}] Stored {len(documents)} documents")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "orchestrator": self.name,
            "agents": {
                "ingestion": self.ingestion_agent.name,
                "retrieval": self.retrieval_agent.name,
                "healing": self.healing_agent.name
            },
            "llm_provider": self.llm_manager.default_provider,
            "embedding_provider": self.llm_manager.default_embedding_provider,
            "rbac_enabled": self.rbac_manager.enforce_rbac,
            "timestamp": datetime.now().isoformat()
        }
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all registered users."""
        users = self.rbac_manager.list_users()
        return [
            {
                "user_id": user.user_id,
                "name": user.name,
                "role": user.role,
                "access_level": user.access_level,
                "permissions": list(user.permissions)
            }
            for user in users
        ]
    
    def list_roles(self) -> List[Dict[str, Any]]:
        """List all available roles."""
        roles = self.rbac_manager.list_roles()
        return [
            {
                "role": role,
                **self.rbac_manager.get_role_info(role)
            }
            for role in roles
        ]
