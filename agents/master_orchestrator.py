"""
Master Orchestrator
Top-level agent that coordinates Ingestion, Retrieval, and Healing agents
Uses DeepAgents with write_todos for complex workflow planning
Includes parameter management and runtime optimization
"""
import json
from typing import Dict, Any, Optional
from deepagents import create_deep_agent
from langchain_core.tools import Tool
from core.agent_utils import AgentInitializer, ToolFactory
from core.parameter_manager import get_parameter_manager

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
        
        # Get parameter manager for runtime coordination
        self.param_manager = get_parameter_manager()
        
        # Load configuration with system prompts
        self.prompts_config = AgentInitializer.load_prompts_config()
        
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
        
        print(f"[{self.name}] Initialized with 3 specialized agents")
    
    def _create_tools(self):
        """Create orchestration tools"""
        from tools.common_tools import get_system_status_tool
        
        # Parameter management tools
        def get_parameter_status():
            """Get current parameter configuration"""
            rag_params = self.param_manager.get_rag_params()
            llm_params = self.param_manager.get_llm_params()
            return json.dumps({
                "rag_parameters": rag_params,
                "llm_parameters": llm_params,
                "profiles": ["speed", "accuracy", "balanced", "resource_limited", "high_precision"]
            })
        
        def apply_parameter_profile(profile_name: str):
            """Apply a predefined parameter profile"""
            try:
                self.param_manager.apply_profile(profile_name)
                rag_params = self.param_manager.get_rag_params()
                llm_params = self.param_manager.get_llm_params()
                return json.dumps({
                    "success": True,
                    "profile": profile_name,
                    "rag_parameters": rag_params,
                    "llm_parameters": llm_params
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})
        
        def set_parameter(param_name: str, value: Any):
            """Manually set a parameter value"""
            try:
                # Try RAG parameter first
                try:
                    self.param_manager.set_rag_param(param_name, value)
                    param_type = "rag"
                except ValueError:
                    # Try LLM parameter
                    self.param_manager.set_llm_param(param_name, value)
                    param_type = "llm"
                
                return json.dumps({
                    "success": True,
                    "parameter": param_name,
                    "type": param_type,
                    "value": value
                })
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})
        
        # Tool wrappers with spawn logging
        def ingest_wrapper(**kwargs):
            self.services['db'].log_agent_spawn(self.name, 'IngestionAgent', 'Document ingestion requested')
            return json.dumps(self.ingestion_agent.ingest_document(
                kwargs.get('file_path', ''), kwargs.get('metadata')))
        
        def retrieval_wrapper(**kwargs):
            self.services['db'].log_agent_spawn(self.name, 'RetrievalAgent', f"Query: {kwargs.get('query', '')}")
            return json.dumps(self.retrieval_agent.process_query(
                kwargs.get('query', ''), kwargs.get('user_id', ''), 
                kwargs.get('use_planning', False)))
        
        def healing_wrapper(**kwargs):
            self.services['db'].log_agent_spawn(self.name, 'HealingAgent', 'System healing cycle requested')
            return json.dumps(self.healing_agent.run_healing_cycle())
        
        tools = [
            # Agent spawning tools
            ToolFactory.create_tool("spawn_ingestion_agent",
                "Spawn IngestionAgent for document processing", ingest_wrapper),
            ToolFactory.create_tool("spawn_retrieval_agent",
                "Spawn RetrievalAgent for query processing", retrieval_wrapper),
            ToolFactory.create_tool("spawn_healing_agent",
                "Spawn HealingAgent for system optimization", healing_wrapper),
            
            # System analysis tools
            ToolFactory.create_tool("analyze_system_health",
                "Get comprehensive system health analysis",
                lambda: json.dumps(self.healing_agent.analyze_system_health())),
            ToolFactory.create_tool("get_system_status",
                "Get current system status and statistics",
                lambda: get_system_status_tool(self.services['db'], self.services['vectordb'])),
            
            # Parameter management tools
            ToolFactory.create_tool("get_parameter_status",
                "Get current LLM and RAG parameter configuration",
                get_parameter_status),
            ToolFactory.create_tool("apply_parameter_profile",
                "Apply a predefined parameter profile (speed, accuracy, balanced, resource_limited, high_precision)",
                apply_parameter_profile),
            ToolFactory.create_tool("set_parameter",
                "Manually set a specific parameter value",
                set_parameter),
        ]
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for MasterOrchestrator from config"""
        fallback = """You are the Master Orchestrator for an autonomous RAG system.

Responsibilities:
1. Route ingestion requests to IngestionAgent
2. Route query requests to RetrievalAgent
3. Decide when system optimization (HealingAgent) is needed
4. Monitor system health and performance
5. Manage LLM and RAG parameters for runtime optimization

Agents are independent. You make all spawning decisions.

Available agent spawning tools:
- spawn_ingestion_agent(file_path, metadata)
- spawn_retrieval_agent(query, user_id)
- spawn_healing_agent()

Available system analysis tools:
- analyze_system_health()
- get_system_status()

Available parameter management tools:
- get_parameter_status() - Check current LLM/RAG parameters
- apply_parameter_profile(profile) - Apply one of: speed, accuracy, balanced, resource_limited, high_precision
- set_parameter(name, value) - Manually adjust specific parameter

Parameter optimization guidelines:
- Use 'speed' profile when response time is critical
- Use 'accuracy' profile when quality is important
- Use 'balanced' profile as default
- Use 'resource_limited' when system is under heavy load
- Use 'high_precision' for healing operations

Always report what you're doing and why."""
        
        return AgentInitializer.get_agent_prompt('orchestrator', self.prompts_config, fallback)
    
    def get_dynamic_prompt(self, target_agent: str, user_context: Optional[Dict] = None) -> str:
        """
        Generate dynamic prompt for target agent based on current system state.
        
        Args:
            target_agent: 'orchestrator', 'retrieval_agent', 'ingestion_agent', 'healing_agent'
            user_context: Optional user context (priority, deadline, etc)
            
        Returns:
            Dynamically generated prompt
        """
        system_metrics = json.loads(self._tools_by_name()['get_system_status']())
        return AgentInitializer.generate_dynamic_prompt(target_agent, system_metrics, user_context)
    
    def get_action_items(self, target_agent: str) -> list:
        """
        Get action items for target agent based on current system state.
        
        Args:
            target_agent: 'orchestrator', 'retrieval_agent', 'ingestion_agent', 'healing_agent'
            
        Returns:
            List of recommended action items
        """
        system_metrics = json.loads(self._tools_by_name()['get_system_status']())
        return AgentInitializer.generate_action_items(target_agent, system_metrics)
    
    def _tools_by_name(self) -> Dict[str, Any]:
        """Create dict of tool name to function for easy access"""
        return {tool.name: tool.func for tool in self.tools}
    
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
