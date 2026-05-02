import json
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from swarm.server.config import get_task_file, settings
from swarm.server.models import ClientArgs, FilterArgs, Task, TaskStatus


def load_task(task_id: str) -> Optional[Task]:
    task_file = get_task_file(task_id)
    if not task_file.exists():
        return None
    try:
        data = json.loads(task_file.read_text())
        return Task(**data)
    except Exception as e:
        logger.error(f"Failed to load task {task_id}: {e}")
        return None


def save_task(task: Task) -> bool:
    task_file = get_task_file(task.id)
    try:
        task_file.write_text(task.model_dump_json(indent=2))
        return True
    except Exception as e:
        logger.error(f"Failed to save task {task.id}: {e}")
        return False


def list_tasks() -> List[Task]:
    tasks = []
    for task_file in settings.tasks_dir.glob("*.json"):
        try:
            data = json.loads(task_file.read_text())
            tasks.append(Task(**data))
        except Exception as e:
            logger.warning(f"Failed to load task from {task_file}: {e}")
    return sorted(tasks, key=lambda t: t.created_at, reverse=True)


def list_tasks_by_status(status: TaskStatus) -> List[Task]:
    all_tasks = list_tasks()
    return [t for t in all_tasks if t.status == status]


def get_pending_tasks() -> List[Task]:
    return list_tasks_by_status(TaskStatus.PENDING)


def get_running_tasks() -> List[Task]:
    return list_tasks_by_status(TaskStatus.RUNNING)


def create_task(
    name: str,
    repo_url: str,
    branch: str,
    test_paths: List[str],
    filter_args: Optional[FilterArgs] = None,
    client_args: Optional[ClientArgs] = None,
) -> Task:
    import uuid
    task = Task(
        id=str(uuid.uuid4()),
        name=name,
        repo_url=repo_url,
        branch=branch,
        test_paths=test_paths,
        filter_args=filter_args,
        client_args=client_args,
        status=TaskStatus.PENDING,
    )
    save_task(task)
    return task


def update_task_status(task_id: str, status: TaskStatus) -> bool:
    task = load_task(task_id)
    if not task:
        return False
    from datetime import datetime
    task.status = status
    if status == TaskStatus.RUNNING and not task.started_at:
        task.started_at = datetime.now()
    elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        task.finished_at = datetime.now()
    return save_task(task)


def add_test_files(task_id: str, test_files: List[str]) -> bool:
    task = load_task(task_id)
    if not task:
        return False
    task.test_files = test_files
    task.total_files = len(test_files)
    return save_task(task)


def update_task_result(
    task_id: str,
    file_path: str,
    result: Dict,
) -> bool:
    task = load_task(task_id)
    if not task:
        return False
    from swarm.server.models import TestResult
    
    result_obj = TestResult(
        file=file_path,
        status=result.get("status", "unknown"),
        duration=result.get("duration", 0.0),
        passed=result.get("passed", 0),
        failed=result.get("failed", 0),
        error=result.get("error", 0),
        skipped=result.get("skipped", 0),
    )
    task.results.append(result_obj)
    task.completed_files += 1
    if result.get("status") == "failed":
        task.failed_files += 1
    
    if task.completed_files >= task.total_files:
        task.status = TaskStatus.COMPLETED
        from datetime import datetime
        task.finished_at = datetime.now()
    
    return save_task(task)