import pytest
from swarm.server.models import Task, TaskStatus, FilterArgs, ClientArgs


class TestTaskModel:
    def test_task_creation(self):
        task = Task(
            id="test-001",
            name="Test Task",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=["tests/"],
        )
        assert task.id == "test-001"
        assert task.name == "Test Task"
        assert task.status == TaskStatus.PENDING
        assert task.branch == "main"

    def test_task_with_filter_args(self):
        task = Task(
            id="test-002",
            name="Test Task with Filter",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            filter_args=FilterArgs(k="api", m="smoke"),
        )
        assert task.filter_args is not None
        assert task.filter_args.k == "api"
        assert task.filter_args.m == "smoke"

    def test_task_with_client_args(self):
        task = Task(
            id="test-003",
            name="Test Task with Client Args",
            repo_url="https://github.com/test/repo.git",
            client_args=ClientArgs(timeout=60, reruns=2),
        )
        assert task.client_args is not None
        assert task.client_args.timeout == 60
        assert task.client_args.reruns == 2


class TestTaskStatus:
    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"