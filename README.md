# LangGraph Multi-Agent System (Planner uses RAG + Product Manager)

This version upgrades the LangGraph system with:
- **RAG-based Planner**: reads your repo’s _Project Status_ markdown to ground planning.
- **Product Manager agent**: after integration, updates the **Project Status** markdown with a dated entry (feature details, pitfalls, final summary).

Graph:
`plan (RAG) → (uiux || tester || qa_geo) [parallel] → integrate → product_manager → open_mr`

Tool nodes are **MCP-ready shims** (local FS by default). Swap them to Filesystem/GitLab MCP later.

## Quick Start (Docker Compose)

1) Copy `.env.example` → `.env`, set:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
HOST_REPO_PATH=/ABS/PATH/TO/YOUR/REPO
TIMEZONE=America/New_York                # optional
PROJECT_STATUS_FILENAME=PROJECT_STATUS.md # optional; searched if absent
```

2) Up:
```bash
docker compose up --build -d
```

3) Run a feature:
```bash
docker compose exec langgraph python -m app.run "Add reverse geocoding on map click and show popup"
```

4) Review:
```bash
git -C "$HOST_REPO_PATH" status
git -C "$HOST_REPO_PATH" diff
# Project status file updated at: $PROJECT_STATUS_FILENAME (or discovered file)
```

5) Down:
```bash
docker compose down
```

## Local (no Docker)
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o
export REPO_PATH=/ABS/PATH/TO/YOUR/REPO
export TIMEZONE=America/New_York
python -m app.run "Add reverse geocoding on map click and show popup"
```

## MCP Integration
Replace functions in `app/nodes/tools_mcp.py`:
- `fs_read/fs_write/find_project_status_file` → Filesystem MCP tools
- `git_open_mr` → GitLab MCP: create branch/commit/push/MR

Keep signatures intact so nodes don’t change.

## Notes
- Integrator asks LLM for **full file contents** per path; low temperature for determinism.
- Product Manager writes a **dated** section + **final summary** to project status.
- Planner includes project status content as RAG context to avoid re‑inventing the plan.
