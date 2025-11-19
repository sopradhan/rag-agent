"""
Retrieval Agent
Autonomous query processing with RBAC enforcement using DeepAgents
Uses: permission_check, vector_search, rerank, synthesize_answer
Uses dynamic parameters from ParameterManager for runtime optimization
Visualizes thought process for transparency and debugging
"""
import json
import hashlib
import time
from typing import Dict, Any, Optional
from deepagents import create_deep_agent
from langchain_core.tools import Tool
from core.agent_utils import AgentInitializer, ToolFactory, PromptBuilder
from core.parameter_manager import get_parameter_manager, PerformanceMetrics
from core.thought_visualizer import ThoughtVisualizer


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
        
        # Get parameter manager for dynamic optimization
        self.param_manager = get_parameter_manager()
        
        # Get initial parameters from manager (will use defaults or configured values)
        rag_params = self.param_manager.get_rag_params()
        self.top_k = rag_params['top_k']
        self.similarity_threshold = rag_params['similarity_threshold']
        
        # Load configuration with system prompts
        self.prompts_config = AgentInitializer.load_prompts_config()
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create DeepAgent with system prompt from config
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=services['llm'].get_model()
        )
        
        print(f"[{self.name}] Initialized with {len(self.tools)} tools")
        print(f"[{self.name}] Using top_k={self.top_k}, similarity_threshold={self.similarity_threshold}")
    
    def _create_tools(self):
        """Create retrieval tools with service bindings"""
        from tools.retrieval_tools import (
            permission_check_tool, vector_search_tool, rerank_results_tool,
            synthesize_answer_tool, graph_expand_tool
        )
        from tools.common_tools import get_system_status_tool, query_database_tool
        
        # Extract functions from @tool decorators
        funcs = {
            'perm_check': ToolFactory.extract_tool_func(permission_check_tool),
            'vector_search': ToolFactory.extract_tool_func(vector_search_tool),
            'rerank': ToolFactory.extract_tool_func(rerank_results_tool),
            'synthesize': ToolFactory.extract_tool_func(synthesize_answer_tool),
            'expand': ToolFactory.extract_tool_func(graph_expand_tool),
            'status': ToolFactory.extract_tool_func(get_system_status_tool),
            'query': ToolFactory.extract_tool_func(query_database_tool),
        }
        
        # Services for binding
        db_service = self.services['db']
        llm_service = self.services['llm']
        vectordb_service = self.services['vectordb']
        top_k = self.top_k
        
        # Wrapper functions
        def _permission_check(user_id, chunk_ids):
            chunk_ids = json.loads(chunk_ids) if isinstance(chunk_ids, str) else chunk_ids
            return funcs['perm_check'](user_id, json.dumps(chunk_ids), db_service)
        
        def _vector_search(query, top_k_param=None):
            k = top_k_param or top_k
            return funcs['vector_search'](query, k, llm_service, vectordb_service)
        
        def _rerank_results(query, results, top_n=5):
            results = json.loads(results) if isinstance(results, str) else results
            return funcs['rerank'](query, results, top_n)
        
        def _synthesize_answer(query, results):
            results = json.loads(results) if isinstance(results, str) else results
            return funcs['synthesize'](query, results, llm_service)
        
        def _graph_expand(results):
            results = json.loads(results) if isinstance(results, str) else results
            return funcs['expand'](results, vectordb_service)
        
        return [
            ToolFactory.create_tool("permission_check", 
                "Filter chunks based on user's RBAC permissions", _permission_check),
            ToolFactory.create_tool("vector_search",
                "Search vector database for similar chunks", _vector_search),
            ToolFactory.create_tool("rerank_results",
                "Rerank search results for better relevance", _rerank_results),
            ToolFactory.create_tool("synthesize_answer",
                "Generate final answer from retrieved chunks", _synthesize_answer),
            ToolFactory.create_tool("graph_expand",
                "Expand context by finding related chunks", _graph_expand),
            ToolFactory.create_tool("get_system_status",
                "Get current system status and statistics", 
                lambda: funcs['status'](db_service, vectordb_service)),
            ToolFactory.create_tool("query_database",
                "Execute SQL SELECT query",
                lambda sql: funcs['query'](sql, db_service)),
        ]
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for RetrievalAgent from config"""
        fallback = """You are an autonomous retrieval agent for a RAG system with strict RBAC enforcement.
        
Core responsibilities:
1. Search vector database and retrieve relevant chunks
2. Enforce RBAC permissions strictly - never leak restricted information
3. Report RBAC analysis transparently
4. Synthesize answer from allowed chunks only

