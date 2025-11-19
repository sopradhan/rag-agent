"""
Configuration Loader
Loads and validates YAML configuration files
"""
import yaml
from pathlib import Path
from typing import Dict, Any


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration file
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        Configuration dictionary
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config or {}


def load_all_configs(config_dir: str = "config") -> Dict[str, Dict]:
    """
    Load all configuration files from config directory
    
    Args:
        config_dir: Path to config directory
        
    Returns:
        Dictionary of all configurations
    """
    config_path = Path(config_dir)
    
    configs = {}
    
    # Load each config file
    config_files = {
        'agent': 'agent_config.yaml',
        'llm': 'llm_config.yaml',
        'rbac': 'rbac_config.yaml',
        'system': 'system_config.yaml',
        'data_sources': 'data_sources.yaml',
        'prompts': 'prompts_config.yaml'
    }
    
    for key, filename in config_files.items():
        file_path = config_path / filename
        if file_path.exists():
            configs[key] = load_config(str(file_path))
        else:
            print(f"[WARNING] Config file not found: {filename}")
            configs[key] = {}
    
    return configs
