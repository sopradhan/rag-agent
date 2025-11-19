"""Main package for DeepAgent RAG System."""

from .orchestrator import MasterOrchestrator
from .agents import IngestionAgent, RetrievalAgent, HealingAgent
from .abstraction import LLMManager, DataSourceManager, RBACManager  # DEPRECATED: Use orchestrator instead

__version__ = "1.0.0"

__all__ = [
    "MasterOrchestrator",
    "IngestionAgent",  # DEPRECATED
    "RetrievalAgent",  # DEPRECATED
    "HealingAgent",  # DEPRECATED
    "LLMManager",
    "DataSourceManager",
    "RBACManager",  # DEPRECATED
]
