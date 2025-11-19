"""
Master Orchestrator
Top-level agent that coordinates Ingestion, Retrieval, and Healing agents
Uses DeepAgents with write_todos for complex workflow planning
"""
import json
from typing import Dict, Any, Optional
from deepagents import create_deep_agent
from langchain_core.tools import Tool

from .ingestion_agent import IngestionAgent
from .retrieval_agent import RetrievalAgent
from .healing_agent import HealingAgent


class MasterOrchestrator:
    """Top-level orchestrator for autonomous RAG system"""
    
    def __init__(self, services: Dict[str, Any], configs: Dict[str, Any]):
        """
        Initialize MasterOrchestrator
        
        Args:
            services: Dict with 'llm', 'vectordb', 'db' services
            configs: Configuration dictionaries
        """
        self.services = services
        self.configs = configs
        self.name = "MasterOrchestrator"
        
        # Initialize specialized agents
        self.ingestion_agent = IngestionAgent(
            services=services,
            config=configs.get('agent', {}).get('ingestion_agent', {})
        )
        
        self.retrieval_agent = RetrievalAgent(
            services=services,
            config=configs.get('agent', {}).get('retrieval_agent', {})
        )
        
        self.healing_agent = HealingAgent(
            services=services,
            config=configs.get('agent', {}).get('healing_agent', {})
        )
        
        # Create orchestrator tools
        self.tools = self._create_tools()
        
        # Create DeepAgent for orchestration
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=services['llm'].get_model()
        )
        
        print(f"[{self.name}] Initialized with 3 specialized agents")
    
    def _create_tools(self):
        """Create orchestration tools"""
        from tools.common_tools import get_system_status_tool
        
        # Tool wrappers that handle responses
        def ingest_wrapper(**kwargs):
            result = self.ingestion_agent.ingest_document(
                kwargs.get('file_path', ''), 
                kwargs.get('metadata')
            )
            # After ingestion, optionally spawn healing for quick test
            if result.get('success') and kwargs.get('run_quick_test', True):
                print(f"[{self.name}] Post-ingestion quick test - spawning RetrievalAgent...")
                try:
                    test_query = kwargs.get('test_query', 'What documents are available?')
                    test_user = kwargs.get('test_user', 'system@test.com')
                    retrieval_result = self.retrieval_agent.process_query(test_query, test_user, use_planning=False)
                    result['quick_test'] = retrieval_result
                except Exception as e:
                    result['quick_test_error'] = str(e)
            return json.dumps(result)
        
        def retrieval_wrapper(**kwargs):
            result = self.retrieval_agent.process_query(
                kwargs.get('query', ''), 
                kwargs.get('user_id', ''), 
                kwargs.get('use_planning', False)
            )
            # If slow response detected, spawn healing
            if result.get('slow_response', False):
                print(f"[{self.name}] Slow response detected - spawning HealingAgent...")
                try:
                    healing_result = self.healing_agent.run_healing_cycle()
                    result['auto_healing_triggered'] = True
                    result['healing_result'] = healing_result
                except Exception as e:
                    result['healing_error'] = str(e)
            return json.dumps(result)
        
        def healing_wrapper(**kwargs):
            result = self.healing_agent.run_healing_cycle()
            return json.dumps(result)
        
        tools = [
            Tool(
                name="spawn_ingestion_agent",
                description="Spawn IngestionAgent for document processing. Args: file_path (str), metadata (dict), test_query (str), run_quick_test (bool)",
                func=ingest_wrapper
            ),
            
            Tool(
                name="spawn_retrieval_agent",
                description="Spawn RetrievalAgent for query processing. Args: query (str), user_id (str), use_planning (bool)",
                func=retrieval_wrapper
            ),
            
            Tool(
                name="spawn_healing_agent",
                description="Spawn HealingAgent for system optimization and REFRAG",
                func=healing_wrapper
            ),
            
            Tool(
                name="analyze_system_health",
                description="Get comprehensive system health analysis",
                func=lambda **kwargs: json.dumps(
                    self.healing_agent.analyze_system_health()
                )
            ),
            
            Tool(
                name="get_system_status",
                description="Get current system status and statistics",
                func=lambda **kwargs: get_system_status_tool(
                    self.services['db'],
                    self.services['vectordb']
                )
            )
        ]
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for MasterOrchestrator"""
        return """You are the Master Orchestrator for an autonomous RAG system with REFRAG self-healing capabilities.

=== CORE RESPONSIBILITIES ===
1. Analyze user requests and dynamically spawn appropriate subagents
2. Coordinate complex multi-agent workflows and parallel processing
3. Monitor performance and trigger auto-healing when needed
4. Make intelligent decisions about which agents to deploy
5. Optimize resource usage through intelligent agent scheduling

=== AUTONOMOUS SUBAGENTS ===
1. **IngestionAgent** (Document Processing)
   - Handles: chunking, metadata extraction, RBAC classification, embedding generation
   - Auto-triggers: Quick retrieval test after ingestion
   - Monitor: Success rate, ingestion time
   
2. **RetrievalAgent** (Query Processing with RBAC)
   - Handles: Vector search, permission checking, answer synthesis, transparency
   - Auto-triggers: HealingAgent if response time > 10 seconds
   - Monitor: Response time, accuracy, permission denials
   
