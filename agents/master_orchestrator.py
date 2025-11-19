"""
Master Orchestrator
Top-level agent that coordinates Ingestion, Retrieval, and Healing agents
Uses DeepAgents with write_todos for complex workflow planning
"""
import json
from typing import Dict, Any, Optional
from deepagents import create_deep_agent
from langchain_core.tools import Tool
from core.config.loader import load_all_configs

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
        
        # Load configuration with system prompts
        try:
            self.prompts_config = load_all_configs('config').get('prompts', {})
        except:
            self.prompts_config = {}
        
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
        
        # Create DeepAgent for orchestration with system prompt from config
        self.agent = create_deep_agent(
            tools=self.tools,
            system_prompt=self._get_system_prompt(),
            model=services['llm'].get_model()
        )
        
        print(f"[{self.name}] Initialized with 3 specialized agents (prompts from config)")
    
    def _create_tools(self):
        """Create orchestration tools"""
        from tools.common_tools import get_system_status_tool
        
        # Tool wrappers - agents are independent, orchestrator decides when to call healing
        def ingest_wrapper(**kwargs):
            result = self.ingestion_agent.ingest_document(
                kwargs.get('file_path', ''), 
                kwargs.get('metadata')
            )
            return json.dumps(result)
        
        def retrieval_wrapper(**kwargs):
            result = self.retrieval_agent.process_query(
                kwargs.get('query', ''), 
                kwargs.get('user_id', ''), 
                kwargs.get('use_planning', False)
            )
            return json.dumps(result)
        
        def healing_wrapper(**kwargs):
            result = self.healing_agent.run_healing_cycle()
            return json.dumps(result)
        
        tools = [
            Tool(
                name="spawn_ingestion_agent",
                description="Spawn IngestionAgent for document processing. Args: file_path (str), metadata (dict, optional)",
                func=ingest_wrapper
            ),
            
            Tool(
                name="spawn_retrieval_agent",
                description="Spawn RetrievalAgent for query processing. Args: query (str), user_id (str), use_planning (bool, optional)",
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
        """Get system prompt for MasterOrchestrator from config"""
        # Try to get from config first
        if self.prompts_config.get('orchestrator', {}).get('system_prompt'):
            return self.prompts_config['orchestrator']['system_prompt']
        
        # Fallback to basic prompt
        return """You are the Master Orchestrator for an autonomous RAG system.

Your responsibilities:
1. Route ingestion requests to IngestionAgent
2. Route query requests to RetrievalAgent
3. Decide when system optimization (HealingAgent) is needed
4. Monitor system health and performance

Agents are independent - they don't auto-trigger other agents.
You make all decisions about what agents to spawn.

Available tools:
- spawn_ingestion_agent(file_path, metadata)
- spawn_retrieval_agent(query, user_id)
- spawn_healing_agent()
- analyze_system_health()
- get_system_status()

Always report clearly what you're doing and why."""
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
