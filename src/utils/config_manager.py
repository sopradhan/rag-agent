"""
Dynamic Agent Configuration Manager
Allows runtime modification of agent parameters.
"""

import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import threading


class AgentConfigManager:
    """Manages dynamic agent configuration with runtime updates."""
    
    def __init__(self, config_path: str = "config/agent_config.yaml"):
        self.config_path = Path(config_path)
        self.lock = threading.Lock()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
    
    def get_config(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get configuration for agent.
        
        Args:
            agent_name: Name of agent (e.g., 'retrieval_agent'). If None, returns all config.
        
        Returns:
            Configuration dictionary
        """
        with self.lock:
            if agent_name:
                return self.config.get(agent_name, {})
            return self.config.copy()
    
    def set_config(self, agent_name: str, key: str, value: Any) -> bool:
        """
        Set configuration value for agent.
        
        Args:
            agent_name: Name of agent (e.g., 'retrieval_agent')
            key: Configuration key (can be nested with dots: 'subagents.reranker.enabled')
            value: New value
        
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Handle nested keys
                keys = key.split('.')
                config = self.config.setdefault(agent_name, {})
                
                # Navigate to parent
                for k in keys[:-1]:
                    config = config.setdefault(k, {})
                
                # Set value
                config[keys[-1]] = value
                
                # Save to file
                self._save_config()
                
                return True
            except Exception:
                return False
    
    def update_config(self, agent_name: str, updates: Dict[str, Any]) -> bool:
        """
        Update multiple configuration values.
        
        Args:
            agent_name: Name of agent
            updates: Dictionary of key-value pairs to update
        
        Returns:
            True if successful
        """
        with self.lock:
            try:
                if agent_name not in self.config:
                    self.config[agent_name] = {}
                
                # Deep merge updates
                self._deep_update(self.config[agent_name], updates)
                
                # Save to file
                self._save_config()
                
                return True
            except Exception:
                return False
    
    def _deep_update(self, base: Dict, updates: Dict):
        """Recursively update nested dictionary."""
        for key, value in updates.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_update(base[key], value)
            else:
                base[key] = value
    
    def reset_to_default(self, agent_name: Optional[str] = None):
        """Reset configuration to defaults."""
        with self.lock:
            defaults = self._get_default_config()
            
            if agent_name:
                if agent_name in defaults:
                    self.config[agent_name] = defaults[agent_name]
            else:
                self.config = defaults
            
            self._save_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "master_agent": {
                "name": "MasterOrchestrator",
                "memory_backend": "persistent",
                "max_iterations": 10,
                "logging_level": "INFO"
            },
            "ingestion_agent": {
                "name": "IngestionAgent",
                "memory_backend": "persistent",
                "parallel_processing": True,
                "max_workers": 4,
                "subagents": {
                    "chunker": {
                        "name": "ChunkerSubagent",
                        "memory_backend": "in-memory",
                        "strategy": "recursive"
                    },
                    "metadata": {
                        "name": "MetadataSubagent",
                        "memory_backend": "in-memory",
                        "extract_keywords": True,
                        "extract_summary": True
                    },
                    "rbac": {
                        "name": "RBACSubagent",
                        "memory_backend": "in-memory",
                        "auto_classify": True
                    },
                    "embedding": {
                        "name": "EmbeddingSubagent",
                        "memory_backend": "in-memory",
                        "batch_size": 100
                    }
                }
            },
            "retrieval_agent": {
                "name": "RetrievalAgent",
                "memory_backend": "persistent",
                "top_k": 5,
                "similarity_threshold": 0.7,
                "temperature": 0.7,
                "reranker": {
                    "enabled": False,
                    "model": "cross-encoder",
                    "top_n": 3
                },
                "subagents": {
                    "permission_checker": {
                        "name": "PermissionCheckerSubagent",
                        "memory_backend": "in-memory",
                        "strict_mode": True
                    },
                    "graph_expansion": {
                        "name": "GraphExpansionSubagent",
                        "memory_backend": "in-memory",
                        "max_depth": 2,
                        "max_nodes": 10
                    },
                    "answer_synthesis": {
                        "name": "AnswerSynthesisSubagent",
                        "memory_backend": "in-memory",
                        "include_sources": True,
                        "max_context_length": 4000
                    }
                }
            },
            "healing_agent": {
                "name": "HealingAgent",
                "memory_backend": "persistent",
                "run_interval": "24h",
                "auto_optimize": True,
                "subagents": {
                    "heatmap_analyzer": {
                        "name": "HeatmapAnalyzerSubagent",
                        "memory_backend": "persistent",
                        "metrics": [
                            "query_frequency",
                            "retrieval_accuracy",
                            "response_time",
                            "user_feedback"
                        ]
                    },
                    "optimization": {
                        "name": "OptimizationSubagent",
                        "memory_backend": "persistent",
                        "strategies": [
                            "reindex_low_quality",
                            "add_synthetic_questions",
                            "adjust_chunk_size",
                            "update_embeddings"
                        ]
                    }
                }
            }
        }


class LLMConfigManager:
    """Manages LLM configuration with runtime updates."""
    
    def __init__(self, config_path: str = "config/llm_config.yaml"):
        self.config_path = Path(config_path)
        self.lock = threading.Lock()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def _save_config(self):
        """Save configuration to file."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
    
    def get_provider_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get LLM provider configuration."""
        with self.lock:
            if provider:
                return self.config.get("llm_providers", {}).get(provider, {})
            return self.config.get("llm_providers", {})
    
    def set_default_provider(self, provider: str) -> bool:
        """Set default LLM provider."""
        with self.lock:
            try:
                if provider in self.config.get("llm_providers", {}):
                    self.config["default_provider"] = provider
                    self._save_config()
                    return True
                return False
            except Exception:
                return False
    
    def update_provider_config(self, provider: str, key: str, value: Any) -> bool:
        """
        Update provider configuration.
        
        Args:
            provider: Provider name (e.g., 'ollama')
            key: Configuration key (e.g., 'temperature')
            value: New value
        """
        with self.lock:
            try:
                if provider not in self.config.get("llm_providers", {}):
                    return False
                
                self.config["llm_providers"][provider][key] = value
                self._save_config()
                return True
            except Exception:
                return False
    
    def enable_provider(self, provider: str, enabled: bool = True) -> bool:
        """Enable or disable provider."""
        return self.update_provider_config(provider, "enabled", enabled)
    
    def set_temperature(self, provider: str, temperature: float) -> bool:
        """Set temperature for provider."""
        return self.update_provider_config(provider, "temperature", temperature)
    
    def get_active_provider(self) -> str:
        """Get currently active default provider."""
        with self.lock:
            return self.config.get("default_provider", "openai")


# Global singletons
_agent_config_manager = None
_llm_config_manager = None


def get_agent_config_manager() -> AgentConfigManager:
    """Get global agent config manager instance."""
    global _agent_config_manager
    if _agent_config_manager is None:
        _agent_config_manager = AgentConfigManager()
    return _agent_config_manager


def get_llm_config_manager() -> LLMConfigManager:
    """Get global LLM config manager instance."""
    global _llm_config_manager
    if _llm_config_manager is None:
        _llm_config_manager = LLMConfigManager()
    return _llm_config_manager
