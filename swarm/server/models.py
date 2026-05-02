from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClientStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


class FilterArgs(BaseModel):
    k: Optional[str] = None
    m: Optional[str] = None


class ClientArgs(BaseModel):
    timeout: Optional[int] = None
    reruns: Optional[int] = None
    allure_results: Optional[str] = "/tmp/allure-results"


class TestResult(BaseModel):
    file: str
    status: str
    duration: float = 0.0
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0


class Task(BaseModel):
    id: str
    name: str
    repo_url: str
    branch: str = "main"
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    test_paths: List[str] = []
    filter_args: Optional[FilterArgs] = None
    client_args: Optional[ClientArgs] = None
    test_files: List[str] = []
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    results: List[TestResult] = []


class Client(BaseModel):
    id: str
    name: str
    hostname: str
    ip: str
    os: str = ""
    python_version: str = ""
    status: ClientStatus = ClientStatus.ONLINE
    registered_at: datetime = Field(default_factory=datetime.now)
    last_heartbeat: datetime = Field(default_factory=datetime.now)
    current_task_id: Optional[str] = None


class TaskTemplate(BaseModel):
    name: str
    repo_url: str
    branch: str = "main"
    test_paths: List[str] = []
    filter_args: Optional[FilterArgs] = None
    client_args: Optional[ClientArgs] = None


class TaskCreateRequest(BaseModel):
    name: str
    repo_url: str
    branch: str = "main"
    test_paths: List[str] = []
    filter_args: Optional[FilterArgs] = None
    client_args: Optional[ClientArgs] = None


class TaskResponse(BaseModel):
    id: str
    status: TaskStatus
    message: str = ""