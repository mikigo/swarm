import json
from pathlib import Path
from typing import List, Optional

import yaml
from loguru import logger


DEFAULT_CONFIG_PATH = Path.home() / ".swarm" / "config.yaml"


class CLIConfig:
    def __init__(self):
        self.config: dict = self._load_config()
    
    def _load_config(self) -> dict:
        config = {}
        
        if DEFAULT_CONFIG_PATH.exists():
            try:
                config = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text()) or {}
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        
        return config
    
    def get_task_list_config(self) -> dict:
        return self.config.get("task", {}).get("list", {})
    
    def get_columns(self) -> List[str]:
        task_config = self.get_task_list_config()
        return task_config.get("columns", ["id", "name", "status", "created_at"])
    
    def get_column_widths(self) -> dict:
        task_config = self.get_task_list_config()
        return task_config.get("width", {})
    
    def get_column_colors(self) -> dict:
        task_config = self.get_task_list_config()
        return task_config.get("color", {})


config = CLIConfig()