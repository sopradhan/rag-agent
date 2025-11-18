"""Subagents package."""

try:
    from .ingestion_subagents import (
        ChunkerSubagent,
        MetadataSubagent,
        RBACSubagent,
        EmbeddingSubagent
    )
except ImportError:
    ChunkerSubagent = None
    MetadataSubagent = None
    RBACSubagent = None
    EmbeddingSubagent = None

try:
    from .retrieval_subagents import (
        PermissionCheckerSubagent,
        GraphExpansionSubagent,
        AnswerSynthesisSubagent
    )
except ImportError:
    PermissionCheckerSubagent = None
    GraphExpansionSubagent = None
    AnswerSynthesisSubagent = None

try:
    from .healing_subagents import (
        HeatmapAnalyzerSubagent,
        OptimizationSubagent
    )
except ImportError:
    HeatmapAnalyzerSubagent = None
    OptimizationSubagent = None

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
]
