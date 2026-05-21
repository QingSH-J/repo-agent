from typing import Literal, TypedDict

"""
Plan state for plan checklist
"""
class PlanStep(TypedDict):
    text: str
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]

"""
Step state for the entire agent graph. This is the shared state that gets passed between nodes in the graph.
"""
class StepResult(TypedDict):
    step: str
    status: Literal["completed", "failed"]
    result: str



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
    step_results: list[StepResult]
    summary: str
