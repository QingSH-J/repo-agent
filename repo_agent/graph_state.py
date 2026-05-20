from typing import Literal, TypedDict

"""
Plan state for plan checklist
"""
class PlanStep(TypedDict):
    text: str
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]



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
    plan_steps: list[PlanStep]
    result: str
    verification: dict[str, object]

