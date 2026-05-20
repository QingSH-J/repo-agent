from repo_agent.repo_context import get_git_diff, get_git_status
from repo_agent.session import RepoSession

def build_basic_context(task: str, repo_session: RepoSession) -> str:
    git_status = get_git_status(repo_session.repo_path)
    git_diff = get_git_diff(repo_session.repo_path)
    files = "\n".join(repo_session.repo_files)

    return f"""
{task}

Repo:
{repo_session.repo_path}

Branch:
{repo_session.repo_branch}

Files:
{files}

Git Diff:
{git_diff or "clean"} 

Git Status:
{git_status or "No changes"}



"""