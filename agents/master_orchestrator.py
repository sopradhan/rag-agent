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
        
        tools = [
            Tool(
                name="route_to_ingestion",
                description="Route document ingestion tasks to IngestionAgent. Args: file_path (str), metadata (dict, optional)",
                func=lambda **kwargs: json.dumps(
                    self.ingestion_agent.ingest_document(kwargs.get('file_path', ''), kwargs.get('metadata'))
                )
            ),
            
            Tool(
                name="route_to_retrieval",
                description="Route queries to RetrievalAgent. Args: query (str), user_id (str), use_planning (bool, optional)",
                func=lambda **kwargs: json.dumps(
                    self.retrieval_agent.process_query(kwargs.get('query', ''), kwargs.get('user_id', ''), kwargs.get('use_planning', False))
                )
            ),
            
            Tool(
                name="route_to_healing",
                description="Route optimization tasks to HealingAgent",
                func=lambda **kwargs: json.dumps(
                    self.healing_agent.run_healing_cycle()
                )
            ),
            
            Tool(
                name="analyze_system_health",
                description="Get comprehensive system health analysis from HealingAgent",
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
        return """You are the Master Orchestrator for an autonomous RAG system with REFRAG capabilities.

Your role:
1. Understand user requests and route to appropriate specialized agents
2. Coordinate complex multi-agent workflows
3. Use write_todos to plan sophisticated operations
4. Monitor overall system health
5. Make strategic decisions about system optimization

Available Agents:
1. **IngestionAgent**: Document processing, chunking, RBAC classification, embedding
   - Use for: Adding new documents, batch ingestion, document updates
   
2. **RetrievalAgent**: Query processing with RBAC enforcement
   - Use for: Answering user questions, information retrieval
   
3. **HealingAgent**: System optimization and self-healing (REFRAG)
   - Use for: Performance improvements, quality optimization, synthetic question generation

Available tools:
- route_to_ingestion: Send ingestion tasks to IngestionAgent
- route_to_retrieval: Send queries to RetrievalAgent
- route_to_healing: Trigger healing cycles
- analyze_system_health: Get health analysis
- get_system_status: Get current statistics
- write_todos: Plan complex multi-step workflows
- task: Spawn specialized subagents for parallel processing

Decision Logic:
- Document-related requests → IngestionAgent
- Question/query requests → RetrievalAgent
- Performance/optimization requests → HealingAgent
- Complex workflows → Use write_todos + task spawning

Example workflows:

1. **New Document Ingestion**:
   - Route to IngestionAgent with file path
   - Agent handles: chunking, metadata, RBAC, embedding

2. **User Query**:
   - Route to RetrievalAgent with query + user_id
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
