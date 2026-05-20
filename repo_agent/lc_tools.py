from langchain.tools import tool

from repo_agent import display
from repo_agent.repo_context import get_git_diff, get_status_diff
from repo_agent.session import RepoSession
from repo_agent.tools import read_repo_file, resolve_repo_file, search_repo_files, write_repo_file


def build_langchain_tools(repo_session: RepoSession, include_write: bool = True):

    @tool
    def read_file(path: str) -> str:
        """Read a file from the repository. A bare filename is resolved when it matches exactly one indexed file."""
        if not repo_session.is_repo_loaded:
            return "No repository loaded."

        try:
            resolved_path = resolve_repo_file(repo_session.repo_files, path)
            content = read_repo_file(repo_session.repo_path, resolved_path)
        except Exception as exc:
            return f"Error reading file: {exc}"

        if resolved_path != path:
            return f"Resolved '{path}' to '{resolved_path}'.\n\n{content}"

        return content
    

    @tool
    def search_code(query: str) -> str:
        """Search for text in indexed repository files."""
        if repo_session.repo_path is None:
            return "No repository loaded."

        matches = search_repo_files(
            repo_session.repo_path,
            repo_session.repo_files,
            query,
        )

        if not matches:
            return f"No matches found for: {query}"

        lines = [
            f"{file_path}:{line_number}: {line}"
            for file_path, line_number, line in matches[:30]
        ]

        remaining = len(matches) - 30
        if remaining > 0:
            lines.append(f"... and {remaining} more matches")

        return "\n".join(lines)
    
    @tool
    def git_diff() -> str:
        """Show the current unstaged git diff."""
        if repo_session.repo_path is None:
            return "No repository loaded."

        diff = get_git_diff(repo_session.repo_path)
        return diff or "No changes."
    
    @tool
    def list_files() -> str:
        """List all files in the repository."""
        if repo_session.repo_path is None:
            return "No repository loaded."
        
        if not repo_session.repo_files:
            return "No files indexed in the repository."
        
        return "\n".join(repo_session.repo_files)

    @tool
    def write_file(path: str, content: str) -> str:
        """Write content to a file in the repository. Displays a preview and requires user confirmation before writing.
        Use this to create new files or overwrite existing ones with generated code or documentation.
        The path should be relative to the repository root (e.g. 'src/utils.py' or 'README.md')."""
        if not repo_session.is_repo_loaded:
            return "No repository loaded."

        try:
            repo_root = repo_session.repo_path.resolve()
            target = (repo_root / path).resolve()
            try:
                target.relative_to(repo_root)
            except ValueError:
                return f"Error: path '{path}' would escape the repository root."

            is_new = not target.exists()
            display.write_preview(path, content, is_new)

            if not display.write_confirm(path, is_new):
                display.write_skipped(path)
                return f"Write to '{path}' was cancelled by the user."

            write_repo_file(repo_session.repo_path, path, content)

            if path not in repo_session.repo_files:
                repo_session.repo_files.append(path)

            display.write_success(path)
            return f"Successfully wrote {len(content)} characters to '{path}'."
        except Exception as exc:
            return f"Error writing file: {exc}"

    tools = [read_file, search_code, git_diff, list_files]
    if include_write:
        tools.append(write_file)

    return tools
