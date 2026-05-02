import tempfile
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock


class TestGitModule:
    def test_get_repo_name(self):
        from swarm.client import git
        assert git.get_repo_name("https://github.com/test/repo.git") == "repo"
        assert git.get_repo_name("https://github.com/test/repo") == "repo"
        assert git.get_repo_name("https://github.com/test/repo/") == "repo"

    def test_get_repos_dir(self):
        from swarm.client import git
        repos_dir = git.get_repos_dir()
        assert repos_dir.name == "repos"
        assert "swarm" in str(repos_dir)


class TestVenvModule:
    def test_find_venv_tool_pipfile(self):
        from swarm.client import venv
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "Pipfile").touch()
            tool = venv.find_venv_tool(path)
            assert tool == "pipenv"

    def test_find_venv_tool_pyproject(self):
        from swarm.client import venv
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "pyproject.toml").touch()
            tool = venv.find_venv_tool(path)
            assert tool == "uv"

    def test_find_venv_tool_requirements(self):
        from swarm.client import venv
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "requirements.txt").touch()
            tool = venv.find_venv_tool(path)
            assert tool == "venv"

    def test_find_venv_tool_default(self):
        from swarm.client import venv
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            tool = venv.find_venv_tool(path)
            assert tool == "venv"


class TestUploaderModule:
    def test_upload_results_signature(self):
        import inspect
        from swarm.client import uploader
        sig = inspect.signature(uploader.upload_results)
        assert "server_url" in sig.parameters
        assert "task_id" in sig.parameters
        assert "allure_zip" in sig.parameters