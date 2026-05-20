from langchain.agents import create_agent

from repo_agent.lc_tools import build_langchain_tools
from repo_agent.llm import build_llm
from repo_agent.session import RepoSession

PLANNER_AGENT_PROMPT = """You are a planning agent for repository coding tasks.

You may inspect the repository using read-only tools.
Your job is to produce a concise execution plan.

Rules:
- Do not modify files.
- Do not claim you executed the plan.
- Use tools only when needed to understand the task.
- Mention files likely to inspect or modify.
- Produce 3-6 concrete steps.
"""

def create_plan(task: str, context: str, repo_session: RepoSession) -> str:
    tools = build_langchain_tools(repo_session)
    agent = create_agent(
        model=build_llm(),
        tools=tools,
        system_prompt=PLANNER_AGENT_PROMPT,
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
    return result["messages"][-1].content.strip()