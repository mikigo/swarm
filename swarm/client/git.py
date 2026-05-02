from pathlib import Path
from typing import Optional

import git as gitpython
from loguru import logger


def get_repo_name(repo_url: str) -> str:
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


def get_repos_dir() -> Path:
    home = Path.home()
    swarm_dir = home / "swarm" / "repos"
    swarm_dir.mkdir(parents=True, exist_ok=True)
    return swarm_dir


def clone_repo(repo_url: str, branch: str = "main") -> Optional[Path]:
    repo_name = get_repo_name(repo_url)
    repo_path = get_repos_dir() / repo_name
    
    try:
        if repo_path.exists():
            repo = gitpython.Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull()
            if branch != repo.active_branch.name:
                repo.git.checkout(branch)
        else:
            gitpython.Repo.clone_from(repo_url, repo_path, branch=branch)
        
        logger.info(f"Repository cloned/updated: {repo_name}")
        return repo_path
    except Exception as e:
        logger.error(f"Failed to clone repository: {e}")
        return None


def pull_latest(repo_path: Path) -> bool:
    try:
        repo = gitpython.Repo(repo_path)
        origin = repo.remotes.origin
        origin.pull()
        return True
    except Exception as e:
        logger.error(f"Failed to pull latest: {e}")
        return False