from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
console = Console()


def banner() -> None:
    console.print("[bold cyan]Repo Agent v0.1[/bold cyan]")
    console.print("[dim]Type /help for commands.[/dim]\n")


def info(message: str) -> None:
    console.print(f"[cyan]>[/cyan] {message}")


def success(message: str) -> None:
    console.print(f"[green]OK[/green] {message}")


def warning(message: str) -> None:
    console.print(f"[yellow]![/yellow] {message}")


def error(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")


def goodbye() -> None:
    console.print("[dim]Goodbye.[/dim]")


def help() -> None:
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description")
    table.add_row("/open <repo_path>", "Load a repository")
    table.add_row("/status", "Show current repository status")
    table.add_row("/files", "Show indexed files")
    table.add_row("/read <file_path>", "Read a file from the repository")
    table.add_row("/search <query>", "Search indexed repository files")
    table.add_row("/diff", "Show unstaged git diff")
    table.add_row("/run <command>", "Run a command in the loaded repository")
    table.add_row("/quit", "Exit")
    table.add_row("/refresh", "Reload the current repository context")
    table.add_row("/tree", "Show the file tree of the repository")
    table.add_row("/git-status", "Show the short git status of the repository")
    table.add_row("/stage <path>", "Stage one indexed file")
    table.add_row("/unstage <path>", "Unstage one indexed file")
    table.add_row("/commit-preview", "Show the git diff of staged changes")
    table.add_row("/commit-message", "Suggest a commit message for staged changes")
    table.add_row("/commit <message>", "Commit staged changes")
    table.add_row("/write <path>", "Write content to a file (opens editor prompt)")
    table.add_row("/git-tree", "Show recent git commit history as a tree")
    table.add_row("/agent [task_description]", "Enter agent mode, or run one routed agent task")
    table.add_row("/back", "Exit agent mode")
    table.add_row("/session", "Show current session info")
    table.add_row("/sessions", "List saved sessions")
    table.add_row("/session-summary", "Summarize the current session with an LLM")
    console.print(Panel(table, title="Commands", border_style="cyan"))



def status(
    repo_path: Path | None,
    branch: str | None,
    files_count: int,
    messages_count: int,
) -> None:
    if repo_path is None:
        warning("No repository loaded. Use /open <repo_path> to load a repository.")
        return

    table = Table(show_header=False, box=None)
    table.add_row("Repo", str(repo_path))
    table.add_row("Branch", branch or "(detached)")
    table.add_row("Files", str(files_count))
    table.add_row("Messages", str(messages_count))
    console.print(Panel(table, title="Status", border_style="green"))


def files(file_paths: list[str], max_files: int = 40) -> None:
    if not file_paths:
        warning("No files found in the repository.")
        return

    rendered = "\n".join(file_paths[:max_files])
    remaining = len(file_paths) - max_files
    if remaining > 0:
        rendered += f"\n[dim]... and {remaining} more files[/dim]"

    console.print(Panel(rendered, title="Files", border_style="blue"))


def file_content(path: str, content: str) -> None:
    lexer = _lexer_for_path(path)
    syntax = Syntax(content, lexer, line_numbers=True, word_wrap=False)
    console.print(Panel(syntax, title=path, border_style="blue"))


def search_results(
    query: str,
    matches: list[tuple[str, int, str]],
    max_matches: int = 20,
) -> None:
    if not matches:
        warning(f"No matches found for '{query}'.")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("File", style="cyan")
    table.add_column("Line", justify="right", style="magenta", no_wrap=True)
    table.add_column("Match")

    for file_path, line_num, line in matches[:max_matches]:
        table.add_row(file_path, str(line_num), line)

    remaining = len(matches) - max_matches
    if remaining > 0:
        table.add_row("[dim]...[/dim]", "", f"[dim]and {remaining} more matches[/dim]")

    console.print(Panel(table, title=f"Search: {query}", border_style="cyan"))


def diff(content: str) -> None:
    if not content:
        info("No changes in the repository.")
        return

    syntax = Syntax(content, "diff", line_numbers=False, word_wrap=False)
    console.print(Panel(syntax, title="Git Diff", border_style="yellow"))


def command_result(returncode: int, stdout: str, stderr: str) -> None:
    status_text = f"Exit code: {returncode}"
    border_style = "green" if returncode == 0 else "red"

    sections = [status_text]
    if stdout:
        sections.append(f"[bold]STDOUT[/bold]\n{stdout}")
    if stderr:
        sections.append(f"[bold red]STDERR[/bold red]\n{stderr}")

    console.print(Panel("\n\n".join(sections), title="Command", border_style=border_style))


def assistant(message: str) -> None:
    console.print(Panel(Markdown(message), title="Repo Agent", border_style="cyan"))


def _lexer_for_path(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".toml": "toml",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".sh": "bash",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".css": "css",
        ".html": "html",
    }.get(suffix, "text")


def file_tree(root_name: str, file_paths: list[str]) -> None:
    if not file_paths:
        warning("No files found in the repository.")
        return
    
    tree = Tree(root_name)

    nodes = {"" : tree}

    for file_path in sorted(file_paths):
        parts = file_path.split("/")
        current_path = ""

        for index, part in enumerate(parts):
            parent_path = current_path
            current_path = "/".join(parts[: index + 1])
            is_file = index == len(parts) - 1

            if current_path in nodes:
                continue

            label = part if is_file else f"[bold cyan]{part}[/bold cyan]"
            nodes[current_path] = nodes[parent_path].add(label)

    console.print(tree)


def git_status(branch: str | None, status_output: str) -> None:
    table = Table(show_header=False, box=None)
    table.add_row("Branch", branch or "(detached)")

    if status_output:
        table.add_row("Working Directory", "dirty")
    else:
        table.add_row("Working Directory", "clean")

    console.print(Panel(table, title="Git Status", border_style="green"))

    if status_output:
        syntax = Syntax(status_output, "text", line_numbers=False, word_wrap=False)
        console.print(Panel(syntax, title="Changes", border_style="yellow"))
    

def commit_preview(staged_status: str, staged_diff: str) -> None:
    if not staged_status:
        warning("No staged changes to commit.")
        return
    
    status_syntax = Syntax(staged_status, "text", line_numbers=False, word_wrap=False)
    console.print(Panel(status_syntax, title="Staged Changes", border_style="green"))

    if staged_diff:
        diff_syntax = Syntax(staged_diff, "diff", line_numbers=False, word_wrap=False)
        console.print(Panel(diff_syntax, title="Staged Diff", border_style="green"))


def commit_message(message: str) -> None:
    console.print(Panel(Markdown(message), title="Suggested Commit Message", border_style="green"))


def commit_result(output: str, status_output: str) -> None:
    console.print(Panel(output or "Commit created.", title="Commit", border_style="green"))

    if status_output:
        syntax = Syntax(status_output, "text", line_numbers=False, word_wrap=False)
        console.print(Panel(syntax, title="Remaining Changes", border_style="yellow"))
    else:
        success("Working tree clean.")


def write_preview(path: str, content: str, is_new_file: bool) -> None:
    action = "[green]CREATE[/green]" if is_new_file else "[yellow]OVERWRITE[/yellow]"
    lexer = _lexer_for_path(path)
    syntax = Syntax(content, lexer, line_numbers=True, word_wrap=False)
    console.print(
        Panel(
            syntax,
            title=f"{action} [bold]{path}[/bold]",
            border_style="yellow",
        )
    )


def write_confirm(path: str, is_new_file: bool) -> bool:
    action = "Create" if is_new_file else "Overwrite"
    try:
        answer = console.input(
            f"[bold yellow]?[/bold yellow] {action} [cyan]{path}[/cyan]? \\[y/N] "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


def write_success(path: str) -> None:
    console.print(f"[green]Written[/green] {path}")


def write_skipped(path: str) -> None:
    console.print(f"[dim]Skipped write to {path}.[/dim]")



"""
Show recent git commit history as a tree
"""
def git_tree(tree_output: str) -> None:
    if not tree_output:
        warning("No git history found.")
        return
    
    syntax = Syntax(tree_output, "text", line_numbers=False, word_wrap=False)
    console.print(Panel(syntax, title="Git Commit History", border_style="cyan"))



"""
LangGraph Agent Display
"""
def agent_start(task: str) -> None:
    console.print()
    console.print(Panel(task, title="Agent Task", border_style="cyan"))


def agent_step(name: str, detail: str | None = None) -> None:
    console.print(f"[cyan]>[/cyan] [bold]{name}[/bold]")
    if detail:
        console.print(f"  [dim]- {detail}[/dim]")


def agent_success(message: str = "Agent task complete.") -> None:
    console.print(f"[green]OK[/green] {message}")


def agent_error(message: str) -> None:
    console.print(f"[red]Error:[/red] {message}")


def agent_result(result: str) -> None:
    console.print(Panel(Markdown(result), title="Agent Result", border_style="green"))



"""
Session Display
"""
def session_info(session_id: str | None, session_path: str | None) -> None:
    if not session_id:
        warning("No active session. Use /open <repo_path> first.")
        return

    table = Table(show_header=False, box=None)
    table.add_row("Session", str(session_id))
    table.add_row("Path", str(session_path) or "")
    console.print(Panel(table, title="Session", border_style="magenta"))


def sessions(paths: list[Path]) -> None:
    if not paths:
        warning("No sessions found.")
        return

    rendered = "\n".join(path.name for path in paths)
    console.print(Panel(rendered, title="Sessions", border_style="magenta"))

def session_summary(summary: str, path: str | None = None) -> None:
    console.print(Panel(Markdown(summary), title="Session Summary", border_style="magenta"))
    if path:
        info(f"Saved summary: {path}")




"""
Function to display the state of plan steps
"""

def plan_checklist(steps: list[dict[str, str]], title: str = "Plan") -> None:
    if not steps:
        warning("No plan steps found.")
        return
    
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("Status", no_wrap=True, width=5)
    table.add_column("Step")

    marks = {
        "pending": Text("[ ]", style="dim"),
        "in_progress": Text("[>]", style="cyan"),
        "completed": Text("[x]", style="green"),
        "failed": Text("[!]", style="red"),
        "skipped": Text("[-]", style="yellow"),
    }

    for step in steps:
        status = step.get("status", "pending")
        text = step.get("text", "").strip()
        mark = marks.get(status, marks["pending"])
        if text:
            table.add_row(mark, text)

    console.print(Panel(table, title=title, border_style="cyan"))


""""
Function for displaying a verification result with details
"""

def verification_report(report: dict[str, object]) -> None:
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value")

    is_dirty = bool(report.get("is_dirty"))
    status_label = "[yellow]dirty[/yellow]" if is_dirty else "[green]clean[/green]"

    table.add_row("Working Tree", status_label)
    table.add_row("Staged Files", str(len(report.get("staged_files", []))))
    table.add_row("Unstaged Files", str(len(report.get("unstaged_files", []))))
    table.add_row("Untracked Files", str(len(report.get("untracked_files", []))))

    console.print(Panel(table, title="Verification", border_style="magenta"))

    status = str(report.get("status") or "")
    if status:
        console.print(
            Panel(
                Syntax(status, "text", line_numbers=False, word_wrap=False),
                title="Git Status",
                border_style="yellow",
            )
        )

    unstaged_diff = str(report.get("unstaged_diff") or "")
    if unstaged_diff:
        console.print(
            Panel(
                Syntax(unstaged_diff, "diff", line_numbers=False, word_wrap=False),
                title="Unstaged Diff",
                border_style="yellow",
            )
        )

    staged_diff = str(report.get("staged_diff") or "")
    if staged_diff:
        console.print(
            Panel(
                Syntax(staged_diff, "diff", line_numbers=False, word_wrap=False),
                title="Staged Diff",
                border_style="green",
            )
        )

"""
For displaying token usage metrics in a readable format
"""
def token_usage(usage: dict[str, int]) -> None:
    table = Table(show_header=False, box=None)
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Tokens", justify="right")

    table.add_row("Input Tokens", str(usage.get("input_tokens", 0)))
    table.add_row("Output Tokens", str(usage.get("output_tokens", 0)))
    table.add_row("Total Tokens", str(usage.get("total_tokens", 0)))

    console.print(Panel(table, title="Token Usage", border_style="blue"))
