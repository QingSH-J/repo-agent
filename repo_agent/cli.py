from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pathlib import Path
import subprocess
from langchain_core.messages import HumanMessage, SystemMessage
from repo_agent import display
from repo_agent.session import RepoSession
from repo_agent.repo_context import (
    build_repo_context,
    get_git_diff,
    get_git_status,
    stage_file,
    unstage_file,
    get_staged_status,
    get_status_diff,
    has_staged_changes,
    commit_staged_changes,
    resolve_git_root,
    get_git_tree
)
from repo_agent.tools import read_repo_file, resolve_repo_file, search_repo_files, run_repo_command, write_repo_file
from repo_agent.agent import handle_user_task, suggest_commit_message, summarize_current_session
from repo_agent.llm import build_chat_model
from repo_agent.path import get_history_path

from repo_agent.graph import run_graph_agent
from repo_agent.router import route_agent_input

from repo_agent.session_store import (
    list_sessions,
    create_session,
    append_session_event,
    get_session_path,
    read_session_events,
)




def handle_command(user_input: str, repo_session: RepoSession) -> bool:
    parts = user_input.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command == "/quit":
        return False
    
    if command == "/help":
        display.help()
        return True
    
    if command == "/open":
        if not args:
            display.warning("Usage: /open <repo_path>")
            return True
        
        repo_path = Path(args).expanduser().resolve()

        if not repo_path.exists():
            display.error(f"Path '{repo_path}' does not exist.")
            return True
        
        """
        No need to check
        """
        #if not (repo_path / ".git").exists():
        #    display.error(
        
        try:
            repo_path = resolve_git_root(Path(args).expanduser().resolve())
        except subprocess.CalledProcessError as e:
            display.error(f"Error resolving git root: {e.stderr}")
            return True
        
        try:
            branch, files = build_repo_context(repo_path)
        except subprocess.CalledProcessError as e:
            display.error(f"Error loading repository: {e.stderr}")
            return True
        
        repo_session.repo_path = repo_path
        repo_session.repo_branch = branch
        repo_session.repo_files = files

        repo_session.session_id = create_session(repo_session.repo_path)

        append_session_event(
            repo_session.repo_path,
            repo_session.session_id,
            {
                "type": "repo_opened",
                "branch": repo_session.repo_branch,
                "files": repo_session.repo_files,
            }
        )

        display.info(f"Repository opened: {repo_session.repo_path}")
        
        
        display.success(f"Repository loaded: {repo_session.repo_path}")
        display.info(f"Current branch: {repo_session.repo_branch or '(detached)'}")
        display.info(f"Files in repository: {len(repo_session.repo_files)}")



        return True
    

    
    if command == "/status":
        display.status(
            repo_session.repo_path,
            repo_session.repo_branch,
            len(repo_session.repo_files),
            len(repo_session.message),
        )
        return True
    
    if command == "/files":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        display.files(repo_session.repo_files)
        return True
    
    if command == "/read":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        if not args:
            display.warning("Usage: /read <file_path>")
            return True
        
        try:
            file_path = resolve_repo_file(repo_session.repo_files, args)
            content = read_repo_file(repo_session.repo_path, file_path)
            display.file_content(file_path, content)
        except Exception as e:
            display.error(f"Error reading file: {e}")
        
        return True
    


    if command == "/search":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        if not args:
            display.warning("Usage: /search <query>")
            return True
        
        matches = search_repo_files(repo_session.repo_path, repo_session.repo_files, args)
        display.search_results(args, matches)
        return True

    
    if command == "/diff":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        try:
            diff = get_git_diff(repo_session.repo_path)
        except subprocess.CalledProcessError as e:
            display.error(f"Error getting git diff: {e.stderr}")
            return True
        
        display.diff(diff)
        return True
    
    if command == "/run":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        if not args:
            display.warning("Usage: /run <command>")
            return True
        
        returncode, stdout, stderr = run_repo_command(repo_session.repo_path, args)
        display.command_result(returncode, stdout, stderr)
        return True
    
    if command == "/refresh":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        try:
            branch, files = build_repo_context(repo_session.repo_path)
        except subprocess.CalledProcessError as e:
            display.error(f"Error refreshing repository context: {e.stderr}")
            return True
        
        repo_session.repo_branch = branch
        repo_session.repo_files = files

        display.success("Repository context refreshed.")
        display.info(f"Current branch: {repo_session.repo_branch or '(detached)'}")
        display.info(f"Files in repository: {len(repo_session.repo_files)}")

        return True
    
    if command == "/tree":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        root_name = repo_session.repo_path.name if repo_session.repo_path else "Repo"

        display.file_tree(root_name, repo_session.repo_files)
        return True
    
    if command == "/git-status":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        try:
            status = get_git_status(repo_session.repo_path)
        except subprocess.CalledProcessError as e:
            display.error(f"Error getting git status: {e.stderr}")
            return True
        
        display.git_status(repo_session.repo_branch, status)
        return True

    if command == "/stage":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True

        if not args:
            display.warning("Usage: /stage <path>")
            return True

        try:
            file_path = resolve_repo_file(repo_session.repo_files, args)
            stage_file(repo_session.repo_path, file_path)
            status = get_git_status(repo_session.repo_path)
        except (FileNotFoundError, ValueError) as e:
            display.error(str(e))
            return True
        except subprocess.CalledProcessError as e:
            display.error(f"Error staging file: {e.stderr}")
            return True

        display.success(f"Staged: {file_path}")
        display.git_status(repo_session.repo_branch, status)
        return True
    
    if command == "/unstage":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        if not args:
            display.warning("Usage: /unstage <path>")
            return True
        
        try:
            file_path = resolve_repo_file(repo_session.repo_files, args)
            unstage_file(repo_session.repo_path, file_path)
            status = get_git_status(repo_session.repo_path)
        except (FileNotFoundError, ValueError) as e:
            display.error(str(e))
            return True
        except subprocess.CalledProcessError as e:
            display.error(f"Error unstaging file: {e.stderr}")
            return True
        
        display.success(f"Unstaged: {file_path}")
        display.git_status(repo_session.repo_branch, status)
        return True
    
    if command == "/commit-preview":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        try:
            staged_status = get_staged_status(repo_session.repo_path)
            staged_diff = get_status_diff(repo_session.repo_path)
        except subprocess.CalledProcessError as e:
            display.error(f"Error getting commit preview: {e.stderr}")
            return True
        display.commit_preview(staged_status, staged_diff)
        return True
    
    if command == "/commit-message":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        try:
            message = suggest_commit_message(repo_session)
        except subprocess.CalledProcessError as e:
            display.error(f"Error getting staged diff: {e.stderr}")
            return True

        display.commit_message(message)
        return True

    if command == "/commit":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True

        message = args.strip()
        if not message:
            display.warning("Usage: /commit <message>")
            return True

        try:
            if not has_staged_changes(repo_session.repo_path):
                display.warning("No staged changes. Use /stage <path> first.")
                return True

            output = commit_staged_changes(repo_session.repo_path, message)
            status = get_git_status(repo_session.repo_path)
        except subprocess.CalledProcessError as e:
            display.error(f"Error creating commit: {e.stderr}")
            return True

        display.commit_result(output, status)
        return True

    if command == "/write":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True

        if not args:
            display.warning("Usage: /write <path>")
            return True

        file_path = args.strip()
        display.info(f"Enter content for '{file_path}'. Type a line with just '---END---' when done.")

        lines = []
        try:
            while True:
                line = input()
                if line == "---END---":
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            display.warning("Write cancelled.")
            return True

        content = "\n".join(lines)
        if not content:
            display.warning("No content provided. Write cancelled.")
            return True

        from pathlib import Path as _Path
        target = (repo_session.repo_path / file_path).resolve()
        is_new = not target.exists()

        display.write_preview(file_path, content, is_new)

        if not display.write_confirm(file_path, is_new):
            display.write_skipped(file_path)
            return True

        try:
            write_repo_file(repo_session.repo_path, file_path, content)
            if file_path not in repo_session.repo_files:
                repo_session.repo_files.append(file_path)
            display.write_success(file_path)
        except Exception as e:
            display.error(f"Error writing file: {e}")

        return True
    
    if command == "/git-tree":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        try:
            tree = get_git_tree(repo_session.repo_path)
        except subprocess.CalledProcessError as e:
            display.error(f"Error getting git tree: {e.stderr}")
            return True
        
        display.git_tree(tree)
        return True
    
    if command == "/agent":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        if not args:
            repo_session.agent_mode = True
            display.success("Agent mode enabled. Enter a task for the agent to perform.")
            return True

        return handle_agent_input(args, repo_session)
    
    """return to normal mode"""
    if command == "/back":
        if repo_session.agent_mode:
            repo_session.agent_mode = False
            display.success("Exited agent mode.")
        else:
            display.warning("Not in agent mode.")
        return True
    

    #Session Commands
    if command == "/session":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        session_path = None
        if repo_session.session_id:
            session_path = get_session_path(repo_session.repo_path, repo_session.session_id)
        
        display.session_info(repo_session.session_id, session_path)
        return True
    
    #Session command 2
    if command == "/sessions":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        
        paths = list_sessions(repo_session.repo_path)
        display.sessions(paths)
        return True
    
    #Session summary command
    if command == "/session-summary":
        if not repo_session.is_repo_loaded:
            display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
            return True
        try:
            summary, path = summarize_current_session(repo_session)
        except Exception as e:
            display.error(f"Error summarizing session: {e}")
            return True
        display.session_summary(summary, path)
        return True

    """
    tackle the unknown command case.
    """
    display.warning(f"Unknown command: {command}. Type /help.")
    return True
    
    
