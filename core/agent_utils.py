"""
Agent Utilities
Shared utilities for agent initialization, tool binding, and prompt loading
Reduces code duplication across agents
"""
import json
from typing import Dict, Any, Callable, List, Optional
from langchain_core.tools import Tool
from core.config.loader import load_all_configs


class ToolFactory:
    """Factory for creating and binding tools with services"""
    
    @staticmethod
    def extract_tool_func(tool_decorated):
        """Extract underlying function from @tool decorated object"""
        return tool_decorated.func if hasattr(tool_decorated, 'func') else tool_decorated
    
    @staticmethod
    def create_tool(name: str, description: str, func: Callable) -> Tool:
        """Create a Tool object with name, description, and function"""
        return Tool(name=name, description=description, func=func)
    
    @staticmethod
    def bind_service_to_func(func: Callable, service_dict: Dict[str, Any]) -> Callable:
        """
        Bind services to a function via partial application.
        
        Example:
            def vector_search_tool(query, top_k, llm_service, vectordb_service):
                ...
            
            bound_func = bind_service_to_func(vector_search_tool, {'llm': llm, 'vectordb': vdb})
            # Now call: bound_func(query="test", top_k=10)
        """
        def wrapper(**kwargs):
            return func(**kwargs, **service_dict)
        return wrapper


