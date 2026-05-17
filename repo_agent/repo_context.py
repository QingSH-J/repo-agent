from pathlib import Path
import subprocess


def run_git(repo_path: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def build_repo_context(repo_path: Path) -> tuple[str, list[str]]:
    branch = run_git(repo_path, ["branch", "--show-current"])

    files_output = run_git(repo_path, ["ls-files", "--cached", "--others", "--exclude-standard"])
    files = [
        line
        for line in files_output.splitlines()
        if line.strip() and is_indexable_file(line)
    ]

    return branch, files


def get_git_diff(repo_path: Path) -> str:
    return run_git(repo_path, ["diff"])


def is_indexable_file(file_path: str) -> bool:
    ignored_parts = {
        ".git",
        ".venv",
        "__pycache__",
    }
    ignored_names = {
        ".env",
        ".repo_agent_history",
    }

    path = Path(file_path)
    if any(part in ignored_parts for part in path.parts):
        return False
    if path.name in ignored_names:
        return False
    if path.suffix == ".pyc":
        return False
    if any(part.endswith(".egg-info") for part in path.parts):
        return False

    return True


def get_git_status(repo_path: Path) -> str:
    return run_git(repo_path, ["status", "--short"])


def stage_file(repo_path: Path, file_path: str) -> None:
    run_git(repo_path, ["add", "--", file_path])


def unstage_file(repo_path: Path, file_path: str) -> None:
    run_git(repo_path, ["restore", "--staged", "--", file_path])

def get_status_diff(repo_path: Path) -> str:
    return run_git(repo_path, ["diff", "--cached"])

def get_staged_status(repo_path: Path) -> str:
    return run_git(repo_path, ["diff", "--cached", "--name-status"])


def has_staged_changes(repo_path: Path) -> bool:
    return bool(get_staged_status(repo_path))


def commit_staged_changes(repo_path: Path, message: str) -> str:
    return run_git(repo_path, ["commit", "-m", message])



"""
New function help you open the .git wherever the current repo is, and get the branch name and all the files in the repo. This will be used as the context for the agent to understand the repo structure and make decisions based on it.
"""
def resolve_git_root(path: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=True,
    )
    return Path(result.stdout.strip()).resolve()

