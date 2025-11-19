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
        
        # Capture services
        db_service = self.services['db']
        llm_service = self.services['llm']
        vectordb_service = self.services['vectordb']
        top_k = self.top_k
        
        # Create wrapper functions that convert dict args to proper function calls
        def _permission_check(**kwargs):
            user_id = kwargs.get('user_id', '')
            chunk_ids = kwargs.get('chunk_ids', [])
            if isinstance(chunk_ids, str):
                chunk_ids = json.loads(chunk_ids)
            return permission_check_tool(user_id, json.dumps(chunk_ids), db_service)
        
        def _vector_search(**kwargs):
            query = kwargs.get('query', '')
            k = kwargs.get('top_k', top_k)
            return vector_search_tool(query, k, llm_service, vectordb_service)
        
        def _rerank_results(**kwargs):
            query = kwargs.get('query', '')
            results = kwargs.get('results', [])
            if isinstance(results, str):
                results = json.loads(results)
            top_n = kwargs.get('top_n', 5)
            return rerank_results_tool(query, results, top_n)
        
        def _synthesize_answer(**kwargs):
            query = kwargs.get('query', '')
            results = kwargs.get('results', [])
            if isinstance(results, str):
                results = json.loads(results)
            return synthesize_answer_tool(query, results, llm_service)
        
        def _graph_expand(**kwargs):
            results = kwargs.get('results', [])
            if isinstance(results, str):
                results = json.loads(results)
            return graph_expand_tool(results, vectordb_service)
        
        def _get_status(**kwargs):
            return get_system_status_tool(db_service, vectordb_service)
        
        def _query_db(**kwargs):
            sql = kwargs.get('sql', '')
            return query_database_tool(sql, db_service)
        
        tools = [
            Tool(
                name="permission_check",
                description="Filter chunks based on user's RBAC permissions. Args: user_id (str), chunk_ids (list or JSON string)",
                func=_permission_check
            ),
            
            Tool(
                name="vector_search",
                description="Search vector database for similar chunks. Args: query (str), top_k (int, optional)",
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
        """Get system prompt for RetrievalAgent"""
        return """You are an autonomous retrieval agent for a RAG system with strict RBAC enforcement.

=== CORE RESPONSIBILITIES ===
1. Process user queries and retrieve relevant information
2. Enforce RBAC permissions STRICTLY - never leak restricted information  
3. Provide transparent reasoning about RBAC tag decisions
4. Show thought process for relevance assessment
5. Log all access attempts for compliance

=== RBAC TAG SYSTEM (Company-Department-Role) ===
CDR Code Format: [Company][Department][Role] (e.g., "113" = Company 1, Department 1, Role 3)

Tag Information to Report:
- Document's required CDR codes (access control tags)
- User's assigned CDR codes
- Whether intersection exists (grants access)
- Sensitivity level: public, internal, confidential, secret
- Subject area: hr, finance, engineering, general, etc
- Assigned by: ingestion_agent or admin

Example:
  Doc CDR Tags: [131, 132, 133, 231]
  User CDR Tags: [132]
  Access: GRANTED (user has 132, doc allows 131/132/133/231)
  Sensitivity: confidential
  Subject: HR

=== EMBEDDING & SEARCH DETAILS ===
Embeddings stored in ChromaDB:
- Model: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
- Contains: chunk text + metadata (keywords, topics, RBAC tags)
- Search returns: chunk IDs, similarity scores, metadata

Before returning ANY chunk:
1. Verify user has matching CDR code
2. Check sensitivity level matches user role
3. Report RBAC decision in response

=== RESPONSE FORMAT ===
Your response MUST include:

[THOUGHT PROCESS]
- Steps taken to search and filter
- RBAC tag analysis for each result
- Relevance assessment logic
- Any permission denials explained

[RESULTS]
- Only show chunks user can access
- Include RBAC tags and sensitivity
- Cite source chunk IDs
- Report retrieval accuracy

[RBAC REPORT]
- Total chunks retrieved: X
- Chunks granted access: X (Y%)
- Chunks denied access: X (reason: ...)
- User CDR codes: [...]
- Document CDR requirements: [...]

=== AVAILABLE TOOLS ===
- vector_search: Search embeddings (top K similar chunks)
- permission_check: Filter by RBAC tags
- rerank_results: Improve relevance ranking
- synthesize_answer: Generate final answer
- graph_expand: Find related chunks
- get_system_status: System health
- query_database: SQL metadata queries

=== STRICT WORKFLOW ===
1. Search vector DB: vector_search(query=<>, top_k={self.top_k})
2. Extract chunk IDs from results
3. Check permissions: permission_check(user_id=<>, chunk_ids=[...])
4. Report RBAC analysis
5. Rerank allowed chunks: rerank_results(query=<>, results=[...])
6. Synthesize answer: synthesize_answer(query=<>, results=[...])
7. Include RBAC report in final answer

=== COMPLIANCE RULES ===
CRITICAL: These rules are non-negotiable
- NEVER bypass RBAC checks
- NEVER return denied chunks
- ALWAYS show permission reasoning
- ALWAYS report access denials
- Log suspicious access patterns
- Timestamp all operations

If user has NO permissions for any matching documents:
Return: "Access Denied: You do not have permissions to access documents matching this query."
Include: Your CDR codes, required CDR codes, and reason for denial

=== TRANSPARENCY ===
Always show:
1. What was searched
2. What was found
3. What was filtered (and why)
4. What is being returned
5. RBAC tag analysis
6. Relevance scores
7. Any confidence issues

Example Response:
---
[THOUGHT PROCESS]
- Searched for "vacation policy" 
- Found 5 chunks (HR documents)
- User CDR: [112], Docs require: [131,132,133]
- No intersection found
- All results denied due to insufficient HR role level

[RBAC REPORT]
- Total retrieved: 5
- Access granted: 0 (0%)
- Access denied: 5 (100%)
- Reason: User CDR 112 (HR Associate) cannot access CDR tags [131,132,133]
- Recommendation: Request HR Manager or higher role

[RESULT]
Access Denied: Insufficient permissions
Your CDR: HR Associate (112)
Required CDR: HR Manager/Director (131,132,133)
---

Show thoughtful RBAC analysis in every response.
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
