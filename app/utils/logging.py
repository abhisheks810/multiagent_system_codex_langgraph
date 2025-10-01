# app/utils/logging.py
import json, os
from pathlib import Path
from app.settings import LOG_DIR, LATEST_RESPONSE_PATH
from app.nodes.tools_mcp import now_iso_local

def _ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)

def log_event(query: str, response: str, source: str):
    """
    Writes:
    - Append-only NDJSON at {LOG_DIR}/history.ndjson (NOT committed)
    - Latest-only Markdown at {LATEST_RESPONSE_PATH} (committed)
    """
    ts = now_iso_local()
    _ensure_dir(LOG_DIR)

    # 1) Append-only NDJSON history
    rec = {"timestamp": ts, "query": query, "source": source, "response": response}
    history_path = Path(LOG_DIR) / "history.ndjson"
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 2) Latest-only Markdown snapshot
    md = f"""# Agent Last Response
**Timestamp:** {ts}  
**Source:** {source}  
**Query:** {query}

## Response
{response}
"""
    Path(LATEST_RESPONSE_PATH).write_text(md, encoding="utf-8")
