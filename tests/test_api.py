import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from swarm.server import main as server_main
from swarm.server import task as task_manager
from swarm.server import client as client_manager


class TestServerAPI:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        task_manager.settings.tasks_dir = tmp_path / "tasks"
        task_manager.settings.tasks_dir.mkdir()
        client_manager.settings.data_dir = tmp_path
        client_manager.DATA_FILE = tmp_path / "clients.json"
        yield

    def test_root_endpoint(self):
        client = TestClient(server_main.app)
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Swarm Server is running"

    def test_health_endpoint(self):
        client = TestClient(server_main.app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_create_task(self):
        client = TestClient(server_main.app)
        payload = {
            "name": "API Test Task",
            "repo_url": "https://github.com/test/repo.git",
            "branch": "main",
            "test_paths": ["tests/"],
        }
        response = client.post("/api/tasks", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_list_tasks_empty(self):
        client = TestClient(server_main.app)
        response = client.get("/api/tasks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_tasks_with_data(self):
        client = TestClient(server_main.app)
        task_manager.create_task(
            name="Listed Task",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) >= 1

    def test_get_task(self):
        task = task_manager.create_task(
            name="Get Test",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        client = TestClient(server_main.app)
        response = client.get(f"/api/tasks/{task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Test"

    def test_get_nonexistent_task(self):
        client = TestClient(server_main.app)
        response = client.get("/api/tasks/nonexistent-id")
        assert response.status_code == 404

    def test_cancel_task(self):
        task = task_manager.create_task(
            name="Cancel Test",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        client = TestClient(server_main.app)
        response = client.delete(f"/api/tasks/{task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_cancel_completed_task_fails(self):
        task = task_manager.create_task(
            name="Completed Task",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        task_manager.update_task_status(task.id, task_manager.TaskStatus.COMPLETED)
        
        client = TestClient(server_main.app)
        response = client.delete(f"/api/tasks/{task.id}")
        assert response.status_code == 400

    def test_retry_task(self):
        task = task_manager.create_task(
            name="Retry Test",
            repo_url="https://github.com/test/repo.git",
            branch="main",
            test_paths=[],
        )
        task_manager.update_task_status(task.id, task_manager.TaskStatus.FAILED)
        
        client = TestClient(server_main.app)
        response = client.post(f"/api/tasks/{task.id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"


class TestClientAPI:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        client_manager.settings.data_dir = tmp_path
        client_manager.DATA_FILE = tmp_path / "clients.json"
        yield

    def test_list_clients_empty(self):
        client = TestClient(server_main.app)
        response = client.get("/api/clients")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_clients_with_data(self):
        from swarm.server.models import Client, ClientStatus
        c = Client(
            id="api-client-001",
            name="api-client",
            hostname="api-host",
            ip="192.168.1.200",
        )
        client_manager.register_client(c)
        
        client = TestClient(server_main.app)
        response = client.get("/api/clients")
        assert response.status_code == 200
        clients = response.json()
        assert len(clients) >= 1

    def test_get_client(self):
        from swarm.server.models import Client
        c = Client(
            id="api-client-002",
            name="api-client-2",
            hostname="api-host-2",
            ip="192.168.1.201",
        )
        client_manager.register_client(c)
        
        client = TestClient(server_main.app)
        response = client.get("/api/clients/api-client-002")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "api-client-2"

    def test_get_nonexistent_client(self):
        client = TestClient(server_main.app)
        response = client.get("/api/clients/nonexistent")
        assert response.status_code == 404