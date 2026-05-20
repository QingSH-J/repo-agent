import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from repo_agent.path import get_project_dir

def new_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def create_session_id() -> str:
    timestamp = datetime.now().strftime("%Y-m-%dT%H-%M-%S")
    suffix = uuid4().hex[:6]
    return f"{timestamp}_{suffix}"

def get_session_dir(repo_path: Path) -> Path:
    session_dir = get_project_dir(repo_path) / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def get_session_path(repo_path: Path, session_id: str) -> Path:
    return get_session_dir(repo_path) / f"{session_id}.jsonl"

def append_session_event(repo_path: Path, session_id: str, event: dict) -> None:
    session_path = get_session_path(repo_path, session_id)

    event_with_time = {
        "created_at": new_iso(),
        **event,
    }
    with session_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event_with_time, ensure_ascii=False) + "\n")

def create_session(repo_path: Path) -> str:
    session_id = create_session_id()
    append_session_event(
        repo_path,
        session_id,
        {
            "type": "session_start",
            "repo_path": str(repo_path),
        }
    )
    return session_id

def list_sessions(repo_path: Path) -> list[Path]:
    session_dir = get_session_dir(repo_path)
    return sorted(session_dir.glob("*.jsonl"))



"""
Write and Read Session Events for Agent
"""

def read_session_events(repo_path: Path, session_id: str) -> list[dict]:
    session_path = get_session_path(repo_path, session_id)
    if not session_path.exists():
        return []
    
    events: list[dict] = []
    with session_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))

    return events


def get_session_summary_path(repo_path: Path, session_id: str) -> Path:
    return get_session_dir(repo_path) / f"{session_id}.md"

def write_session_summary(repo_path: Path, session_id: str, summary: str) -> Path:
    summary_path = get_session_summary_path(repo_path, session_id)
    summary_path.write_text(summary, encoding="utf-8")
    return summary_path