def handle_natural_language(user_input: str, repo_session: RepoSession) -> bool:
    if not repo_session.is_repo_loaded:
        display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
        return True
    
    repo_session.message.append({"role": "user", "content": user_input})

    record_event(
        repo_session,
        {
            "type": "user_input",
            "text": user_input,
        }
    )

    response = handle_user_task(user_input, repo_session)
    display.assistant(response)

    record_event(
        repo_session,
        {
            "type": "assistant_response",
            "text": response,
        }
    )
    repo_session.message.append({"role": "assistant", "content": response})
    return True

"""
Help Functions
"""
def record_event(repo_session: RepoSession, event: dict) -> None:
    if not repo_session.is_repo_loaded or not repo_session.session_id:
        return
    
    append_session_event(
        repo_session.repo_path,
        repo_session.session_id,
        event,
    )

"""
functio to handle agent mode input
"""
def handle_agent_input(user_input: str, repo_session: RepoSession) -> bool:
    if not repo_session.is_repo_loaded:
        display.warning("No repository loaded. Use /open <repo_path> to load a repository.")
        return True

    route = route_agent_input(user_input)
    display.info(
        f"Route: {route['intent']} "
        f"(write_allowed={route['write_allowed']}, run_command_allowed={route['run_command_allowed']})"
    )
    
    record_event(
        repo_session,
        {
            "type": "agent_task",
            "text": user_input,
            "route": route,
        }
    )

    if route["intent"] == "chat":
        response = answer_agent_chat(user_input, repo_session)
        display.assistant(response)
        repo_session.message.append({"role": "user", "content": user_input})
        repo_session.message.append({"role": "assistant", "content": response})
        record_event(
            repo_session,
            {
                "type": "agent_chat_response",
                "text": response,
                "route": route,
            }
        )
        return True

    if route["intent"] == "memory_query":
        response = answer_memory_query(repo_session)
        display.assistant(response)
        record_event(
            repo_session,
            {
                "type": "agent_memory_response",
                "text": response,
                "route": route,
            }
        )
        return True

    display.agent_start(user_input)

    try:
        result = run_graph_agent(
            user_input,
            repo_session,
            write_allowed=route["write_allowed"],
        )
    except Exception as e:
        display.error(f"Error running agent: {e}")
        return True
    
    record_event(
        repo_session,
        {
            "type": "agent_result",
            "text": result,
        }
    )

    display.agent_success()
    display.agent_result(result)
    return True