class AgentInitializer:
    """Base class for agent initialization with shared logic"""
    
    @staticmethod
    def load_prompts_config() -> Dict[str, Any]:
        """Load prompts from config, with fallback to empty dict"""
        try:
            return load_all_configs('config').get('prompts', {})
        except:
            return {}
    
    @staticmethod
    def get_agent_prompt(agent_type: str, prompts_config: Dict[str, Any], 
                        fallback_prompt: str = "") -> str:
        """
        Get agent system prompt from config with fallback.
        
        Args:
            agent_type: 'orchestrator', 'retrieval_agent', 'ingestion_agent', 'healing_agent'
            prompts_config: Loaded prompts configuration
            fallback_prompt: Fallback prompt if not in config
            
        Returns:
            System prompt string
        """
        agent_key = agent_type if agent_type.endswith('_agent') else f"{agent_type}_agent"
        
        # Try config first
        prompt = prompts_config.get(agent_key, {}).get('system_prompt')
        if prompt:
            return prompt
        
        # Use fallback
        return fallback_prompt or f"You are a {agent_type} agent."
    
    @staticmethod
    def generate_dynamic_prompt(agent_type: str, system_metrics: Dict[str, Any],
                               user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate dynamic prompt based on system metrics and context.
        Used by MasterOrchestrator to adapt prompts in real-time.
        
        Args:
            agent_type: Type of agent to generate prompt for
            system_metrics: Current system metrics (from get_system_status)
            user_context: Optional user/task context
            
        Returns:
            Dynamically generated prompt
        """
        base_prompt = f"You are the {agent_type} in an autonomous RAG system.\n\n"
        
        # Add system context
        context = f"""=== CURRENT SYSTEM STATE ===
- Total documents: {system_metrics.get('documents', {}).get('total_documents', 0)}
- Total queries processed: {system_metrics.get('queries', {}).get('total_queries', 0)}
- Avg response time: {system_metrics.get('queries', {}).get('avg_execution_time_ms', 0):.0f}ms
- System health: {"Optimal" if system_metrics.get('health', 'unknown') == 'healthy' else "Degraded"}
"""
        
        # Add agent-specific guidance
        if agent_type == 'orchestrator':
            guidance = """
=== REAL-TIME DECISION GUIDANCE ===
Based on current metrics:
- If avg response time > 5000ms: Consider triggering healing
- If document count > 100: May need query optimization
- If query volume high: Monitor resource usage

Always prioritize system stability and user privacy.
"""
        elif agent_type == 'retrieval_agent':
            guidance = """
=== REAL-TIME CONTEXT ===
- Current system load: {'high' if system_metrics.get('queries', {}).get('total_queries', 0) > 50 else 'normal'}
- Focus on accuracy and RBAC compliance
- Report all access control decisions transparently
"""
        elif agent_type == 'ingestion_agent':
            guidance = """
=== REAL-TIME CONTEXT ===
- Documents in system: {system_metrics.get('documents', {}).get('total_documents', 0)}
- Maintain consistent quality standards
- Verify RBAC classification before storage
"""
        elif agent_type == 'healing_agent':
            guidance = f"""
=== REAL-TIME OPTIMIZATION TARGETS ===
- Target avg response time: <3000ms (currently {system_metrics.get('queries', {}).get('avg_execution_time_ms', 0):.0f}ms)
- Focus areas: {system_metrics.get('focus_areas', ['general_optimization'])}
- Priority: High-impact optimizations only
"""
        else:
            guidance = ""
        
        # Add user context if provided
        user_guidance = ""
        if user_context:
            if user_context.get('priority'):
                user_guidance += f"\nUser Priority: {user_context['priority']}\n"
            if user_context.get('deadline'):
                user_guidance += f"Time-sensitive task (complete by: {user_context['deadline']})\n"
        
        return base_prompt + context + guidance + user_guidance
    
    @staticmethod
    def generate_action_items(agent_type: str, system_metrics: Dict[str, Any],
                             current_status: Optional[str] = None) -> List[str]:
        """
        Generate action items based on system metrics and agent type.
        Used by MasterOrchestrator for dynamic task planning.
        
        Args:
            agent_type: Type of agent
            system_metrics: Current system metrics
            current_status: Optional current status description
            
        Returns:
            List of action items for the agent to consider
        """
        actions = []
        
        if agent_type == 'orchestrator':
            # Orchestrator action items
            if system_metrics.get('queries', {}).get('avg_execution_time_ms', 0) > 5000:
                actions.append("URGENT: Average query time > 5s - analyze and consider healing")
            if system_metrics.get('documents', {}).get('total_documents', 0) > 100:
                actions.append("Consider reindexing: Document count exceeds 100")
            if system_metrics.get('rbac', {}).get('total_users', 0) > 50:
                actions.append("REVIEW: 50+ users in system - ensure RBAC audit trail current")
            if system_metrics.get('healing', {}).get('total_healing_operations', 0) == 0:
                actions.append("PROACTIVE: No healing cycles yet - consider running baseline optimization")
        
        elif agent_type == 'healing_agent':
            # Healing agent action items
            actions.append("Analyze query heatmap for cold spots")
            actions.append("Detect and remediate low-quality embeddings")
            if system_metrics.get('queries', {}).get('total_queries', 0) > 30:
                actions.append("Generate synthetic questions for underperforming documents")
            actions.append("Measure before/after metrics for all optimizations")
            actions.append("Report improvement percentages")
        
        elif agent_type == 'retrieval_agent':
            # Retrieval agent action items
            actions.append("Execute vector search with high relevance threshold")
            actions.append("Strictly enforce RBAC - check permissions before returning results")
            actions.append("Report all permission denials with reasoning")
            actions.append("Return sources with confidence scores")
            if system_metrics.get('queries', {}).get('total_queries', 0) > 100:
                actions.append("PERFORMANCE: Optimize reranking for speed")
        
        elif agent_type == 'ingestion_agent':
            # Ingestion agent action items
            actions.append("Chunk documents semantically for better retrieval")
            actions.append("Extract accurate metadata (title, summary, keywords)")
            actions.append("Classify RBAC tags based on content sensitivity")
            actions.append("Verify embedding quality before storage")
            if system_metrics.get('documents', {}).get('total_documents', 0) > 50:
                actions.append("Monitor ingestion speed - optimize if > 2s per document")
        
        return actions


class PromptBuilder:
    """Build structured prompts with consistent formatting"""
    
    @staticmethod
    def build_tool_list_prompt(tools: List[Dict[str, str]]) -> str:
        """
        Build formatted tool list for prompts.
        
        Args:
            tools: List of tool dicts with 'name' and 'description'
            
        Returns:
            Formatted tool list string
        """
        lines = ["=== AVAILABLE TOOLS ==="]
        for tool in tools:
            lines.append(f"- {tool['name']}: {tool['description']}")
        return "\n".join(lines)
    
    @staticmethod
    def build_workflow_prompt(steps: List[str], description: str = "") -> str:
        """
        Build formatted workflow for prompts.
        
        Args:
            steps: List of workflow steps
            description: Optional description
            
        Returns:
            Formatted workflow string
        """
        lines = []
        if description:
            lines.append(f"{description}")
        lines.append("=== WORKFLOW ===")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
        return "\n".join(lines)
    
    @staticmethod
    def build_rules_prompt(rules: List[str], title: str = "RULES") -> str:
        """
        Build formatted rules for prompts.
        
        Args:
            rules: List of rules
            title: Title for rules section
            
        Returns:
            Formatted rules string
        """
        lines = [f"=== {title} ==="]
        for rule in rules:
            lines.append(f"[OK] {rule}")
        return "\n".join(lines)
