"""
Configuration Loader and Manager
Centralized configuration access for the entire system
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading


class ConfigLoader:
    """Thread-safe singleton configuration loader."""
    
    _instance = None
    _lock = threading.Lock()
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config/system_config.yaml"):
        """Initialize configuration loader."""
        if self._config is None:
            self._config_path = config_path
            self.reload()
    
    def reload(self):
        """Reload configuration from file."""
        with self._lock:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get full configuration."""
        return self._config
    
    # Database Configuration
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self._config.get("database", {})
    
    def get_database_path(self) -> str:
        """Get database file path."""
        return self.get_database_config().get("path", "data/rag_system.db")
    
    def get_table_definitions(self) -> Dict[str, Any]:
        """Get all table definitions."""
        return self.get_database_config().get("tables", {})
    
    def get_table_definition(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get definition for specific table."""
        return self.get_table_definitions().get(table_name)
    
    # Department Configuration
    
    def get_departments(self) -> Dict[str, Any]:
        """Get all department configurations."""
        return self._config.get("departments", {})
    
    def get_department_config(self, department: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific department."""
        return self.get_departments().get(department)
    
    def get_department_keywords(self, department: str) -> List[str]:
        """Get keywords for a department."""
        dept = self.get_department_config(department)
        return dept.get("keywords", []) if dept else []
    
    def get_department_access_level(self, department: str) -> int:
        """Get access level for a department."""
        dept = self.get_department_config(department)
        return dept.get("access_level", 5) if dept else 5
    
    def get_department_allowed_roles(self, department: str) -> List[str]:
        """Get allowed roles for a department."""
        dept = self.get_department_config(department)
        return dept.get("allowed_roles", []) if dept else []
    
    # Role Configuration
    
    def get_roles(self) -> Dict[str, Any]:
        """Get all role configurations."""
        return self._config.get("roles", {})
    
    def get_role_config(self, role: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific role."""
        return self.get_roles().get(role)
    
    def get_role_display_name(self, role: str) -> str:
        """Get display name for a role."""
        role_config = self.get_role_config(role)
        return role_config.get("display_name", role.title()) if role_config else role.title()
    
    def get_role_description(self, role: str) -> str:
        """Get description for a role."""
        role_config = self.get_role_config(role)
        return role_config.get("description", "") if role_config else ""
    
    def get_role_access_level(self, role: str) -> int:
        """Get access level for a role."""
        role_config = self.get_role_config(role)
        return role_config.get("access_level", 5) if role_config else 5
    
    # Retrieval Configuration
    
    def get_retrieval_config(self) -> Dict[str, Any]:
        """Get retrieval configuration."""
        return self._config.get("retrieval", {})
    
    def get_default_top_k(self) -> int:
        """Get default top_k value."""
        return self.get_retrieval_config().get("default_top_k", 5)
    
    def get_default_similarity_threshold(self) -> float:
        """Get default similarity threshold."""
        return self.get_retrieval_config().get("default_similarity_threshold", 0.3)
    
    def get_faithfulness_config(self) -> Dict[str, Any]:
        """Get faithfulness threshold configuration."""
        return self.get_retrieval_config().get("faithfulness", {})
    
    def get_greeting_keywords(self) -> List[str]:
        """Get greeting keywords."""
        return self.get_retrieval_config().get("greeting_keywords", [])
    
    def get_help_keywords(self) -> List[str]:
        """Get help keywords."""
        return self.get_retrieval_config().get("help_keywords", [])
    
    # Dashboard Configuration
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get dashboard configuration."""
        return self._config.get("dashboard", {})
    
    def get_dashboard_title(self) -> str:
        """Get dashboard title."""
        return self.get_dashboard_config().get("title", "RAG System Dashboard")
    
    def get_dashboard_pages(self) -> List[Dict[str, str]]:
        """Get dashboard page configurations."""
        return self.get_dashboard_config().get("pages", [])
    
    def get_max_chat_history(self) -> int:
        """Get maximum chat history size."""
        return self.get_dashboard_config().get("max_chat_history", 100)
    
    # Data Sources Configuration
    
    def get_data_sources(self) -> List[Dict[str, Any]]:
        """Get data source configurations."""
        return self._config.get("data_sources", [])
    
    def get_enabled_data_sources(self) -> List[Dict[str, Any]]:
        """Get only enabled data sources."""
        return [ds for ds in self.get_data_sources() if ds.get("enabled", False)]
    
    # System Configuration
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration."""
        return self._config.get("system", {})
    
    def get_log_level(self) -> str:
        """Get log level."""
        return self.get_system_config().get("log_level", "INFO")
    
    def is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self.get_system_config().get("enable_debug", False)
    
    def get_healing_config(self) -> Dict[str, Any]:
        """Get healing configuration."""
        return self.get_system_config().get("healing", {})
    
    def is_healing_enabled(self) -> bool:
        """Check if healing is enabled."""
        return self.get_healing_config().get("enabled", True)
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return self.get_system_config().get("performance", {})


# Global singleton instance
_config_loader = None


def get_config() -> ConfigLoader:
    """Get global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


# Convenience functions for common config access

def get_db_path() -> str:
    """Get database path from config."""
    return get_config().get_database_path()


def get_departments_config() -> Dict[str, Any]:
    """Get departments configuration."""
    return get_config().get_departments()


def get_roles_config() -> Dict[str, Any]:
    """Get roles configuration."""
    return get_config().get_roles()


def get_role_level(role: str) -> int:
    """Get access level for a role."""
    return get_config().get_role_access_level(role)


def reload_config():
    """Reload configuration from file."""
    get_config().reload()
