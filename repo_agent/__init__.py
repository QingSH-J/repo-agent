from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

class RepoSession:
    def __init__(self):
        self.repo_path : str | None = None
        self.message : list[dict[str, str]] = []

    @property
    def is_repo_loaded(self) -> bool:
        return self.repo_path is not None
    
def handle_command(user_input: str, repo_session: RepoSession) -> bool:
    parts = user_input.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command == "/quit":
        return False
    
    if command == "/help":
        print("/open <repo_path> - Load a repository")
        print("/quit - Exit the application")
        print("/status - Show current repository status")
        print("/diff - Show changes in the repository")
        return True
    
    if command == "/open":
        if not args:
            print("Usage: /open <repo_path>")
            return True
        
        repo_session.repo_path = args
        print(f"Repository loaded: {repo_session.repo_path}")
        return True
    
    if command == "/status":
        if repo_session.is_repo_loaded:
            print(f"Current repository: {repo_session.repo_path}")
        else:
            print("No repository loaded. Use /open <repo_path> to load a repository.")
        
        print(f"Message history: {repo_session.message}")
        return True
    
    if command == "/diff":
        print("TODO")
        return True
    
def handle_natural_language(user_input: str, repo_session: RepoSession) -> bool:
    if not repo_session.is_repo_loaded:
        print("No repository loaded. Use /open <repo_path> to load a repository.")
        return True
    
    repo_session.message.append({"role": "user", "content": user_input})
    print(f"TODO: Process natural language command: {user_input}")
    return True

def main() -> None:
    print("Repo Agent v0.1")
    print("Type /help for a list of commands.")

    prompt_session = PromptSession(history=FileHistory(".repo_agent_history"))
    repo_session = RepoSession()

    while True:
        try:
            user_input = prompt_session.prompt("> ").strip()

            if not user_input:
                continue

            if user_input.startswith("/"):
                should_continue = handle_command(user_input, repo_session)
                if not should_continue:
                    break
            else:
                handle_natural_language(user_input, repo_session)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
        except EOFError:
            print("\nExiting...")
            break

    print("Goodbye!")

if __name__ == "__main__":
    main()