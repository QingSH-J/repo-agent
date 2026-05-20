import hashlib
import os
from pathlib import Path

def get_repo_agent_home():
    """
    Get the home directory of the repo agent.
    """
    return Path(os.getenv("REPO_AGENT_HOME", Path.home() / ".repo-agent")).expanduser()

def ensure_repo_agent_home():
    """
    Ensure that the repo agent home directory exists.
    """
    home = get_repo_agent_home()
    home.mkdir(parents=True, exist_ok=True)
    return home

def get_history_path():
    """
    Get the path to the history file.
    """
    home = ensure_repo_agent_home()
    return home / "history"

def get_project_id(repo_path: Path) -> str:
    resolved = str(repo_path.resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:12]


def get_project_dir(repo_path: Path) -> Path:
    project_dir = ensure_repo_agent_home() / "projects" / get_project_id(repo_path)
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir
