"""
Parameter Manager
Dynamic LLM and RAG parameter optimization at runtime
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class RAGParameters:
    """RAG-specific parameters"""
    top_k: int = 10  # Number of results to retrieve
    similarity_threshold: float = 0.7  # Minimum similarity score
    reranker_top_n: int = 5  # Results to rerank
    chunk_size: int = 500  # Chunk size for ingestion
    chunk_overlap: int = 50  # Overlap between chunks
    max_results_to_synthesize: int = 3  # Max chunks for answer synthesis


@dataclass
class LLMParameters:
    """LLM-specific parameters"""
    temperature: float = 0.7  # Creativity (0=deterministic, 1=random)
    max_tokens: int = 512  # Maximum response length
    top_p: float = 0.9  # Nucleus sampling
    frequency_penalty: float = 0.0  # Reduce repetition
    presence_penalty: float = 0.0  # Encourage new topics


@dataclass
class PerformanceMetrics:
    """Metrics from a retrieval operation"""
    response_time_ms: float
    retrieval_accuracy: float
    rbac_denial_rate: float
    token_usage: int
    relevance_score: float
    user_satisfaction: Optional[float] = None


class ParameterProfile:
    """Predefined parameter profiles for different scenarios"""
    
    PROFILES = {
        'speed': {
            'rag': {'top_k': 5, 'similarity_threshold': 0.8, 'reranker_top_n': 3},
            'llm': {'temperature': 0.3, 'max_tokens': 256},
            'description': 'Optimized for speed - fewer results, lower latency'
        },
        'accuracy': {
            'rag': {'top_k': 20, 'similarity_threshold': 0.6, 'reranker_top_n': 10},
            'llm': {'temperature': 0.5, 'max_tokens': 1024},
            'description': 'Optimized for accuracy - more results, better quality'
        },
        'balanced': {
            'rag': {'top_k': 10, 'similarity_threshold': 0.7, 'reranker_top_n': 5},
            'llm': {'temperature': 0.7, 'max_tokens': 512},
            'description': 'Balanced between speed and accuracy'
        },
        'resource_limited': {
            'rag': {'top_k': 3, 'similarity_threshold': 0.85, 'reranker_top_n': 2},
            'llm': {'temperature': 0.4, 'max_tokens': 128},
            'description': 'Minimal resource usage - very fast, quick answers'
        },
        'high_precision': {
            'rag': {'top_k': 30, 'similarity_threshold': 0.5, 'reranker_top_n': 15},
            'llm': {'temperature': 0.3, 'max_tokens': 1024},
            'description': 'Maximum precision - deep analysis, highest quality'
        },
    }
    
    @classmethod
    def get_profile(cls, profile_name: str) -> Dict[str, Any]:
        """Get parameter profile by name"""
        return cls.PROFILES.get(profile_name, cls.PROFILES['balanced'])
    
    @classmethod
    def list_profiles(cls) -> List[str]:
        """List available profile names"""
        return list(cls.PROFILES.keys())


class ParameterManager:
    """Manage and optimize parameters at runtime"""
    
    def __init__(self):
        """Initialize parameter manager"""
        self.rag_params = RAGParameters()
        self.llm_params = LLMParameters()
        self.history: List[Dict[str, Any]] = []
        self.profile_name = 'balanced'
        self.optimization_enabled = True
    
    # ============ Current Parameter Access ============
    
    def get_rag_params(self) -> Dict[str, Any]:
        """Get current RAG parameters"""
        return asdict(self.rag_params)
    
    def get_llm_params(self) -> Dict[str, Any]:
        """Get current LLM parameters"""
        return asdict(self.llm_params)
    
    def get_all_params(self) -> Dict[str, Any]:
        """Get all current parameters"""
        return {
            'rag': self.get_rag_params(),
            'llm': self.get_llm_params(),
            'profile': self.profile_name
        }
    
    # ============ Profile-Based Configuration ============
    
    def apply_profile(self, profile_name: str):
        """Apply predefined parameter profile"""
        profile = ParameterProfile.get_profile(profile_name)
        self.profile_name = profile_name
        
        # Apply RAG parameters
        rag_overrides = profile.get('rag', {})
        for key, value in rag_overrides.items():
            if hasattr(self.rag_params, key):
                setattr(self.rag_params, key, value)
        
        # Apply LLM parameters
        llm_overrides = profile.get('llm', {})
        for key, value in llm_overrides.items():
            if hasattr(self.llm_params, key):
                setattr(self.llm_params, key, value)
        
        return {
            'profile': profile_name,
            'description': profile.get('description', ''),
            'rag': self.get_rag_params(),
            'llm': self.get_llm_params()
        }
    
    # ============ Manual Parameter Adjustment ============
    
    def set_rag_param(self, param_name: str, value: Any) -> bool:
        """Set individual RAG parameter"""
        if hasattr(self.rag_params, param_name):
            setattr(self.rag_params, param_name, value)
            return True
        return False
    
    def set_llm_param(self, param_name: str, value: Any) -> bool:
        """Set individual LLM parameter"""
        if hasattr(self.llm_params, param_name):
            setattr(self.llm_params, param_name, value)
            return True
        return False
    
    def batch_update_params(self, updates: Dict[str, Any]):
        """Update multiple parameters at once"""
        results = {}
        
        # RAG parameters
        for key, value in updates.get('rag', {}).items():
            results[f'rag.{key}'] = self.set_rag_param(key, value)
        
        # LLM parameters
        for key, value in updates.get('llm', {}).items():
            results[f'llm.{key}'] = self.set_llm_param(key, value)
        
        return results
    
    # ============ Dynamic Optimization ============
    
    def optimize_for_scenario(self, scenario: str, current_metrics: PerformanceMetrics):
        """
        Optimize parameters based on scenario and current metrics.
        
        Args:
            scenario: 'slow_response', 'low_accuracy', 'high_load', 'low_load'
            current_metrics: Current performance metrics
            
        Returns:
            Dict with parameter adjustments made
        """
        adjustments = {}
        
        if scenario == 'slow_response':
            # Query is slow - reduce computation
            if current_metrics.response_time_ms > 5000:
                adjustments['rag.top_k'] = max(3, self.rag_params.top_k - 2)
                adjustments['rag.similarity_threshold'] = min(0.95, 
                    self.rag_params.similarity_threshold + 0.1)
                adjustments['rag.reranker_top_n'] = max(2, self.rag_params.reranker_top_n - 2)
                adjustments['llm.temperature'] = max(0.2, self.llm_params.temperature - 0.1)
                adjustments['llm.max_tokens'] = max(128, self.llm_params.max_tokens - 128)
        
        elif scenario == 'low_accuracy':
            # Results are poor quality - increase search depth
            if current_metrics.retrieval_accuracy < 0.6:
                adjustments['rag.top_k'] = min(30, self.rag_params.top_k + 5)
                adjustments['rag.similarity_threshold'] = max(0.5, 
                    self.rag_params.similarity_threshold - 0.1)
                adjustments['rag.reranker_top_n'] = min(15, self.rag_params.reranker_top_n + 3)
                adjustments['llm.temperature'] = min(0.9, self.llm_params.temperature + 0.1)
        
        elif scenario == 'high_load':
            # System under stress - minimize resource usage
            adjustments['rag.top_k'] = max(3, int(self.rag_params.top_k * 0.6))
            adjustments['llm.max_tokens'] = max(128, int(self.llm_params.max_tokens * 0.5))
            adjustments['rag.reranker_top_n'] = max(2, int(self.rag_params.reranker_top_n * 0.5))
        
        elif scenario == 'low_load':
            # System has capacity - improve quality
            adjustments['rag.top_k'] = min(30, int(self.rag_params.top_k * 1.5))
            adjustments['llm.max_tokens'] = min(1024, int(self.llm_params.max_tokens * 1.5))
            adjustments['rag.reranker_top_n'] = min(15, int(self.rag_params.reranker_top_n * 1.5))
        
        # Apply adjustments
        self.batch_update_params(self._restructure_adjustments(adjustments))
        
        # Record in history
        self._record_optimization(scenario, adjustments)
        
        return adjustments
    
    def auto_optimize(self, current_metrics: PerformanceMetrics) -> Dict[str, Any]:
        """
        Automatically optimize parameters based on current metrics.
        
        Args:
            current_metrics: Current performance metrics
            
        Returns:
            Dict with optimizations applied
        """
        if not self.optimization_enabled:
            return {'enabled': False}
        
        adjustments = {}
        
        # Rule 1: Response time too high
        if current_metrics.response_time_ms > 5000:
            adjustments['scenario'] = 'slow_response'
            self.optimize_for_scenario('slow_response', current_metrics)
        
        # Rule 2: Accuracy too low
        elif current_metrics.retrieval_accuracy < 0.5:
            adjustments['scenario'] = 'low_accuracy'
            self.optimize_for_scenario('low_accuracy', current_metrics)
        
        # Rule 3: RBAC denials high (security issue)
        elif current_metrics.rbac_denial_rate > 0.5:
            # Increase similarity threshold to reduce false positives
            self.set_rag_param('similarity_threshold', 
                min(0.95, self.rag_params.similarity_threshold + 0.05))
            adjustments['scenario'] = 'high_rbac_denials'
        
        # Rule 4: Token usage high
        elif current_metrics.token_usage > 1000:
            self.set_llm_param('max_tokens', max(128, int(self.llm_params.max_tokens * 0.7)))
            adjustments['scenario'] = 'high_token_usage'
        
        adjustments['current_metrics'] = asdict(current_metrics)
        adjustments['new_params'] = self.get_all_params()
        
        return adjustments
    
    # ============ Parameter History & Learning ============
    
    def _record_optimization(self, scenario: str, adjustments: Dict[str, Any]):
        """Record optimization in history"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'scenario': scenario,
            'adjustments': adjustments,
            'params_after': self.get_all_params()
        })
    
    def get_optimization_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent optimization history"""
        return self.history[-limit:]
    
    def get_most_effective_adjustments(self) -> Dict[str, Any]:
        """Analyze history to find most effective adjustments"""
        if not self.history:
            return {}
        
        scenarios = {}
        for record in self.history:
            scenario = record['scenario']
            if scenario not in scenarios:
                scenarios[scenario] = []
            scenarios[scenario].append(record['adjustments'])
        
        return {
            'total_optimizations': len(self.history),
            'scenarios_used': list(scenarios.keys()),
            'most_recent': self.history[-1] if self.history else {}
        }
    
    # ============ Parameter Recommendations ============
    
    def recommend_parameters(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend parameters based on constraints.
        
        Args:
            constraints: Dict with 'max_response_time_ms', 'min_accuracy', etc
            
        Returns:
            Recommended parameter set
        """
        recommendations = {
            'rag': {},
            'llm': {},
            'profile': 'balanced'
        }
        
        # If response time constraint is tight
        if constraints.get('max_response_time_ms', float('inf')) < 2000:
            recommendations['profile'] = 'speed'
            recommendations['rag']['top_k'] = 5
            recommendations['rag']['similarity_threshold'] = 0.8
            recommendations['llm']['temperature'] = 0.3
        
        # If accuracy requirement is high
        elif constraints.get('min_accuracy', 0) > 0.8:
            recommendations['profile'] = 'high_precision'
            recommendations['rag']['top_k'] = 30
            recommendations['rag']['similarity_threshold'] = 0.5
            recommendations['llm']['temperature'] = 0.3
        
        # If under resource constraints
        elif constraints.get('resource_limited', False):
            recommendations['profile'] = 'resource_limited'
            recommendations['rag']['top_k'] = 3
            recommendations['llm']['max_tokens'] = 128
        
        return recommendations
    
    # ============ Export & Import ============
    
    def export_config(self) -> str:
        """Export current configuration as JSON"""
        return json.dumps(self.get_all_params(), indent=2)
    
    def import_config(self, config_json: str) -> bool:
        """Import configuration from JSON"""
        try:
            config = json.loads(config_json)
            self.batch_update_params(config)
            return True
        except Exception as e:
            print(f"Error importing config: {e}")
            return False
    
    def reset_to_profile(self, profile_name: str = 'balanced'):
        """Reset all parameters to profile defaults"""
        return self.apply_profile(profile_name)
    
    # ============ Helper Methods ============
    
    def _restructure_adjustments(self, adjustments: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Restructure flat adjustments dict to nested format"""
        result = {'rag': {}, 'llm': {}}
        for key, value in adjustments.items():
            if key.startswith('rag.'):
                result['rag'][key[4:]] = value
            elif key.startswith('llm.'):
                result['llm'][key[4:]] = value
        return result
    
    def get_parameter_summary(self) -> str:
        """Get human-readable parameter summary"""
        summary = f"""
=== PARAMETER CONFIGURATION ===

Profile: {self.profile_name}
Optimization Enabled: {self.optimization_enabled}

RAG PARAMETERS:
- Top K: {self.rag_params.top_k}
- Similarity Threshold: {self.rag_params.similarity_threshold}
- Reranker Top N: {self.rag_params.reranker_top_n}
- Chunk Size: {self.rag_params.chunk_size}
- Max Results to Synthesize: {self.rag_params.max_results_to_synthesize}

LLM PARAMETERS:
- Temperature: {self.llm_params.temperature}
- Max Tokens: {self.llm_params.max_tokens}
- Top P: {self.llm_params.top_p}
- Frequency Penalty: {self.llm_params.frequency_penalty}
- Presence Penalty: {self.llm_params.presence_penalty}

OPTIMIZATION HISTORY:
- Total Optimizations: {len(self.history)}
- Recent Scenarios: {[r['scenario'] for r in self.history[-5:]]}
"""
        return summary


class ParameterOptimizer:
    """Optimize parameters for specific agent operations"""
    
    def __init__(self, param_manager: ParameterManager):
        self.manager = param_manager
    
    def optimize_for_retrieval(self, accuracy_weight: float = 0.5, 
                              speed_weight: float = 0.5) -> Dict[str, Any]:
        """Optimize for retrieval based on accuracy vs speed tradeoff"""
        if accuracy_weight > 0.7:
            profile = 'accuracy'
        elif speed_weight > 0.7:
            profile = 'speed'
        else:
            profile = 'balanced'
        
        return self.manager.apply_profile(profile)
    
    def optimize_for_ingestion(self, quality_level: str = 'balanced') -> Dict[str, Any]:
        """Optimize for ingestion based on quality needs"""
        profiles = {
            'fast': 'resource_limited',
            'balanced': 'balanced',
            'high_quality': 'accuracy'
        }
        
        profile = profiles.get(quality_level, 'balanced')
        return self.manager.apply_profile(profile)
    
    def optimize_for_healing(self) -> Dict[str, Any]:
        """Optimize for healing/REFRAG operations"""
        return self.manager.apply_profile('high_precision')


# Global instance
_global_param_manager = None

def get_parameter_manager() -> ParameterManager:
    """Get or create global parameter manager"""
    global _global_param_manager
    if _global_param_manager is None:
        _global_param_manager = ParameterManager()
    return _global_param_manager
