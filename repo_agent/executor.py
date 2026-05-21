from langchain.agents import create_agent

from repo_agent.lc_tools import build_langchain_tools
from repo_agent.llm import build_chat_model
from repo_agent.session import RepoSession
from repo_agent.token_usage import empty_token_usage, extract_agent_usage


EXECUTOR_PROMPT = """You are Repo-Agent's step executor.

You execute exactly one plan step at a time inside a local git repository.

Rules:
- Focus on the current step only.
- Use completed step results as context, but do not redo completed work unless required.
- Use tools when you need to inspect or modify files.
- If modifying a file, write the full intended file content.
- Do not claim the whole task is complete unless this current step completes the whole task.
- Return a concise result for this step, including files touched or findings.
"""


def execute_plan_step(
        *,
        task: str,
        context: str,
        plan: str,
        current_step: str,
        completed_results: list[str],
        repo_session: RepoSession,
        include_write: bool = True,
) -> dict[str, object]:
    if not repo_session.is_repo_loaded:
        return {
            "content": "No repository loaded. Use /open <repo_path> to load a repository.",
            "token_usage": empty_token_usage(),
        }
    
    tools = build_langchain_tools(repo_session, include_write=include_write)
    agent = create_agent(
        model=build_chat_model(),
        tools=tools,
        system_prompt=EXECUTOR_PROMPT,
    )

    completed_context = "\n\n".join(
        f"{index + 1}. {result}"
        for index, result in enumerate(completed_results)
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""Task:
{task}

Context:
{context}

Execution Plan:
{plan}

Completed Steps:
{completed_context or "None yet"}

Current Step to Execute:
{current_step}

Execute the current step based on the above information and return the result.
"""


                }
            ]
        }
    )

    final_result = result["messages"][-1]
    return {
        "content": final_result.content.strip(),
        "token_usage": extract_agent_usage(result)
    }   
