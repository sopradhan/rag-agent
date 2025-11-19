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
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create DeepAgent
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=services['llm'].get_model()
        )
        
        print(f"[{self.name}] Initialized with {len(self.tools)} tools")
    
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
        
        tools = [
            Tool(
                name="permission_check",
                description="Filter chunks based on user's RBAC permissions. Args: user_id (str), chunk_ids (list)",
                func=lambda **kwargs: permission_check_tool(
                    kwargs.get('user_id', ''), kwargs.get('chunk_ids', []), self.services['db']
                )
            ),
            
            Tool(
                name="vector_search",
                description="Search vector database for similar chunks. Args: query (str), top_k (int, optional)",
                func=lambda **kwargs: vector_search_tool(
                    kwargs.get('query', ''), kwargs.get('top_k', self.top_k),
                    self.services['llm'],
                    self.services['vectordb']
                )
            ),
            
            Tool(
                name="rerank_results",
                description="Rerank search results to improve relevance. Args: query (str), results (list), top_n (int, optional)",
                func=lambda **kwargs: rerank_results_tool(kwargs.get('query', ''), kwargs.get('results', []), kwargs.get('top_n', 5))
            ),
            
            Tool(
                name="synthesize_answer",
                description="Generate final answer from retrieved chunks using LLM. Args: query (str), results (list)",
                func=lambda **kwargs: synthesize_answer_tool(
                    kwargs.get('query', ''), kwargs.get('results', []), self.services['llm']
                )
            ),
            
            Tool(
                name="graph_expand",
                description="Expand context by finding related chunks. Args: results (list)",
                func=lambda **kwargs: graph_expand_tool(kwargs.get('results', []), self.services['vectordb'])
            ),
            
            Tool(
                name="get_system_status",
                description="Get current system status and statistics",
                func=lambda **kwargs: get_system_status_tool(
                    self.services['db'],
                    self.services['vectordb']
                )
            ),
            
            Tool(
                name="query_database",
                description="Execute SQL SELECT query. Args: sql (str)",
                func=lambda **kwargs: query_database_tool(kwargs.get('sql', ''), self.services['db'])
            )
        ]
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for RetrievalAgent"""
        return """You are an autonomous retrieval agent for a RAG system with RBAC enforcement.

Your responsibilities:
1. Process user queries and retrieve relevant information
2. Enforce RBAC permissions strictly - never leak restricted information
3. Use write_todos to plan complex multi-hop queries
4. Provide accurate answers with source citations
5. Log query metadata for system improvement

Available tools:
- vector_search: Search vector database for similar chunks
- permission_check: Filter results based on user's CDR access codes
- rerank_results: Improve relevance ranking
- synthesize_answer: Generate final answer with LLM
- graph_expand: Find related information (optional)
- get_system_status: Check system status
- query_database: Execute SQL queries for metadata
- write_todos: Plan complex query workflows
- task: Spawn subagents for specialized retrieval

RBAC Enforcement (CRITICAL):
1. ALWAYS check permissions before returning any information
2. User's CDR codes determine what they can access
3. If no matching permissions, return "Access Denied"
4. Log all access attempts for audit trail

Workflow for standard queries:
1. Search vector database for relevant chunks
2. Extract chunk IDs from search results
3. Check user permissions for those chunks
4. Filter to only allowed chunks
5. Rerank remaining results
6. Synthesize answer from allowed chunks
7. Cite sources clearly

For complex queries:
1. Use write_todos to break down into steps
2. Consider spawning specialized subagents with task tool
3. Combine results from multiple searches if needed

Always provide clear, accurate answers with source citations.
Never make up information - only use retrieved context.
"""
    
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
            planning_note = "\nUse write_todos to plan your approach." if use_planning else ""
            
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
            final_message = messages[-1] if messages else {}
            response = final_message.get('content', 'No response')
            
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
