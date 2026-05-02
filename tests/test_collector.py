import os
import tempfile
from pathlib import Path

import pytest
from swarm.server import collector


class TestCollector:
    def test_find_python_test_files_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            files = collector.find_python_test_files(tmpdir)
            assert files == []

    def test_find_python_test_files_with_test_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            (test_dir / "test_example.py").touch()
            (test_dir / "example_test.py").touch()
            (test_dir / "not_test.py").touch()
            (test_dir / "test_helper.py").touch()
            
            files = collector.find_python_test_files(tmpdir)
            assert len(files) == 4

    def test_find_python_test_files_nested(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            (test_dir / "tests" / "test_a.py").parent.mkdir(parents=True)
            (test_dir / "tests" / "test_a.py").touch()
            (test_dir / "tests" / "test_b.py").touch()
            
            files = collector.find_python_test_files(tmpdir)
            assert len(files) == 2

    def test_find_python_test_files_nonexistent(self):
        files = collector.find_python_test_files("/nonexistent/path")
        assert files == []

    def test_get_test_count(self):
        files = []
        count = collector.get_test_count(files)
        assert count["total"] == 0
        assert count["files"] == 0