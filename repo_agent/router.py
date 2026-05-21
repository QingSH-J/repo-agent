import json
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage

from repo_agent.llm import build_chat_model


Intent = Literal[
    "chat",
    "memory_query",
    "read_only_repo_task",
    "code_change",
    "command_task",
]


class AgentRoute(TypedDict):
    intent: Intent
    write_allowed: bool
    run_command_allowed: bool
    reason: str


ROUTER_PROMPT = """You classify user input for a local coding agent.

Return only valid JSON. Do not wrap it in markdown fences.

Intents:
- chat: general conversation, no repository work required.
- memory_query: asks about previous conversation, session history, or prior work.
- read_only_repo_task: asks to inspect, explain, summarize, review, or analyze repository code without requiring edits.
- code_change: asks to implement, fix, modify, refactor, add, remove, or update repository files.
- command_task: asks to run tests, execute shell commands, build, lint, or inspect command output.

Rules:
- If the user asks not to modify files, write_allowed must be false.
- If the task can be answered by reading/analyzing code, write_allowed should be false.
- Set write_allowed true only when the user clearly wants repository files changed.
- Set run_command_allowed true only when the user asks to run commands/tests/build/lint.
- If ambiguous, prefer read_only_repo_task over code_change.

Schema:
{
  "intent": "chat",
  "write_allowed": false,
  "run_command_allowed": false,
  "reason": "short reason"
}
"""


VALID_INTENTS = {
    "chat",
    "memory_query",
    "read_only_repo_task",
    "code_change",
    "command_task",
}


def route_agent_input(user_input: str) -> AgentRoute:
    try:
        llm = build_chat_model()
        response = llm.invoke(
            [
                SystemMessage(content=ROUTER_PROMPT),
                HumanMessage(content=user_input),
            ]
        )
        return parse_route(response.content, user_input)
    except Exception as error:
        route = fallback_route(user_input)
        route["reason"] = f"Router failed; fallback route used: {error}"
        return route


def parse_route(content: str, user_input: str) -> AgentRoute:
    try:
        data = json.loads(_strip_json_fence(content))
    except json.JSONDecodeError:
        route = fallback_route(user_input)
        route["reason"] = "Router returned invalid JSON; fallback route used."
        return route

    intent = str(data.get("intent", "read_only_repo_task"))
    if intent not in VALID_INTENTS:
        intent = "read_only_repo_task"

    write_allowed = bool(data.get("write_allowed", False))
    run_command_allowed = bool(data.get("run_command_allowed", False))

    if _user_forbids_writes(user_input):
        write_allowed = False

    if intent in {"chat", "memory_query", "read_only_repo_task"}:
        write_allowed = False

    if intent != "command_task":
        run_command_allowed = False

    return {
        "intent": intent,  # type: ignore[typeddict-item]
        "write_allowed": write_allowed,
        "run_command_allowed": run_command_allowed,
        "reason": str(data.get("reason", "")),
    }


def fallback_route(user_input: str) -> AgentRoute:
    lowered = user_input.lower()

    if any(token in lowered for token in ("之前", "剛才", "刚才", "聊了", "記得", "记得", "session", "history")):
        return {
            "intent": "memory_query",
            "write_allowed": False,
            "run_command_allowed": False,
            "reason": "Fallback matched a memory/session query.",
        }

    if any(token in lowered for token in ("pytest", "test", "lint", "build", "run ", "執行", "执行", "跑測試", "跑测试")):
        return {
            "intent": "command_task",
            "write_allowed": False,
            "run_command_allowed": True,
            "reason": "Fallback matched a command or validation request.",
        }

    if _user_forbids_writes(user_input) or any(
        token in lowered
        for token in ("總結", "总结", "分析", "解釋", "解释", "review", "inspect", "summarize")
    ):
        return {
            "intent": "read_only_repo_task",
            "write_allowed": False,
            "run_command_allowed": False,
            "reason": "Fallback matched a read-only repository task.",
        }

    if any(token in lowered for token in ("修", "改", "實作", "实现", "implement", "fix", "refactor", "add ", "update ")):
        return {
            "intent": "code_change",
            "write_allowed": True,
            "run_command_allowed": False,
            "reason": "Fallback matched a code change request.",
        }

    return {
        "intent": "chat",
        "write_allowed": False,
        "run_command_allowed": False,
        "reason": "Fallback found no repository action request.",
    }


def _strip_json_fence(content: str) -> str:
    text = content.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text


def _user_forbids_writes(user_input: str) -> bool:
    lowered = user_input.lower()
    return any(
        token in lowered
        for token in (
            "不要修改",
            "不用修改",
            "不修改",
            "不要改",
            "do not modify",
            "don't modify",
            "no modifications",
            "read-only",
        )
    )
