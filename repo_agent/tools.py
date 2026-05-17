from pathlib import Path
import subprocess


def resolve_repo_file(files: list[str], requested_path: str) -> str:
    requested_path = requested_path.strip()

    if requested_path in files:
        return requested_path

    normalized_path = requested_path.lstrip("./")
    if normalized_path in files:
        return normalized_path

    basename_matches = [
        file_path
        for file_path in files
        if Path(file_path).name == requested_path
    ]

    if len(basename_matches) == 1:
        return basename_matches[0]

    if len(basename_matches) > 1:
        matches = "\n".join(f"- {file_path}" for file_path in basename_matches)
        raise ValueError(
            f"Multiple files match '{requested_path}'. Use one of:\n{matches}"
        )

    raise FileNotFoundError(
        f"File '{requested_path}' was not found. Use /files or search_code to find the correct path."
    )


def read_repo_file(repo_path: Path, file_path: str) -> str:
    target_path = (repo_path / file_path).resolve()

    if not target_path.exists():
        raise FileNotFoundError(f"File '{file_path}' does not exist in the repository.")
    
    if not target_path.is_file():
        raise ValueError(f"Path '{file_path}' is not a file.")
    
    return target_path.read_text(encoding="utf-8")


def search_repo_files(repo_path: Path, files: list[str], query: str) -> list[tuple[str, int, str]]:
    matches = []
    for file_path in files:
        target_path = repo_path / file_path

        if not target_path.is_file():
            continue

        try:
            lines = target_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_num, line in enumerate(lines, start=1):
            if query.lower() in line.lower():
                matches.append((file_path, line_num, line.strip()))
    return matches



def write_repo_file(repo_path: Path, file_path: str, content: str) -> bool:
    repo_root = repo_path.resolve()
    target_path = (repo_root / file_path).resolve()

    try:
        target_path.relative_to(repo_root)
    except ValueError:
        raise ValueError(f"Path '{file_path}' escapes the repository root.")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    return target_path.exists()


def run_repo_command(repo_path: Path, command: str) -> tuple[int, str, str]:
    result = subprocess.run(
        command.split(),
        cwd=repo_path,
        text=True,
        capture_output=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()
