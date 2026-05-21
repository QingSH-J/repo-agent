from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage

from repo_agent.lc_tools import build_langchain_tools
from repo_agent.llm import build_chat_model, build_reasoning_model
from repo_agent.session import RepoSession

import json
import re

MAX_PLAN_STEPS = 6


PLANNER_AGENT_PROMPT = """You are a planning agent for repository coding tasks.

You may inspect the repository using read-only tools.
Your job is to produce a concise execution plan.

Rules:
- Do not modify files.
- Do not run commands.
- Do not claim you executed the plan.
- Use tools only when needed to understand the task.
- Mention files likely to inspect or modify.
- Produce 3-6 concrete steps.
"""

SCOUT_PROMPT = """You inspect a repository to gather planning context.

You may use read-only tools.
Do not modify files.
Return concise findings relevant to the task.
"""

PLANNER_PROMPT = """You are a reasoning planner for repository coding tasks.

Given the task, initial context, and scout findings, produce a structured execution plan.

Return only valid JSON. Do not wrap it in markdown fences.

Schema:
{
  "steps": [
    {
      "text": "A single executable action for the coding agent."
    }
  ]
}

Rules:
- Produce 2-5 steps. Never produce more than 5 steps.
- Each step must be one concrete executable action.
- Step text must be plain text only.
- Do not use Markdown formatting, headings, bold text, blockquotes, or bullet syntax inside step text.
- Do not include section titles.
- Do not include explanatory notes.
- Do not include meta steps like "Create the execution plan".
- Do not include final answer formatting steps like "Output the final summary".
- Do not include "no modifications required" as a step.
- For read-only analysis tasks, prefer 3 steps: inspect relevant files, extract key facts, summarize findings.
- Mention likely files to inspect or modify.
- Do not claim you executed anything.

Bad steps:
[
  {"text": "**Read repo_agent/llm.py**"},
  {"text": "Note parameters and return types."},
  {"text": "> No modifications to files required."},
  {"text": "Output the final summary."}
]

Good steps:
[
  {"text": "Read repo_agent/llm.py and identify all model builder functions."},
  {"text": "Analyze how each function configures DeepSeek models and environment loading."},
  {"text": "Summarize the module's dependencies, functions, and model selection behavior."}
]
"""

def create_plan(task: str, context: str, repo_session: RepoSession) -> str:
    tools = build_langchain_tools(repo_session, include_write=False)
    agent = create_agent(
        model=build_chat_model(),
        tools=tools,
        system_prompt=SCOUT_PROMPT,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""Task:
{task}

Initial context:
{context}

Create an execution plan
""",
                }
            ]
        }
    )
    scout_findings = result["messages"][-1].content.strip()

    reasoning_llm = build_reasoning_model()
    plan_response = reasoning_llm.invoke(
        [
            SystemMessage(content=PLANNER_PROMPT),
            HumanMessage(
                content=f"""Task:
{task}

Initial context:
{context}

Scout findings:
{scout_findings}

Create the execution plan.
"""
            ),
        ]
    )

    return plan_response.content.strip()



"""Parse a plan into a list of steps."""

def parse_plan_steps(plan: str) -> list[dict[str, str]]:
    try:
        return parse_json_plan_steps(plan)
    except (json.JSONDecodeError, TypeError, ValueError):
        return parse_markdown_plan_steps(plan)


def parse_json_plan_steps(plan: str) -> list[dict[str, str]]:
    text = _strip_json_fence(plan)
    data = json.loads(text)

    if isinstance(data, dict):
        raw_steps = data.get("steps", [])
    elif isinstance(data, list):
        raw_steps = data
    else:
        raise ValueError("Plan JSON must be an object or list.")

    steps: list[dict[str, str]] = []

    for item in raw_steps:
        if isinstance(item, str):
            step_text = item.strip()
        elif isinstance(item, dict):
            step_text = str(item.get("text", "")).strip()
        else:
            continue

        if is_valid_plan_step(step_text):
            steps.append({"text": step_text, "status": "pending"})

    if not steps:
        raise ValueError("Plan JSON did not contain valid steps.")

    return steps[:MAX_PLAN_STEPS]


def parse_markdown_plan_steps(plan: str) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []

    for raw_line in plan.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("```"):
            continue

        if line.startswith("#"):
            continue

        line = re.sub(r"^[-*]\s+", "", line)
        line = re.sub(r"^\d+[.)]\s+", "", line)
        line = re.sub(r"^\[[ xX-]\]\s+", "", line)

        if not line:
            continue

        if is_valid_plan_step(line):
            steps.append({"text": line, "status": "pending"})

    return steps[:MAX_PLAN_STEPS]


def _strip_json_fence(content: str) -> str:
    text = content.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text


def is_valid_plan_step(text: str) -> bool:
    stripped = text.strip()
    normalized = stripped.lower().strip(" .:")

    if not stripped:
        return False

    if stripped.startswith((">", "#")):
        return False

    if stripped.startswith("**") and stripped.endswith("**"):
        return False

    ignored_lines = {
        "create the execution plan",
        "here is the execution plan",
        "here is the plan",
        "execution plan",
        "plan",
        "final answer",
        "output the final summary",
        "synthesize a structured summary",
    }

    if normalized in ignored_lines:
        return False

    banned_phrases = (
        "no modifications",
        "no file modifications",
        "no changes required",
        "present the summary",
        "clear, readable format",
        "output the final",
        "ensure no files are modified",
    )

    if any(phrase in normalized for phrase in banned_phrases):
        return False

    return True
