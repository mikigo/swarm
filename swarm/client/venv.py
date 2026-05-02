import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


def find_venv_tool(repo_path: Path) -> str:
    if (repo_path / "Pipfile").exists():
        return "pipenv"
    if (repo_path / "pyproject.toml").exists():
        return "uv"
    return "venv"


def create_venv(repo_path: Path) -> Optional[Path]:
    venv_dir = repo_path / ".venv"
    if venv_dir.exists():
        return venv_dir
    
    tool = find_venv_tool(repo_path)
    
    try:
        if tool == "pipenv":
            subprocess.run(
                ["pipenv", "--python", "python"],
                cwd=repo_path,
                check=True,
            )
        elif tool == "uv":
            subprocess.run(
                ["uv", "venv", str(venv_dir)],
                check=True,
            )
        else:
            subprocess.run(
                ["python", "-m", "venv", str(venv_dir)],
                check=True,
            )
        
        logger.info(f"Virtual environment created using {tool}")
        return venv_dir
    except Exception as e:
        logger.error(f"Failed to create virtual environment: {e}")
        return None


def install_dependencies(venv_path: Path, repo_path: Path) -> bool:
    tool = find_venv_tool(repo_path)
    
    try:
        if tool == "pipenv":
            subprocess.run(
                ["pipenv", "install"],
                cwd=repo_path,
                check=True,
            )
        elif tool == "uv":
            pip_exe = venv_path / "bin" / "pip"
            if os.name == "nt":
                pip_exe = venv_path / "Scripts" / "pip.exe"
            subprocess.run(
                [str(pip_exe), "install", "-e", "."],
                cwd=repo_path,
                check=True,
            )
        else:
            pip_exe = venv_path / "bin" / "pip"
            if os.name == "nt":
                pip_exe = venv_path / "Scripts" / "pip.exe"
            
            if (repo_path / "requirements.txt").exists():
                subprocess.run(
                    [str(pip_exe), "install", "-r", "requirements.txt"],
                    cwd=repo_path,
                    check=True,
                )
            elif (repo_path / "pyproject.toml").exists():
                subprocess.run(
                    [str(pip_exe), "install", "-e", "."],
                    cwd=repo_path,
                    check=True,
                )
        
        logger.info(f"Dependencies installed using {tool}")
        return True
    except Exception as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False


def cleanup_venv(venv_path: Path) -> bool:
    try:
        shutil.rmtree(venv_path)
        logger.info(f"Virtual environment cleaned up: {venv_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup virtual environment: {e}")
        return False