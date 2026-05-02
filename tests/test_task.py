import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from swarm.server import task as task_manager
from swarm.server.models import Task, TaskStatus, FilterArgs, ClientArgs


class TestTaskManager:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        task_manager.settings.tasks_dir = tmp_path
        yield

    def test_create_task(self):
        task = task_manager.create_task(
            name="Test Task",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=["tests/"],
        )
        assert task.name == "Test Task"
        assert task.repo_url == "https://github.com/test/repo.git"
        assert task.branch == "main"
        assert task.status == TaskStatus.PENDING
        assert task.id is not None

    def test_create_task_with_filter_args(self):
        task = task_manager.create_task(
            name="Filtered Task",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=["tests/"],
            filter_args=FilterArgs(k="api"),
        )
        assert task.filter_args is not None
        assert task.filter_args.k == "api"

    def test_load_task(self):
        created = task_manager.create_task(
            name="Task to Load",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=["tests/"],
        )
        loaded = task_manager.load_task(created.id)
        assert loaded is not None
        assert loaded.id == created.id
        assert loaded.name == "Task to Load"

    def test_load_nonexistent_task(self):
        loaded = task_manager.load_task("nonexistent-id")
        assert loaded is None

    def test_save_and_load_task(self):
        task = Task(
            id="test-save-001",
            name="Save Test",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        task_manager.save_task(task)
        loaded = task_manager.load_task("test-save-001")
        assert loaded is not None
        assert loaded.name == "Save Test"

    def test_list_tasks(self):
        task_manager.create_task(
            name="Task 1",
            repo_url="https://github.com/test/repo1.git",
            branch="main",
            test_paths=[],
        )
        task_manager.create_task(
            name="Task 2",
            repo_url="https://github.com/test/repo2.git",
            branch="main",
            test_paths=[],
        )
        tasks = task_manager.list_tasks()
        assert len(tasks) >= 2

    def test_update_task_status(self):
        task = task_manager.create_task(
            name="Status Test",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        result = task_manager.update_task_status(task.id, TaskStatus.RUNNING)
        assert result is True
        updated = task_manager.load_task(task.id)
        assert updated.status == TaskStatus.RUNNING
        assert updated.started_at is not None

    def test_update_nonexistent_task_status(self):
        result = task_manager.update_task_status("nonexistent", TaskStatus.RUNNING)
        assert result is False

    def test_add_test_files(self):
        task = task_manager.create_task(
            name="Files Test",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        test_files = ["tests/api/test_user.py", "tests/api/test_order.py"]
        result = task_manager.add_test_files(task.id, test_files)
        assert result is True
        updated = task_manager.load_task(task.id)
        assert len(updated.test_files) == 2
        assert updated.total_files == 2


class TestTaskManagerFilters:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        task_manager.settings.tasks_dir = tmp_path
        yield

    def test_list_tasks_by_status(self):
        task1 = task_manager.create_task(
            name="Pending Task",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        task2 = task_manager.create_task(
            name="Another Task",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        task_manager.update_task_status(task2.id, TaskStatus.RUNNING)
        
        pending = task_manager.list_tasks_by_status(TaskStatus.PENDING)
        assert any(t.id == task1.id for t in pending)
        
        running = task_manager.list_tasks_by_status(TaskStatus.RUNNING)
        assert any(t.id == task2.id for t in running)