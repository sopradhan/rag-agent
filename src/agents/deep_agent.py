"""
DeepAgent Base Implementation
Provides the foundation for creating agents with memory, tools, and planning.
Includes agentic spawning and delegation capabilities.
"""

from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
import uuid
import json
from datetime import datetime


class Memory:
    """Agent memory system."""
    
    def __init__(self, backend: str = "in-memory"):
        self.backend = backend
        self.storage: List[Dict[str, Any]] = []
    
    def add(self, entry: Dict[str, Any]):
        """Add entry to memory."""
        entry["timestamp"] = datetime.now().isoformat()
        entry["id"] = str(uuid.uuid4())
        self.storage.append(entry)
    
    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get n most recent entries."""
        return self.storage[-n:]
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search memory (simple implementation)."""
        results = []
        query_lower = query.lower()
        for entry in self.storage:
            entry_str = json.dumps(entry).lower()
            if query_lower in entry_str:
                results.append(entry)
        return results
    
    def clear(self):
        """Clear memory."""
        self.storage.clear()


class DeepAgent(ABC):
    """Base DeepAgent class with planning, memory, tool execution, and chain-of-thought reasoning."""
    
    def __init__(
        self,
        name: str,
        tools: Optional[List[Callable]] = None,
        memory_backend: str = "in-memory",
        config: Optional[Dict[str, Any]] = None,
        parent_agent: Optional['DeepAgent'] = None
    ):
        self.name = name
        self.tools = tools or []
        self.memory = Memory(backend=memory_backend)
        self.config = config or {}
        self.agent_id = str(uuid.uuid4())
        self.cot_enabled = config.get("cot_enabled", True) if config else True
        self.cot_iterations = config.get("cot_iterations", 5) if config else 5
        
        # Agentic spawning capabilities
        self.parent_agent = parent_agent
        self.spawned_agents: Dict[str, 'DeepAgent'] = {}
        self.agent_registry: Dict[str, 'DeepAgent'] = {}
        self.execution_results: List[Dict[str, Any]] = []
    
    def run(self, *args, **kwargs) -> Any:
        """Execute agent with given inputs using chain-of-thought reasoning."""
        self.memory.add({
            "type": "run_start",
            "agent": self.name,
            "args": str(args)[:200],
            "kwargs": str(kwargs)[:200],
            "cot_enabled": self.cot_enabled
        })
        
        try:
            # Use chain-of-thought if enabled
            if self.cot_enabled:
                result = self._execute_with_cot(*args, **kwargs)
            else:
                result = self._execute(*args, **kwargs)
            
            self.memory.add({
                "type": "run_success",
                "agent": self.name,
                "result": str(result)[:200] if result else "No result"
            })
            
            return result
        except Exception as e:
            self.memory.add({
                "type": "run_error",
                "agent": self.name,
                "error": str(e)
            })
            raise
    
    def _execute_with_cot(self, *args, **kwargs) -> Any:
        """
        Execute with chain-of-thought reasoning:
        1. THINK: Initial analysis and planning
        2. EVALUATE: Execute and assess results
        3. RETHINK: Refine based on evaluation (up to 5 iterations)
        """
        # Phase 1: THINK - Initial analysis
        initial_thinking = self._think(*args, **kwargs)
        self.memory.add({
            "type": "cot_think",
            "agent": self.name,
            "iteration": 0,
            "thinking": initial_thinking
        })
        
        # Phase 2: EVALUATE & RETHINK loop
        current_result = initial_thinking
        best_result = current_result
        best_score = 0.0
        
        for iteration in range(1, self.cot_iterations + 1):
            # Execute based on current thinking
            evaluation = self._evaluate(current_result, *args, **kwargs)
            score = evaluation.get("score", 0.0)
            
            self.memory.add({
                "type": "cot_evaluate",
                "agent": self.name,
                "iteration": iteration,
                "score": score,
                "feedback": evaluation.get("feedback", "")
            })
            
            # Track best result
            if score > best_score:
                best_score = score
                best_result = evaluation.get("result", current_result)
            
            # Check if we should continue
            if evaluation.get("sufficient", False):
                self.memory.add({
                    "type": "cot_converged",
                    "agent": self.name,
                    "iteration": iteration,
                    "reason": "Sufficient score reached"
                })
                break
            
            # Rethink based on feedback
            rethinking = self._rethink(
                current_result,
                evaluation.get("feedback", ""),
                iteration,
                *args,
                **kwargs
            )
            
            self.memory.add({
                "type": "cot_rethink",
                "agent": self.name,
                "iteration": iteration,
                "rethinking": rethinking
            })
            
            current_result = rethinking
        
        # Return best result found
        final_result = best_result if best_score > 0 else current_result
        
        self.memory.add({
            "type": "cot_complete",
            "agent": self.name,
            "total_iterations": self.cot_iterations,
            "best_score": best_score,
            "final_result": str(final_result)[:200]
        })
        
        return final_result
    
    def _think(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Phase 1: THINK - Initial analysis and problem decomposition.
        Default implementation - override in subclasses for custom logic.
        """
        return {
            "phase": "think",
            "input_analysis": f"Analyzing {len(args)} args and {len(kwargs)} kwargs",
            "approach": "Will execute and evaluate iteratively",
            "confidence": 0.5
        }
    
    def _evaluate(self, current_result: Any, *args, **kwargs) -> Dict[str, Any]:
        """
        Phase 2: EVALUATE - Assess current results and provide feedback.
        Returns dict with keys: score (0-1), feedback (str), sufficient (bool), result (Any)
        Default implementation - override in subclasses for custom evaluation.
        """
        # Execute once if we haven't yet
        if isinstance(current_result, dict) and current_result.get("phase") == "think":
            try:
                result = self._execute(*args, **kwargs)
                score = 0.8 if result else 0.3
                sufficient = bool(result)
            except Exception as e:
                result = None
                score = 0.2
                sufficient = False
        else:
            result = current_result
            score = 0.7 if result else 0.3
            sufficient = bool(result)
        
        return {
            "score": score,
            "feedback": "Execution completed" if sufficient else "Need refinement",
            "sufficient": sufficient,
            "result": result
        }
    
    def _rethink(
        self,
        current_result: Any,
        feedback: str,
        iteration: int,
        *args,
        **kwargs
    ) -> Any:
        """
        Phase 3: RETHINK - Refine approach based on evaluation feedback.
        Default implementation - override in subclasses for custom refinement.
        """
        # If we haven't executed yet, do it now
        if not current_result or (isinstance(current_result, dict) and current_result.get("phase") == "think"):
            try:
                return self._execute(*args, **kwargs)
            except Exception as e:
                return {"error": str(e), "iteration": iteration}
        
        # Otherwise return current result (already executed)
        return current_result
    
    @abstractmethod
    def _execute(self, *args, **kwargs) -> Any:
        """Agent-specific execution logic."""
        pass
    
    def get_memory(self) -> List[Dict[str, Any]]:
        """Get agent memory."""
        return self.memory.storage
    
    def get_cot_trace(self) -> List[Dict[str, Any]]:
        """Get chain-of-thought reasoning trace."""
        cot_types = {"cot_think", "cot_evaluate", "cot_rethink", "cot_converged", "cot_complete"}
        return [entry for entry in self.memory.storage if entry.get("type") in cot_types]
    
    def spawn_subagent(
        self,
        subagent_class: type,
        subagent_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> 'DeepAgent':
        """
        Dynamically spawn a subagent.
        
        Args:
            subagent_class: The class of the subagent to create
            subagent_name: Name for the subagent
            config: Configuration for the subagent
        
        Returns:
            The spawned subagent instance
        """
        subagent = subagent_class(
            name=subagent_name,
            tools=self.tools,
            memory_backend="in-memory",
            config=config or self.config,
            parent_agent=self
        )
        
        agent_id = subagent.agent_id
        self.spawned_agents[agent_id] = subagent
        self.agent_registry[agent_id] = subagent
        
        self.memory.add({
            "type": "agent_spawned",
            "parent": self.name,
            "parent_id": self.agent_id,
            "child": subagent_name,
            "child_id": agent_id,
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"[{self.name}] Spawned subagent: {subagent_name} ({agent_id[:8]})")
        return subagent
    
    def delegate_task(
        self,
        subagent: 'DeepAgent',
        task_description: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Delegate a task to a subagent.
        
        Args:
            subagent: The subagent to delegate to
            task_description: Description of the task
            *args: Arguments to pass to the subagent's run method
            **kwargs: Keyword arguments to pass to the subagent's run method
        
        Returns:
            Result from the subagent
        """
        self.memory.add({
            "type": "task_delegated",
            "from_agent": self.name,
            "to_agent": subagent.name,
            "task": task_description,
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"\n[{self.name}] Delegating to {subagent.name}: {task_description}")
        result = subagent.run(*args, **kwargs)
        
        self.memory.add({
            "type": "task_completed",
            "from_agent": self.name,
            "to_agent": subagent.name,
            "result_summary": str(result)[:100],
            "timestamp": datetime.now().isoformat()
        })
        
        self.execution_results.append({
            "agent": subagent.name,
            "task": task_description,
            "result": result
        })
        
        return result
    
    def report_to_parent(self, result: Dict[str, Any]) -> None:
        """
        Report execution result back to parent agent.
        
        Args:
            result: Result dictionary to report
        """
        if not self.parent_agent:
            print(f"[{self.name}] No parent agent to report to")
            return
        
        self.memory.add({
            "type": "report_sent",
            "from_agent": self.name,
            "to_parent": self.parent_agent.name,
            "result_summary": str(result)[:100],
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"\n[{self.name}] Reporting to parent: {self.parent_agent.name}")
        self.parent_agent.receive_report(self, result)
    
    def receive_report(self, subagent: 'DeepAgent', result: Dict[str, Any]) -> None:
        """
        Receive report from a subagent.
        
        Args:
            subagent: The subagent reporting
            result: The result being reported
        """
        self.memory.add({
            "type": "report_received",
            "from_agent": subagent.name,
            "from_agent_id": subagent.agent_id,
            "result_summary": str(result)[:100],
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"[{self.name}] Received report from {subagent.name}")
    
    def get_spawned_agents(self) -> List[Dict[str, Any]]:
        """Get list of spawned agents"""
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "spawned_agents": len(agent.spawned_agents)
            }
            for agent in self.spawned_agents.values()
        ]
    
    def get_agent_tree(self) -> Dict[str, Any]:
        """Get hierarchical tree of agents"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "parent": self.parent_agent.name if self.parent_agent else None,
            "spawned_agents": [child.get_agent_tree() for child in self.spawned_agents.values()],
            "total_children": len(self.spawned_agents)
        }


def create_deep_agent(
    name: str,
    agent_class: type = None,
    tools: Optional[List[Callable]] = None,
    memory_backend: str = "in-memory",
    config: Optional[Dict[str, Any]] = None
) -> DeepAgent:
    """Factory function to create DeepAgent instances."""
    if agent_class:
        return agent_class(
            name=name,
            tools=tools,
            memory_backend=memory_backend,
            config=config
        )
    
    # Create generic agent
    class GenericAgent(DeepAgent):
        def _execute(self, *args, **kwargs):
            # Execute tools in sequence
            result = args[0] if args else None
            for tool in self.tools:
                result = tool(result)
            return result
    
    return GenericAgent(
        name=name,
        tools=tools,
        memory_backend=memory_backend,
        config=config
    )
