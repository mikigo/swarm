import json
import tempfile
from pathlib import Path

import pytest
from swarm.server import config


class TestConfig:
    def test_settings_default_values(self):
        assert config.settings.host == "0.0.0.0"
        assert config.settings.port == 8000
        assert config.settings.heartbeat_interval == 30
        assert config.settings.heartbeat_timeout == 60

    def test_ensure_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config.settings.data_dir = Path(tmpdir)
            config.settings.tasks_dir = Path(tmpdir) / "tasks"
            config.settings.reports_dir = Path(tmpdir) / "reports"
            config.settings.allure_dir = Path(tmpdir) / "allure"
            config.settings.logs_dir = Path(tmpdir) / "logs"
            
            config.ensure_directories()
            
            assert config.settings.tasks_dir.exists()
            assert config.settings.reports_dir.exists()
            assert config.settings.allure_dir.exists()
            assert config.settings.logs_dir.exists()

    def test_get_task_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config.settings.tasks_dir = Path(tmpdir)
            task_file = config.get_task_file("task-123")
            assert task_file.name == "task-123.json"

    def test_get_report_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config.settings.reports_dir = Path(tmpdir)
            report_dir = config.get_report_dir("task-456")
            assert report_dir.name == "task-456"

    def test_get_allure_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config.settings.allure_dir = Path(tmpdir)
            allure_dir = config.get_allure_dir("task-789")
            assert allure_dir.name == "task-789"