def answer_agent_chat(user_input: str, repo_session: RepoSession) -> str:
    messages = [
        SystemMessage(
            content=(
                "You are Repo-Agent in agent chat mode. Answer conversationally and briefly. "
                "Do not claim you inspected or modified repository files. "
                "If the user asks for repository work, say they should ask directly and you can route it."
            )
        )
    ]

    for message in repo_session.message[-6:]:
        role = message.get("role")
        content = message.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))

    messages.append(HumanMessage(content=user_input))
    response = build_chat_model().invoke(messages)
    return response.content.strip()


def answer_memory_query(repo_session: RepoSession) -> str:
    if not repo_session.session_id or not repo_session.repo_path:
        return "No active session is available yet."

    events = read_session_events(repo_session.repo_path, repo_session.session_id)
    if not events:
        return "I do not have any session events recorded yet."

    recent_events = events[-12:]
    lines = ["Here is what I can see from the current session:"]

    for event in recent_events:
        event_type = event.get("type", "event")
        created_at = event.get("created_at", "")
        text = event.get("text")

        if text:
            lines.append(f"- {created_at} `{event_type}`: {text}")
        else:
            summary = {
                key: value
                for key, value in event.items()
                if key not in {"files"} and key != "created_at"
            }
            lines.append(f"- {created_at} `{event_type}`: {summary}")

    return "\n".join(lines)



def main() -> None:
    display.banner()

    prompt_session = PromptSession(history=FileHistory(str(get_history_path())))
    repo_session = RepoSession()

    while True:
        try:
            prompt_text = "Agent> " if repo_session.agent_mode else "> "
            user_input = prompt_session.prompt(prompt_text).strip()

            if not user_input:
                continue

            if user_input.startswith("/"):
                should_continue = handle_command(user_input, repo_session)
                if not should_continue:
                    break
            else:
                if repo_session.agent_mode:
                    handle_agent_input(user_input, repo_session)
                else:
                    handle_natural_language(user_input, repo_session)

        except KeyboardInterrupt:
            display.warning("Interrupted.")
            break
        except Exception as e:
            display.error(str(e))
        except EOFError:
            display.warning("EOF received.")
            break

    display.goodbye()

if __name__ == "__main__":
    main()
