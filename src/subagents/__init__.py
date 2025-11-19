"""Subagents package."""

# Legacy subagents - create dummy implementations to support existing code
class ChunkerSubagent:
    """Placeholder for chunking functionality."""
    def __init__(self, name=None, config=None, **kwargs):
        self.name = name
        self.config = config or {}
        for k, v in kwargs.items():
            setattr(self, k, v)

class MetadataSubagent:
    """Placeholder for metadata extraction."""
    def __init__(self, name=None, config=None, llm_manager=None, **kwargs):
        self.name = name
        self.config = config or {}
        self.llm_manager = llm_manager
        for k, v in kwargs.items():
            setattr(self, k, v)

class RBACSubagent:
    """Placeholder for RBAC classification."""
    def __init__(self, name=None, config=None, rbac_manager=None, **kwargs):
        self.name = name
        self.config = config or {}
        self.rbac_manager = rbac_manager
        for k, v in kwargs.items():
            setattr(self, k, v)

class EmbeddingSubagent:
    """Placeholder for embedding generation."""
    def __init__(self, name=None, config=None, llm_manager=None, **kwargs):
        self.name = name
        self.config = config or {}
        self.llm_manager = llm_manager
        for k, v in kwargs.items():
            setattr(self, k, v)

# Retrieval subagents - check if actual implementations exist
try:
    from .retrieval_subagents import (
        PermissionCheckerSubagent,
        GraphExpansionSubagent,
        AnswerSynthesisSubagent
    )
except ImportError:
    # Fallback to placeholder implementations
    class PermissionCheckerSubagent:
        def __init__(self, name=None, config=None, llm_manager=None, rbac_manager=None, **kwargs):
            self.name = name
            self.config = config or {}
            self.llm_manager = llm_manager
            self.rbac_manager = rbac_manager
            for k, v in kwargs.items():
                setattr(self, k, v)

    class GraphExpansionSubagent:
        def __init__(self, name=None, config=None, llm_manager=None, **kwargs):
            self.name = name
            self.config = config or {}
            self.llm_manager = llm_manager
            for k, v in kwargs.items():
                setattr(self, k, v)

    class AnswerSynthesisSubagent:
        def __init__(self, name=None, config=None, llm_manager=None, **kwargs):
            self.name = name
            self.config = config or {}
            self.llm_manager = llm_manager
            for k, v in kwargs.items():
                setattr(self, k, v)

# Healing subagents - check if actual implementations exist
try:
    from .healing_subagents import (
        HeatmapAnalyzerSubagent,
        OptimizationSubagent
    )
except ImportError:
    # Fallback to placeholder implementations
    class HeatmapAnalyzerSubagent:
        def __init__(self, name=None, config=None, llm_manager=None, **kwargs):
            self.name = name
            self.config = config or {}
            self.llm_manager = llm_manager
            for k, v in kwargs.items():
                setattr(self, k, v)

    class OptimizationSubagent:
        def __init__(self, name=None, config=None, llm_manager=None, **kwargs):
            self.name = name
            self.config = config or {}
            self.llm_manager = llm_manager
            for k, v in kwargs.items():
                setattr(self, k, v)

# LangChain subagents (always available)
from .langchain_subagents import (
    AnalyzerSubagent,
    SearcherSubagent,
    FilterSubagent,
    RankerSubagent,
    SynthesizerSubagent,
    RefinerSubagent,
    ValidatorSubagent,
    SubagentRegistry
)

# SQLite ingestion subagent
try:
    from .sqlite_ingestion_subagent import (
        SQLiteIngestionSubagent,
        SQLiteSource
    )
except ImportError:
    SQLiteIngestionSubagent = None
    SQLiteSource = None

# RBAC-aware ingestion subagent
try:
    from .rbac_ingestion_subagent import (
        DocumentNamespace,
        RBACContext,
        RBACResolver,
        NamespaceManager,
        RBACIntelligentIngestionSubagent
    )
except ImportError:
    DocumentNamespace = None
    RBACContext = None
    RBACResolver = None
    NamespaceManager = None
    RBACIntelligentIngestionSubagent = None

# RBAC-aware retrieval subagent
try:
    from .rbac_retrieval_subagent import (
        RBACFilteringSubagent,
        TagRetrievalSubagent,
        RBACSearchSubagent
    )
except ImportError:
    RBACFilteringSubagent = None
    TagRetrievalSubagent = None
    RBACSearchSubagent = None

# RBAC-aware healing subagent
try:
    from .rbac_healing_subagent import (
        EmbeddingShuffler,
        EmbeddingRefragmenter,
        RBACHealingSubagent
    )
except ImportError:
    EmbeddingShuffler = None
    EmbeddingRefragmenter = None
    RBACHealingSubagent = None

__all__ = [
    "ChunkerSubagent",
    "MetadataSubagent",
    "RBACSubagent",
    "EmbeddingSubagent",
    "PermissionCheckerSubagent",
    "GraphExpansionSubagent",
    "AnswerSynthesisSubagent",
    "HeatmapAnalyzerSubagent",
    "OptimizationSubagent",
    "AnalyzerSubagent",
    "SearcherSubagent",
    "FilterSubagent",
    "RankerSubagent",
    "SynthesizerSubagent",
    "RefinerSubagent",
    "ValidatorSubagent",
    "SubagentRegistry",
    "SQLiteIngestionSubagent",
    "SQLiteSource",
    "DocumentNamespace",
    "RBACContext",
    "RBACResolver",
    "NamespaceManager",
    "RBACIntelligentIngestionSubagent",
    "RBACFilteringSubagent",
    "TagRetrievalSubagent",
    "RBACSearchSubagent",
    "EmbeddingShuffler",
    "EmbeddingRefragmenter",
    "RBACHealingSubagent",
]
