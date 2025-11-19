"""Abstraction layer package."""

from .llm_abstraction import LLMManager, BaseLLM
from .data_source_abstraction import DataSourceManager, Document
from .rbac_abstraction import RBACManager, User, DocumentAccess  # DEPRECATED: Use SQLite hierarchical RBAC instead
from .database_abstraction import DatabaseManager, SQLiteDatabase, BaseDatabase
from .prompt_manager import PromptManager, PromptTemplate, COTReasoner
from .vector_store_abstraction import VectorStoreManager, ChromaVectorStore, BaseVectorStore, SearchResult

__all__ = [
    "LLMManager",
    "BaseLLM",
    "DataSourceManager",
    "Document",
    "RBACManager",  # DEPRECATED
    "User",  # DEPRECATED
    "DocumentAccess",  # DEPRECATED
    "DatabaseManager",
    "SQLiteDatabase",
    "BaseDatabase",
    "PromptManager",
    "PromptTemplate",
    "COTReasoner",
    "VectorStoreManager",
    "ChromaVectorStore",
    "BaseVectorStore",
    "SearchResult",
]
