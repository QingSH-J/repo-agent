from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage

from repo_agent.lc_tools import build_langchain_tools
from repo_agent.llm import build_chat_model, build_reasoning_model
from repo_agent.session import RepoSession

import re
import json


PLANNER_PROMPT = """You are a reasoning planner for repository coding tasks.

Given the task, initial context, and scout findings, produce a structured execution plan.

Return only valid JSON. Do not wrap it in markdown fences.

Schema:
{
  "steps": [
    {
      "text": "A concrete execution step."
    }
  ]
}

Rules:
- Produce 3-6 concrete steps.
- Each step must be actionable by a coding agent.
- Mention likely files to inspect or modify when useful.
- Do not include headings, introductions, explanations, or conclusions.
- Do not claim you executed anything.
- Do not include meta steps like "Create the execution plan".
"""

SCOUT_PROMPT = """You inspect a repository to gather planning context.

You may use read-only tools.
Do not modify files.
Return concise findings relevant to the task.
"""

PLANNER_PROMPT = """You are a reasoning planner for repository coding tasks.

Given the task, initial context, and scout findings, produce a concise execution plan.

Rules:
- Use 3-6 concrete steps.
- Mention likely files to inspect or modify.
- Do not claim you executed anything.
"""

"""
help function
"""
def _strip_json_fence(content: str) -> str:
    text = content.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()
    
    if text.endswith("```"):
        text = text.removesuffix("```").strip()
    
    return text


"""
help function to parse the plan response
"""
def parse_json_plan_response(plan: str) -> list[dict[str, str]]:
    text = _strip_json_fence(plan)

    data = json.loads(text)

    if isinstance(data, list):
        raw_steps = data
    elif isinstance(data,dict):
        raw_steps = data.get("steps", [])
    else:
        raise ValueError("Invalid plan format: expected a JSON object with a 'steps' list or a JSON array.")
    
    steps : list[dict[str, str]] = []

    for item in raw_steps:
        if isinstance(item, str):
            step_text = item.strip()
        elif isinstance(item, dict):
            step_text = item.get("text", "").strip()
        else:
            continue

        if step_text:
            steps.append({"text": step_text, "status": "pending"})
        
    if not steps:
        raise ValueError("No valid steps found in the plan response.")
    
    return steps




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

        steps.append({"text": line, "status": "pending"})

    return steps


def parse_plan_steps(plan: str) -> list[dict[str, str]]:
    try:
        return parse_json_plan_response(plan)
    except Exception:
        return parse_markdown_plan_steps(plan)