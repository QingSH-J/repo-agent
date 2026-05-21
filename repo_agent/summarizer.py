from repo_agent.llm import build_reasoning_model
from langchain_core.messages import SystemMessage, HumanMessage


SUMMARIZER_PROMPT = """You are a coding agent run summarizer.

Summarize the completed agent run using only the provided task, plan, execution result, and verification report.

Rules:
- Be concise.
- Do not invent files or changes.
- Mention whether the working tree is clean or dirty.
- Mention staged, unstaged, and untracked files if present.
- If verification shows no file changes, say so clearly.
- Include practical next steps only when useful.
"""


def summarize_agent_run(task: str, plan: str, result: str, verification_report: dict[str, object]) -> str:
    llm = build_reasoning_model()
    response = llm.invoke(
        [
            SystemMessage(content=SUMMARIZER_PROMPT),
            HumanMessage(
                content=f"""Task:
{task}

Execution Plan:
{plan}

Execution Result:
{result}

Verification Report:
{verification_report}

Summarize the agent run based on the above information.
"""           ),
        ]
    )
    return response.content.strip()