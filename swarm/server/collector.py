import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


def find_python_test_files(directory: str) -> List[str]:
    test_files = []
    path = Path(directory)
    if not path.exists():
        return test_files
    
    for item in path.rglob("*"):
        if item.is_file() and item.suffix == ".py":
            if item.name.startswith("test_") or "_test.py" in item.name:
                test_files.append(str(item))
    
    return sorted(test_files)


def collect_tests(
    repo_url: str,
    branch: str,
    test_paths: List[str],
    filter_args: Optional[Dict] = None,
    work_dir: Optional[str] = None,
) -> List[str]:
    logger.info(f"Collecting tests from {repo_url} (branch: {branch})")
    
    test_dirs = test_paths if test_paths else ["tests", "test"]
    all_files = []
    
    for test_dir in test_dirs:
        files = find_python_test_files(test_dir)
        all_files.extend(files)
    
    if filter_args:
        k_filter = filter_args.get("k")
        m_filter = filter_args.get("m")
        
        if k_filter or m_filter:
            filtered_files = []
            cmd = ["pytest", "--collect-only", "-q"]
            
            if k_filter:
                cmd.extend(["-k", k_filter])
            if m_filter:
                cmd.extend(["-m", m_filter])
            
            for test_file in all_files:
                try:
                    result = subprocess.run(
                        cmd + [test_file],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0 or "test session starts" in result.stdout:
                        filtered_files.append(test_file)
                except Exception as e:
                    logger.warning(f"Failed to collect {test_file}: {e}")
            
            all_files = filtered_files
    
    logger.info(f"Collected {len(all_files)} test files")
    return all_files


def get_test_count(test_files: List[str]) -> Dict:
    total_tests = 0
    for test_file in test_files:
        try:
            result = subprocess.run(
                ["pytest", "--collect-only", "-q", test_file],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in result.stdout.split("\n"):
                if "<Module" in line or "<Function" in line:
                    total_tests += 1
        except Exception:
            pass
    
    return {"total": total_tests, "files": len(test_files)}