Never bypass RBAC checks. Always report access decisions."""
        
        return AgentInitializer.get_agent_prompt('retrieval', self.prompts_config, fallback)
    
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
        
        # Create thought process visualization
        thought = ThoughtVisualizer.create_process(self.name, f"Process Query: {query[:50]}")
        step_init = thought.add_step(
            "Initialize",
            "Load parameters and prepare for query processing",
            {"user_id": user_id, "use_planning": use_planning}
        )
        thought.start_step(step_init)
        
        try:
            # Get current parameters from manager (may have been auto-optimized)
            rag_params = self.param_manager.get_rag_params()
            current_top_k = rag_params['top_k']
            current_similarity_threshold = rag_params['similarity_threshold']
            
            # Analyze query heatmap to learn from historical patterns
            heatmap = self.services['db'].get_heatmap_analysis()
            if heatmap['poor_quality']:
                # Increase similarity threshold for high-precision queries if past ones were poor quality
                current_similarity_threshold = min(0.85, current_similarity_threshold + 0.05)
                thought.add_metadata("heatmap_analysis", "Detected poor quality queries - increasing threshold")
            if heatmap['cold_spots'] and len(heatmap['cold_spots']) > 0:
                # Rare queries might need more results
                current_top_k = min(20, current_top_k + 3)
                thought.add_metadata("heatmap_analysis", "Detected cold spot query - retrieving more chunks")
            
            thought.complete_step(step_init)
            thought.set_metadata("top_k", current_top_k)
            thought.set_metadata("similarity_threshold", current_similarity_threshold)
            
            # Step 2: Query processing
            step_query = thought.add_step(
                "Vector Search",
                f"Search vector database for top {current_top_k} relevant chunks",
                {"threshold": current_similarity_threshold}
            )
            thought.start_step(step_query)
            
            # Create request for agent
            planning_note = "\nUse write_todos with a list of steps to plan your approach: write_todos(['Step 1', 'Step 2', ...])" if use_planning else ""
            
            request = f"""
Process this query with strict RBAC enforcement:

Query: {query}
User ID: {user_id}
{planning_note}

Steps you MUST follow:
1. Search vector database for relevant chunks (top {current_top_k})
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
            
            thought.complete_step(step_query, int((time.time() - start_time) * 1000))
            
            # Step 3: RBAC enforcement
            step_rbac = thought.add_step(
                "RBAC Enforcement",
                f"Check permissions for user '{user_id}' on retrieved chunks",
                {"chunks_retrieved": len(messages)}
            )
            thought.start_step(step_rbac)
            thought.complete_step(step_rbac, 50)  # Estimate 50ms
            
            # Step 4: Response generation
            step_synthesis = thought.add_step(
                "Synthesis",
                "Generate final answer from allowed results",
                {"response_length": len(response), "message_count": len(messages)}
            )
            thought.start_step(step_synthesis)
            
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
            
            # Log token usage (estimate: ~4 chars per token)
            prompt_tokens = (len(query) + len(str(retrieved_docs))) // 4
            completion_tokens = len(response) // 4
            self.services['db'].log_token_usage(
                self.name, op_id, 'ollama', 'qwen2.5:0.5b',
                prompt_tokens, completion_tokens
            )
            
            # Estimate retrieval accuracy from response (simple heuristic)
            # In production, would use actual metrics from retrieval results
            retrieval_accuracy = 0.8 if len(response) > 100 else 0.5
            
            # Track performance metrics for optimization
            metrics = PerformanceMetrics(
                response_time_ms=execution_time_ms,
                retrieval_accuracy=retrieval_accuracy,
                rbac_denial_rate=0.0,  # Would track from actual denials
                token_usage=len(response) // 4,  # Rough estimate
                relevance_score=retrieval_accuracy
            )
            
            # Auto-optimize parameters based on metrics
            optimizations = self.param_manager.auto_optimize(metrics)
            if optimizations:
                print(f"[{self.name}] Auto-optimizations applied: {optimizations}")
            
            # Update query heatmap
            self.services['db'].update_query_heatmap(
                query_hash=query_hash,
                query_example=query,
                retrieval_accuracy=retrieval_accuracy,
                response_time_ms=execution_time_ms
            )
            
            # Store agent memory (execution context for future queries)
            self.services['db'].store_agent_memory(
                self.name, f"query_{query_hash}", 
                json.dumps({
                    "query": query, "accuracy": retrieval_accuracy,
                    "time_ms": execution_time_ms, "user": user_id
                }), 'query_result'
            )
            
            # Store in query history
            self.services['db'].execute("""
                INSERT INTO query_history 
                (user_id, query_text, query_type, response, execution_time_ms, status)
                VALUES (?, ?, 'retrieval', ?, ?, 'completed')
            """, (user_id, query, response, execution_time_ms))
            
            # Complete thought process
            thought.complete_step(step_synthesis, int((time.time() - start_time) * 1000))
            thought.set_metadata("success", True)
            thought.set_metadata("accuracy", retrieval_accuracy)
            
            # Print animated thought visualization
            thought.animate_simple(delay=0.3)
            
            return {
                "success": True,
                "query": query,
                "user_id": user_id,
                "answer": response,
                "execution_time_ms": execution_time_ms,
                "messages": len(messages),
                "parameters": {
                    "top_k": current_top_k,
                    "similarity_threshold": current_similarity_threshold
                },
                "thought_process": thought.to_dict()
            }
            
        except Exception as e:
            thought.error_step(thought.current_step, str(e))
            print(thought.visualize_simple())
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "thought_process": thought.to_dict()
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
