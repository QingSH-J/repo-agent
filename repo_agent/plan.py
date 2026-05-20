from langchain.agents import create_agent
from langchain_core.messages import SystemMessage, HumanMessage

from repo_agent.lc_tools import build_langchain_tools
from repo_agent.llm import build_chat_model, build_reasoning_model
from repo_agent.session import RepoSession

import re


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

Given the task, initial context, and scout findings, produce a concise execution plan.

Rules:
- Use 3-6 concrete steps.
- Mention likely files to inspect or modify.
- Do not claim you executed anything.
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