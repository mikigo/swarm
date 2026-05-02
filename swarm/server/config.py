import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    data_dir: Path = Path("./data")
    tasks_dir: Path = Path("./data/tasks")
    reports_dir: Path = Path("./data/reports")
    allure_dir: Path = Path("./data/allure")
    logs_dir: Path = Path("./data/logs")
    
    heartbeat_interval: int = 30
    heartbeat_timeout: int = 60
    
    log_retention_days: int = 7
    
    class Config:
        env_prefix = "SWARM_"


settings = Settings()


def ensure_directories() -> None:
    for directory in [
        settings.data_dir,
        settings.tasks_dir,
        settings.reports_dir,
        settings.allure_dir,
        settings.logs_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def get_task_file(task_id: str) -> Path:
    return settings.tasks_dir / f"{task_id}.json"


def get_report_dir(task_id: str) -> Path:
    return settings.reports_dir / task_id


def get_allure_dir(task_id: str) -> Path:
    return settings.allure_dir / task_id