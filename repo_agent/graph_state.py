from typing import TypedDict

class AgentGraphState(TypedDict, total=False):
    task: str
    repo_path: str
    branch: str
    memory: str
    file_tree: str
    git_status: str
    git_diff: str
    context: str
    plan: str
    result: str

