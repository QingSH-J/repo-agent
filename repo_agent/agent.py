from langchain.agents import create_agent
from langchain.tools import tool

from repo_agent.lc_tools import build_langchain_tools
from repo_agent.llm import build_llm
from repo_agent.session import RepoSession
from repo_agent.repo_context import get_status_diff

SYSTEM_PROMPT = """You are Repo-Agent, a coding assistant working inside a local git repository.

You can inspect and modify the repository using tools.
Prefer searching before reading files.
When you need more context, call search_code or read_file.
Answer concisely and include file paths when useful.
When the user mentions a filename without a directory, you may call read_file directly; the tool can resolve a unique bare filename.
If read_file reports multiple matches or no match, call list_files or search_code to resolve the repo-relative path.

To create or update a file, call write_file with the repo-relative path and the full file content.
The user will be shown a syntax-highlighted preview and asked to confirm before anything is written.
Always write the complete intended file content — never partial snippets.
After writing, remind the user they can stage and commit the file with /stage and /commit.

"""

COMMIT_AGENT_PROMPT = """You write concise git commit messages.

You have access to the staged git diff through tools.
First inspect the staged diff.
Then produce one commit message in this format:

<type>: <summary>

- <bullet>
- <bullet>

Rules:
- Use one of: feat, fix, refactor, docs, test, chore
- Keep summary under 72 characters
- Do not mention files unless helpful
- Do not wrap the response in markdown fences
- If there are no staged changes, say: No staged changes.
"""


def handle_user_task(user_input: str, repo_session: RepoSession) -> str:
    if not repo_session.is_repo_loaded:
        return "No repository loaded. Use /open <repo_path> to load a repository."
    
    tools = build_langchain_tools(repo_session)
    llm = build_llm()
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_input,
                }
            ]
        }
    )

    return result["messages"][-1].content


def suggest_commit_message(repo_session: RepoSession) -> str:
    if not repo_session.is_repo_loaded:
        return "No repository loaded. Use /open <repo_path> to load a repository."

    @tool
    def staged_diff() -> str:
        """Return the currently staged git diff."""
        diff = get_status_diff(repo_session.repo_path)
        return diff or "No staged changes."

    llm = build_llm()
    agent = create_agent(
        model=llm,
        tools=[staged_diff],
        system_prompt=COMMIT_AGENT_PROMPT,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Suggest a commit message for the currently staged changes.",
                }
            ]
        }
    )

    return result["messages"][-1].content.strip()