3. **HealingAgent** (System Optimization - REFRAG)
   - Handles: Performance optimization, synthetic question generation, quality improvement
   - Auto-triggers: After slow queries or periodic maintenance
   - Monitor: System health, index quality, response times

=== AVAILABLE TOOLS ===
Tools that spawn subagents dynamically:
- spawn_ingestion_agent: Deploy IngestionAgent with auto-testing
- spawn_retrieval_agent: Deploy RetrievalAgent with auto-healing
- spawn_healing_agent: Deploy HealingAgent for optimization
- analyze_system_health: Get comprehensive health metrics
- get_system_status: Get current system statistics

=== INTELLIGENT ROUTING ===
Document-related requests:
  → spawn_ingestion_agent (with run_quick_test=true)
  → Automatically tests retrieval after ingestion
  
Query/Retrieval requests:
  → spawn_retrieval_agent
  → Automatically triggers healing if slow (>10s)
  
Performance/Health requests:
  → analyze_system_health
  → spawn_healing_agent if issues detected

Complex Multi-Step Workflows:
  → Use write_todos to plan steps
  → Use spawn_* tools for each step
  → Coordinate results and next actions

=== AUTO-HEALING TRIGGERS ===
1. **Slow Query** (>10 seconds)
   → RetrievalAgent detects → Auto-spawns HealingAgent
   
2. **Post-Ingestion**
   → IngestionAgent completes → Auto-runs quick test query
   → If test fails → Auto-spawns HealingAgent
   
3. **Health Monitoring**
   → Periodically check system_health
   → If degradation detected → Spawn healing cycle

=== STRATEGIC DECISIONS ===
When to spawn multiple agents:
- After bulk ingestion: spawn_ingestion_agent + monitor with get_system_status
- During high load: spawn_healing_agent proactively
- Complex workflows: parallelize with write_todos + spawn_* tools

When to NOT spawn healing:
- Single slow query (might be legitimate)
- System under normal load
- Recent healing cycle completed

=== WORKFLOW EXAMPLES ===

**Workflow 1: Ingest Document + Quick Test**
1. spawn_ingestion_agent(file_path, run_quick_test=true, test_query="...")
2. Agent automatically runs test query after ingestion
3. If test fails, agents coordinate healing
4. Return results with test status

**Workflow 2: User Query with Auto-Healing**
1. spawn_retrieval_agent(query, user_id)
2. If response time > 10s, RetrievalAgent auto-triggers healing
3. Return query results + healing status

**Workflow 3: System Health Check & Optimization**
1. analyze_system_health()
2. If issues detected, spawn_healing_agent()
3. Monitor healing progress
4. Return health report + healing results

Always balance autonomy with resource efficiency. Make smart decisions about which agents to spawn and when.
   - Agent handles: search, permission check, answer synthesis

3. **System Optimization**:
   - Route to HealingAgent
   - Agent handles: heatmap analysis, reindexing, quality improvement

4. **Complex Multi-Step**:
   - Use write_todos to plan workflow
   - Use task to spawn parallel agents
   - Coordinate results

Always consider RBAC implications and system capacity before routing tasks.
"""
    
    def process_request(self, request: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Process any type of request - ingestion, retrieval, or healing
        
        Args:
            request: User request text
            context: Optional context (user_id, file_path, etc.)
            
        Returns:
            Processing results
        """
        try:
            context_str = json.dumps(context) if context else "None"
            
            orchestrator_request = f"""
Process this request:

Request: {request}

Context: {context_str}

Instructions:
1. Analyze the request type (ingestion, retrieval, or healing)
2. Route to the appropriate specialized agent
3. If complex, use write_todos to plan the workflow
4. Return clear results to the user

Remember:
- For document ingestion: route_to_ingestion
- For user queries: route_to_retrieval (include user_id for RBAC)
- For system optimization: route_to_healing
- For complex tasks: use write_todos and task spawning
"""
            
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": orchestrator_request}]
            })
            
            messages = result.get('messages', [])
            final_message = messages[-1] if messages else {}
            response = final_message.get('content', 'No response')
            
            # Log orchestration
            self.services['db'].log_agent_operation(
                agent_name=self.name,
                operation_type='orchestration',
                query=request,
                final_response=response,
                metadata=context
            )
            
            return {
                "success": True,
                "request": request,
                "response": response,
                "messages": len(messages)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def ingest_document(self, file_path: str, metadata: Dict = None) -> Dict[str, Any]:
        """Direct document ingestion"""
        return self.ingestion_agent.ingest_document(file_path, metadata)
    
    def query(self, query: str, user_id: str, use_planning: bool = False) -> Dict[str, Any]:
        """Direct query processing"""
        return self.retrieval_agent.process_query(query, user_id, use_planning)
    
    def heal(self) -> Dict[str, Any]:
        """Direct healing cycle"""
        return self.healing_agent.run_healing_cycle()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        from tools.common_tools import get_system_status_tool
        
        status_json = get_system_status_tool(
            self.services['db'],
            self.services['vectordb']
        )
        
        return json.loads(status_json)
