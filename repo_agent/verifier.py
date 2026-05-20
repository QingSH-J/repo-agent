from typing import TypedDict

from repo_agent.session import RepoSession
from repo_agent.repo_context import get_git_diff, get_git_status, run_git

class VerificationReport(TypedDict):
    is_dirty: bool
    status: str
    unstaged_files: list[str]
    staged_files: list[str]
    untracked_files: list[str]
    unstaged_diff: str
    staged_diff: str

def verify_working_tree(repo_session: RepoSession) -> VerificationReport:
    if repo_session.repo_path is None:
        raise ValueError("No repository loaded.")

    status = get_git_status(repo_session.repo_path)
    unstaged_diff = get_git_diff(repo_session.repo_path)
    staged_diff = run_git(repo_session.repo_path, ["diff", "--cached"])

    unstaged_files, staged_files, untracked_files = parse_short_status(status)

    return {
        "is_dirty": bool(status),
        "status": status,
        "unstaged_files": unstaged_files,
        "staged_files": staged_files,
        "untracked_files": untracked_files,
        "unstaged_diff": unstaged_diff,
        "staged_diff": staged_diff,
    }


def parse_short_status(status: str) -> tuple[list[str], list[str], list[str]]:
    unstaged_files: list[str] = []
    staged_files: list[str] = []
    untracked_files: list[str] = []

    for line in status.splitlines():
        if not line.strip():
            continue

        code = line[:2]
        path = line[3:].strip()

        if code == "??":
            untracked_files.append(path)
            continue

        staged_code = code[0]
        unstaged_code = code[1]

        if staged_code != " ":
            staged_files.append(path)

        if unstaged_code != " ":
            unstaged_files.append(path)

    return unstaged_files, staged_files, untracked_files