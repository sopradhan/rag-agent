"""
Retrieval Agent
Autonomous query processing with RBAC enforcement using DeepAgents
Uses: permission_check, vector_search, rerank, synthesize_answer
"""
import json
import hashlib
import time
from typing import Dict, Any, Optional
from deepagents import create_deep_agent
from langchain_core.tools import Tool
from core.config.loader import load_all_configs


class RetrievalAgent:
    """Autonomous query processing agent with RBAC"""
    
    def __init__(self, services: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize RetrievalAgent
        
        Args:
            services: Dict with 'llm', 'vectordb', 'db' services
            config: Agent configuration
        """
        self.services = services
        self.config = config
        self.name = config.get('name', 'RetrievalAgent')
        self.top_k = config.get('top_k', 10)
        self.similarity_threshold = config.get('similarity_threshold', 0.75)
        
        # Load configuration with system prompts
        try:
            self.prompts_config = load_all_configs('config').get('prompts', {})
        except:
            self.prompts_config = {}
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create DeepAgent with system prompt from config
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=services['llm'].get_model()
        )
        
        print(f"[{self.name}] Initialized with {len(self.tools)} tools (prompts from config)")
    
    def _create_tools(self):
        """Create retrieval tools with service bindings"""
        from tools.retrieval_tools import (
            permission_check_tool,
            vector_search_tool,
            rerank_results_tool,
            synthesize_answer_tool,
            graph_expand_tool
        )
        from tools.common_tools import get_system_status_tool, query_database_tool
        
        # Capture services
        db_service = self.services['db']
        llm_service = self.services['llm']
        vectordb_service = self.services['vectordb']
        top_k = self.top_k
        
        # Get the underlying functions from @tool decorated objects
        # This allows us to call them directly without the StructuredTool wrapper
        perm_check_func = permission_check_tool.func if hasattr(permission_check_tool, 'func') else permission_check_tool
        vector_search_func = vector_search_tool.func if hasattr(vector_search_tool, 'func') else vector_search_tool
        rerank_func = rerank_results_tool.func if hasattr(rerank_results_tool, 'func') else rerank_results_tool
        synthesize_func = synthesize_answer_tool.func if hasattr(synthesize_answer_tool, 'func') else synthesize_answer_tool
        expand_func = graph_expand_tool.func if hasattr(graph_expand_tool, 'func') else graph_expand_tool
        status_func = get_system_status_tool.func if hasattr(get_system_status_tool, 'func') else get_system_status_tool
        query_func = query_database_tool.func if hasattr(query_database_tool, 'func') else query_database_tool
        
        # Create wrapper functions that properly bind services
        def _permission_check(user_id, chunk_ids):
            if isinstance(chunk_ids, str):
                chunk_ids = json.loads(chunk_ids)
            return perm_check_func(user_id, json.dumps(chunk_ids), db_service)
        
        def _vector_search(query, top_k_param=None):
            k = top_k_param if top_k_param else top_k
            return vector_search_func(query, k, llm_service, vectordb_service)
        
        def _rerank_results(query, results, top_n=5):
            if isinstance(results, str):
                results = json.loads(results)
            return rerank_func(query, results, top_n)
        
        def _synthesize_answer(query, results):
            if isinstance(results, str):
                results = json.loads(results)
            return synthesize_func(query, results, llm_service)
        
        def _graph_expand(results):
            if isinstance(results, str):
                results = json.loads(results)
            return expand_func(results, vectordb_service)
        
        def _get_status():
            return status_func(db_service, vectordb_service)
        
        def _query_db(sql):
            return query_func(sql, db_service)
        
        tools = [
            Tool(
                name="permission_check",
                description="Filter chunks based on user's RBAC permissions. Args: user_id (str), chunk_ids (list or JSON string)",
                func=_permission_check
            ),
            
            Tool(
                name="vector_search",
                description="Search vector database for similar chunks. Args: query (str), top_k_param (int, optional)",
                func=_vector_search
            ),
            
            Tool(
                name="rerank_results",
                description="Rerank search results to improve relevance. Args: query (str), results (list or JSON), top_n (int, optional)",
                func=_rerank_results
            ),
            
            Tool(
                name="synthesize_answer",
                description="Generate final answer from retrieved chunks using LLM. Args: query (str), results (list or JSON)",
                func=_synthesize_answer
            ),
            
            Tool(
                name="graph_expand",
                description="Expand context by finding related chunks. Args: results (list or JSON)",
                func=_graph_expand
            ),
            
            Tool(
                name="get_system_status",
                description="Get current system status and statistics",
                func=_get_status
            ),
            
            Tool(
                name="query_database",
                description="Execute SQL SELECT query. Args: sql (str)",
                func=_query_db
            )
        ]
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for RetrievalAgent from config"""
        # Try to get from config first
        if self.prompts_config.get('retrieval_agent', {}).get('system_prompt'):
            return self.prompts_config['retrieval_agent']['system_prompt']
        
        # Fallback to hardcoded prompt
        return self.prompts_config.get('retrieval_agent', {}).get('system_prompt', """You are an autonomous retrieval agent for a RAG system with strict RBAC enforcement.

=== CORE RESPONSIBILITIES ===
1. Process user queries and retrieve relevant information
2. Enforce RBAC permissions STRICTLY - never leak restricted information  
3. Provide transparent reasoning about RBAC tag decisions
4. Show thought process for relevance assessment

=== AVAILABLE TOOLS ===
- vector_search: Search embeddings (top K similar chunks)
- permission_check: Filter by RBAC tags
- rerank_results: Improve relevance ranking
- synthesize_answer: Generate final answer

=== STRICT WORKFLOW ===
1. Search vector DB
2. Check permissions
3. Rerank allowed chunks
4. Synthesize answer
5. Report RBAC analysis

NEVER bypass RBAC checks.
""")
    
    def process_query(self, query: str, user_id: str, 
                     use_planning: bool = False) -> Dict[str, Any]:
        """
        Process a user query with RBAC enforcement
        
        Args:
            query: User's query text
            user_id: User identifier for RBAC
            use_planning: Whether to use write_todos for planning
            
        Returns:
            Query results with answer and metadata
        """
        start_time = time.time()
        
        try:
            # Create request for agent
            planning_note = "\nUse write_todos with a list of steps to plan your approach: write_todos(['Step 1', 'Step 2', ...])" if use_planning else ""
            
            request = f"""
Process this query with strict RBAC enforcement:

Query: {query}
User ID: {user_id}
{planning_note}

Steps you MUST follow:
1. Search vector database for relevant chunks (top {self.top_k})
2. Extract chunk IDs from search results
3. Check user '{user_id}' permissions for those chunks
4. Filter to ONLY chunks user is allowed to access
5. If no allowed chunks, return "Access Denied - insufficient permissions"
6. Rerank allowed results for relevance
7. Synthesize answer from allowed chunks only
8. Cite sources with chunk IDs

Remember: NEVER return information the user doesn't have permission to access.
"""
            
            # Invoke DeepAgent
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": request}]
            })
            
            # Extract response
            messages = result.get('messages', [])
            final_message = messages[-1] if messages else None
            
            # Handle both dict and AIMessage objects
            if final_message is None:
                response = 'No response'
            elif isinstance(final_message, dict):
                response = final_message.get('content', 'No response')
            else:
                # Handle AIMessage or other message types
                response = getattr(final_message, 'content', str(final_message))
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Generate query hash for heatmap
            query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:16]
            
            # Log operation
            op_id = self.services['db'].log_agent_operation(
                agent_name=self.name,
                operation_type='retrieval',
                query=query,
                final_response=response,
                response_time_ms=execution_time_ms,
                metadata={'user_id': user_id, 'use_planning': use_planning}
            )
            
            # Update query heatmap
            self.services['db'].update_query_heatmap(
                query_hash=query_hash,
                query_example=query,
                retrieval_accuracy=0.8,  # TODO: Calculate actual accuracy
                response_time_ms=execution_time_ms
            )
            
            # Store in query history
            self.services['db'].execute("""
                INSERT INTO query_history 
                (user_id, query_text, query_type, response, execution_time_ms, status)
                VALUES (?, ?, 'retrieval', ?, ?, 'completed')
            """, (user_id, query, response, execution_time_ms))
            
            return {
                "success": True,
                "query": query,
                "user_id": user_id,
                "answer": response,
                "execution_time_ms": execution_time_ms,
                "messages": len(messages)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    def process_feedback(self, query_id: int, feedback_score: int):
        """
        Process user feedback for a query
        
        Args:
            query_id: Query ID from query_history
            feedback_score: User rating (1-5)
        """
        try:
            # Update query history
            self.services['db'].execute("""
                UPDATE query_history
                SET user_feedback = ?
                WHERE query_id = ?
            """, (feedback_score, query_id))
            
            # Get query details for heatmap update
            query_info = self.services['db'].query("""
                SELECT query_text, execution_time_ms 
                FROM query_history 
                WHERE query_id = ?
            """, (query_id,))
            
            if query_info:
                query_text = query_info[0]['query_text']
                exec_time = query_info[0]['execution_time_ms']
                query_hash = hashlib.md5(query_text.lower().encode()).hexdigest()[:16]
                
                # Update heatmap with feedback
                self.services['db'].update_query_heatmap(
                    query_hash=query_hash,
                    query_example=query_text,
                    retrieval_accuracy=0.8,
                    response_time_ms=exec_time,
                    user_feedback=feedback_score
                )
            
            print(f"[{self.name}] Feedback recorded: {feedback_score}/5 for query {query_id}")
            
        except Exception as e:
            print(f"[ERROR] Failed to process feedback: {e}")
