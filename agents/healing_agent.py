"""
Healing Agent (REFRAG)
Autonomous system optimization and self-healing using DeepAgents
Uses: analyze_heatmap, detect_low_quality, generate_synthetic_questions, reindex_documents
"""
import json
import time
from typing import Dict, Any, List
from deepagents import create_deep_agent
from langchain_core.tools import Tool
from core.agent_utils import AgentInitializer, ToolFactory


class HealingAgent:
    """Autonomous self-healing agent for REFRAG system"""
    
    def __init__(self, services: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize HealingAgent
        
        Args:
            services: Dict with 'llm', 'vectordb', 'db' services
            config: Agent configuration
        """
        self.services = services
        self.config = config
        self.name = config.get('name', 'HealingAgent')
        self.auto_optimize = config.get('auto_optimize', True)
        
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
    
    def _create_tools(self):
        """Create healing tools with service bindings"""
        from tools.healing_tools import (
            analyze_heatmap_tool,
            detect_low_quality_tool,
            generate_synthetic_questions_tool,
            reindex_documents_tool,
            optimize_chunk_strategy_tool
        )
        from tools.common_tools import get_system_status_tool
        
        tools = [
            Tool(
                name="analyze_heatmap",
                description="Analyze query heatmap to find cold spots, poor quality, and slow queries",
                func=lambda **kwargs: analyze_heatmap_tool(self.services['db'])
            ),
            
            Tool(
                name="detect_low_quality",
                description="Detect documents with low quality scores. Args: threshold (float, optional, default=0.5)",
                func=lambda **kwargs: detect_low_quality_tool(
                    kwargs.get('threshold', 0.5), self.services['db']
                )
            ),
            
            Tool(
                name="generate_synthetic_questions",
                description="Generate synthetic questions for a document. Args: doc_id (str), count (int, optional, default=10)",
                func=lambda **kwargs: generate_synthetic_questions_tool(
                    kwargs.get('doc_id', ''), kwargs.get('count', 10), self.services['llm'], self.services['db']
                )
            ),
            
            Tool(
                name="reindex_documents",
                description="Re-chunk and re-embed documents. Args: doc_ids (list), strategy (str)",
                func=lambda **kwargs: reindex_documents_tool(
                    kwargs.get('doc_ids', []), kwargs.get('strategy', 'recursive'),
                    self.services['vectordb'],
                    self.services['db'],
                    self.services['llm']
                )
            ),
            
            Tool(
                name="optimize_chunk_strategy",
                description="Test different chunking strategies and recommend best one. Args: doc_id (str)",
                func=lambda **kwargs: optimize_chunk_strategy_tool(
                    kwargs.get('doc_id', ''),
                    self.services['vectordb'],
                    self.services['db'],
                    self.services['llm']
                )
            ),
            
            Tool(
                name="get_system_status",
                description="Get comprehensive system status and health metrics",
                func=lambda **kwargs: get_system_status_tool(
                    self.services['db'],
                    self.services['vectordb']
                )
            )
        ]
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for HealingAgent from config"""
        fallback = """You are an autonomous system healing agent for REFRAG operations.

Mission: Monitor system health, identify optimization opportunities, implement improvements.

Available tools:
- analyze_heatmap: Find performance issues
- detect_low_quality: Find low-quality documents  
- generate_synthetic_questions: Create test questions
- reindex_documents: Re-chunk and re-embed
- optimize_chunk_strategy: Test chunking strategies
- get_system_status: Check system health

Measure before/after metrics for all optimizations."""
        
        return AgentInitializer.get_agent_prompt('healing', self.prompts_config, fallback)
    
    def run_healing_cycle(self, strategies: List[str] = None) -> Dict[str, Any]:
        """
        Run autonomous healing cycle
        
        Args:
            strategies: Optional list of specific strategies to run
                       If None, runs comprehensive analysis
            
        Returns:
            Healing results with improvements
        """
        start_time = time.time()
        
        try:
            if strategies is None:
                strategies = [
                    'reindex_low_quality',
                    'add_synthetic_questions',
                    'adjust_chunk_size'
                ]
            
            request = f"""
Run a comprehensive healing cycle to optimize the RAG system.

Requested strategies: {', '.join(strategies)}

Your healing plan:
1. Use write_todos with a list of steps to plan the healing workflow: write_todos(["Get baseline", "Analyze heatmap", "Detect issues", "Apply optimizations", "Measure improvement"])
2. Get current system status as baseline
3. Analyze query heatmap for issues
4. Detect low-quality embeddings (threshold: 0.5)
5. For each issue found:
   - Choose appropriate healing strategy
   - Measure before metrics
   - Apply optimization
   - Measure after metrics
   - Calculate improvement delta
6. Generate synthetic questions for problematic documents
7. Provide comprehensive healing report with:
   - Total optimizations performed
   - Documents improved
   - Improvement percentages
   - Recommendations for next cycle

Focus on high-impact improvements that will benefit users.
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
            
            # Log healing operation
            self.services['db'].log_healing_operation(
                strategy='comprehensive_cycle',
                target_docs=[],
                reason='Scheduled healing cycle',
                actions_taken={'strategies': strategies, 'response': response},
                before_metrics={'timestamp': start_time},
                after_metrics={'timestamp': time.time()},
                improvement_delta=0.0  # TODO: Calculate from agent's analysis
            )
            
            # Log agent operation
            self.services['db'].log_agent_operation(
                agent_name=self.name,
                operation_type='healing',
                query='Run healing cycle',
                final_response=response,
                response_time_ms=execution_time_ms,
                metadata={'strategies': strategies}
            )
            
            return {
                "success": True,
                "strategies": strategies,
                "execution_time_ms": execution_time_ms,
                "response": response,
                "messages": len(messages)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def analyze_system_health(self) -> Dict[str, Any]:
        """
        Analyze system health without making changes
        
        Returns:
            Health analysis report
        """
        try:
            request = """
Perform a comprehensive system health analysis:

1. Get current system status
2. Analyze query heatmap for patterns
3. Detect low-quality embeddings
4. Review recent agent operations
5. Check token usage trends

Provide a health report with:
- Overall health score (0-100)
- Critical issues (if any)
- Warnings
- Optimization opportunities
- Recommended actions

Do NOT make any changes - analysis only.
"""
            
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": request}]
            })
            
            messages = result.get('messages', [])
            final_message = messages[-1] if messages else {}
            response = final_message.get('content', 'No response')
            
            return {
                "success": True,
                "health_report": response
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def optimize_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Optimize a specific document
        
        Args:
            doc_id: Document ID to optimize
            
        Returns:
            Optimization results
        """
        try:
            request = f"""
Optimize this specific document:

Document ID: {doc_id}

Steps:
1. Analyze current chunking strategy and quality
2. Test alternative chunking strategies
3. Recommend and apply best strategy
4. Generate synthetic questions for testing
5. Measure improvement

Provide before/after metrics.
"""
            
            result = self.agent.invoke({
                "messages": [{"role": "user", "content": request}]
            })
            
            messages = result.get('messages', [])
            final_message = messages[-1] if messages else {}
            response = final_message.get('content', 'No response')
            
            # Log operation
            self.services['db'].log_healing_operation(
                strategy='optimize_document',
                target_docs=[doc_id],
                reason=f'Manual optimization request for {doc_id}',
                actions_taken={'response': response},
                before_metrics={},
                after_metrics={},
                improvement_delta=0.0
            )
            
            return {
                "success": True,
                "doc_id": doc_id,
                "response": response
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
