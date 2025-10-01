import os
from pathlib import Path
from typing import List
from datetime import datetime, timezone

from app.settings import REPO_PATH, PROJECT_STATUS_FILENAME, TIMEZONE

# ---- MCP-ready local tool shims ----
# Swap bodies with MCP client calls (Filesystem/GitLab) in production.

def fs_read(rel_path: str) -> str:
    p = Path(REPO_PATH) / rel_path
    return p.read_text() if p.exists() else ""

def fs_write(rel_path: str, content: str) -> None:
    p = Path(REPO_PATH) / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)

def _candidate_status_names() -> List[str]:
    return [
        "project status.md",
        "Project Status.md",
        "PROJECT_STATUS.md",
        "project_status.md",
        "project-status.md",
        "PROJECT_STATUS.MD",
    ]

def find_project_status_file() -> str:
    # Returns a relative path to the project status file.
    # 1) If PROJECT_STATUS_FILENAME env var is set, use it.
    # 2) Otherwise, search top-level of REPO_PATH for common names.
    # 3) If none found, default to 'PROJECT_STATUS.md'.
    if PROJECT_STATUS_FILENAME:
        return PROJECT_STATUS_FILENAME

    root = Path(REPO_PATH)
    if not root.exists():
        return "PROJECT_STATUS.md"

    names = set(_candidate_status_names())
    for child in root.iterdir():
        if child.is_file() and child.name in names:
            return child.name
    return "PROJECT_STATUS.md"

def read_project_status() -> str:
    path = find_project_status_file()
    return fs_read(path)

def write_project_status(content: str) -> str:
    path = find_project_status_file()
    fs_write(path, content)
    return path

def repo_status() -> str:
    return f"Repo root: {REPO_PATH}"

def git_open_mr(source_branch: str, target_branch: str, title: str, body: str) -> str:
    # Placeholder: write MR request as a file. Replace with GitLab MCP call.
    path = Path(REPO_PATH) / "AGENT_MR_REQUEST.md"
    content = f"# MR: {title}\n\nFrom: {source_branch}\nTo: {target_branch}\n\n{body}\n"
    fs_write("AGENT_MR_REQUEST.md", content)
    return str(path)

def now_iso_local() -> str:
    # Return current timestamp in local timezone (TIMEZONE env), fallback to UTC.
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(TIMEZONE or "America/New_York")
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
