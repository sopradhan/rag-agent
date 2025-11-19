"""
LangChain DeepAgents Orchestrator V2
Uses LangChain-based subagents for all processing
Full chain-of-thought reasoning at every step
"""

from typing import Dict, List, Any
from datetime import datetime
import json

try:
    from langchain_ollama import ChatOllama
except ImportError:
    from langchain_community.chat_models import ChatOllama

from src.storage import RAGDatabase, ChromaVectorStore
from src.subagents.langchain_subagents import (
    AnalyzerSubagent, SearcherSubagent, FilterSubagent, 
    RankerSubagent, SynthesizerSubagent
)


class MasterOrchestrator:
    """LangChain DeepAgents-based Master Orchestrator"""
    
    def __init__(self, name: str = "master_orchestrator_v2"):
        self.name = name
        self.db = RAGDatabase()
        self.vector_store = ChromaVectorStore()
        self.llm = ChatOllama(model="llama3.2:latest", temperature=0.3)
        self.execution_history = []
        
        # Initialize LangChain subagents with parent reference
        self.analyzer = AnalyzerSubagent(parent_agent=None)
        self.searcher = SearcherSubagent(parent_agent=self.analyzer)
        self.filter = FilterSubagent(parent_agent=self.searcher)
        self.ranker = RankerSubagent(parent_agent=self.filter)
        self.synthesizer = SynthesizerSubagent(parent_agent=self.ranker)
        
        # Agent registry for tracking
        self.all_agents = {
            "analyzer": self.analyzer,
            "searcher": self.searcher,
            "filter": self.filter,
            "ranker": self.ranker,
            "synthesizer": self.synthesizer
        }
        self.spawned_agents = {}
        
        print(f"[OK] Master Orchestrator '{name}' initialized with LangChain DeepAgents")
    
    def process_query(self, 
                     query: str, 
                     user_id: str = "default", 
                     user_role: str = "engineer",
                     access_level: int = 3) -> Dict[str, Any]:
        """
        Process query using chain of LangChain DeepAgents
        Each agent uses chain-of-thought reasoning
        """
        
        print(f"\n{'='*80}")
        print(f"LANGCHAIN ORCHESTRATOR: Processing query")
        print(f"User: {user_role} (Level {access_level})")
        print(f"{'='*80}\n")
        
        execution_log = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "user": {"id": user_id, "role": user_role, "access_level": access_level},
            "agents_executed": [],
            "results": {},
            "status": "in_progress",
            "agents_cot_logs": []
        }
        
        try:
            # Step 1: ANALYZE
            print("[STEP 1/5] [ANALYZER] - Query decomposition...")
            analysis_result = self.analyzer.execute(query)
            execution_log["agents_executed"].append("analyzer")
            execution_log["agents_cot_logs"].extend(self.analyzer.execution_log)
            print(f"  [OK] Keywords: {analysis_result.get('keywords', [])}")
            print(f"  [OK] Intent: {analysis_result.get('intent')}")
            
            # Step 2: SEARCH
            print("\n[STEP 2/5] [SEARCHER] - Semantic search...")
            search_result = self.searcher.execute(query, top_k=5)
            documents = search_result.get("documents", [])
            execution_log["agents_executed"].append("searcher")
            execution_log["agents_cot_logs"].extend(self.searcher.execution_log)
            print(f"  [OK] Found {len(documents)} documents")
            
            if not documents:
                print("\n  [WARNING] No documents found")
                execution_log["status"] = "success"
                execution_log["results"] = {
                    "answer": f"No documents found to answer: {query}",
                    "documents_used": 0,
                    "confidence": 0.0,
                    "rbac_applied": False,
                    "reasoning_trace": {"analysis": analysis_result}
                }
                self.execution_history.append(execution_log)
                return execution_log
            
            # Step 3: FILTER
            print(f"\n[STEP 3/5] [FILTER] - RBAC filtering (access level {access_level})...")
            filter_result = self.filter.execute(documents, access_level, user_role)
            filtered_docs = filter_result.get("documents", [])
            execution_log["agents_executed"].append("filter")
            execution_log["agents_cot_logs"].extend(self.filter.execution_log)
            print(f"  [OK] Filtered to {len(filtered_docs)} documents")
            print(f"  [OK] Restricted: {filter_result.get('restricted_count', 0)}")
            
            if not filtered_docs:
                print("\n  [WARNING] Access denied - insufficient permissions")
                execution_log["status"] = "success"
                execution_log["results"] = {
                    "answer": "Access denied: You do not have sufficient permissions to access these documents.",
                    "documents_used": 0,
                    "confidence": 0.0,
                    "rbac_applied": True,
                    "reasoning_trace": {"filter_reason": "access_level_insufficient"}
                }
                self.execution_history.append(execution_log)
                return execution_log
            
            # Step 4: RANK
            print("\n[STEP 4/5] [RANKER] - Document ranking...")
            ranking_result = self.ranker.execute(filtered_docs)
            ranked_docs = ranking_result.get("documents", [])
            execution_log["agents_executed"].append("ranker")
            execution_log["agents_cot_logs"].extend(self.ranker.execution_log)
            top_score = ranking_result.get("top_score", 0)
            print(f"  [OK] Ranked {len(ranked_docs)} documents")
            print(f"  [OK] Top relevance: {top_score:.2f}")
            
            # Step 5: SYNTHESIZE
            print("\n[STEP 5/5] [SYNTHESIZER] - Answer generation...")
            synthesis_result = self.synthesizer.execute(query, ranked_docs)
            execution_log["agents_executed"].append("synthesizer")
            execution_log["agents_cot_logs"].extend(self.synthesizer.execution_log)
            answer = synthesis_result.get("answer", "")
            print(f"  [OK] Answer generated ({len(answer)} chars)")
            
            # Compile results
            execution_log["status"] = "success"
            execution_log["results"] = {
                "answer": answer,
                "confidence": synthesis_result.get("confidence", 0),
                "sources": synthesis_result.get("sources", []),
                "documents_used": len(ranked_docs),
                "rbac_applied": True,
                "reasoning_trace": {
                    "analysis": {
                        "keywords": analysis_result.get("keywords", []),
                        "intent": analysis_result.get("intent")
                    },
                    "search": {"documents_found": len(documents)},
                    "filtering": {"documents_after_filter": len(filtered_docs)},
                    "ranking": {"top_score": top_score},
                    "synthesis": {"documents_used": len(ranked_docs)}
                }
            }
            
        except Exception as e:
            print(f"\n[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            execution_log["status"] = "error"
            execution_log["error"] = str(e)
            execution_log["results"] = {
                "answer": f"Error: {str(e)}",
                "documents_used": 0,
                "confidence": 0.0,
                "rbac_applied": False,
                "reasoning_trace": {}
            }
        
        print(f"\n{'='*80}")
        print(f"EXECUTION COMPLETE - Status: {execution_log['status']}")
        print(f"Chain: {' -> '.join(execution_log['agents_executed'])}")
        print(f"{'='*80}\n")
        
        self.execution_history.append(execution_log)
        return execution_log
    
    def get_execution_history(self, limit: int = 10) -> List[Dict]:
        """Get recent execution history"""
        return self.execution_history[-limit:]
    
    def route_command(self, 
                     command: str, 
                     database_name: str = None,
                     table_name: str = None,
                     **kwargs) -> Dict[str, Any]:
        """
        Route command to appropriate agent based on keyword
        Keywords: ingest, retrieve, heal, query
        """
        command_lower = command.lower()
        
        # Determine intent from command
        if any(kw in command_lower for kw in ["ingest", "upload", "load", "import"]):
            return {
                "intent": "ingest",
                "agent": "IngestionAgent",
                "database": database_name,
                "table": table_name,
                "params": kwargs
            }
        elif any(kw in command_lower for kw in ["retrieve", "search", "query", "find", "fetch"]):
            return {
                "intent": "retrieve",
                "agent": "RetrievalAgent",
                "query": command,
                "database": database_name,
                "table": table_name,
                "params": kwargs
            }
        elif any(kw in command_lower for kw in ["heal", "optimize", "rebuild", "fix", "repair"]):
            return {
                "intent": "heal",
                "agent": "HealingAgent",
                "mode": kwargs.get("mode", "full"),
                "database": database_name,
                "table": table_name,
                "params": kwargs
            }
        elif any(kw in command_lower for kw in ["embedding", "index", "vector"]):
            return {
                "intent": "heal",
                "agent": "HealingAgent",
                "mode": "embedding",
                "database": database_name,
                "table": table_name,
                "params": kwargs
            }
        else:
            # Default to retrieval
            return {
                "intent": "retrieve",
                "agent": "RetrievalAgent",
                "query": command,
                "database": database_name,
                "table": table_name,
                "params": kwargs
            }
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return {
            "total_executions": len(self.execution_history),
            "success_rate": sum(1 for e in self.execution_history if e.get("status") == "success") / max(len(self.execution_history), 1),
            "agents": ["analyzer", "searcher", "filter", "ranker", "synthesizer"],
            "framework": "LangChain DeepAgents"
        }
    
    def dashboard_statistics(self) -> Dict[str, Any]:
        """Get dashboard statistics"""
        stats = self.db.get_dashboard_stats()
        return stats or {
            "total_documents": 0,
            "queries_24h": 0,
            "active_agents": 5,
            "avg_response_time": 0.0,
            "success_rate": 100.0,
            "agent_spawns_24h": 0,
            "healing_ops_24h": 0
        }
    
    def get_agent_tree(self) -> Dict[str, Any]:
        """Get hierarchical agent tree showing spawning relationships"""
        def build_tree(agent):
            spawned = []
            if hasattr(agent, 'spawned_agents') and agent.spawned_agents:
                spawned = [build_tree(child) for child in agent.spawned_agents.values()]
            return {
                "agent_id": agent.agent_id if hasattr(agent, 'agent_id') else "unknown",
                "name": agent.name,
                "spawned_agents": spawned,
                "total_children": len(spawned)
            }
        
        return {
            "orchestrator": self.name,
            "pipeline": [build_tree(agent) for agent in self.all_agents.values()]
        }
    
    def get_all_spawned_agents(self) -> List[Dict[str, Any]]:
        """Get all spawned agents across the system"""
        all_spawned = []
        
        def collect_spawned(agent, parent_name=""):
            if hasattr(agent, 'spawned_agents') and agent.spawned_agents:
                for spawned_agent in agent.spawned_agents.values():
                    all_spawned.append({
                        "agent_id": spawned_agent.agent_id,
                        "name": spawned_agent.name,
                        "parent": agent.name,
                        "type": type(spawned_agent).__name__
                    })
                    collect_spawned(spawned_agent, agent.name)
        
        for agent in self.all_agents.values():
            collect_spawned(agent)
        
        return all_spawned
