from typing import Dict, Any
from app.nodes.tools_mcp import git_open_mr

def node_open_mr(state: Dict[str, Any]) -> Dict[str, Any]:
    title = f"feat(agent): {state['feature'][:72]}"
    body = state.get("integration_report", "")
    mr_path = git_open_mr("agent/feature", "main", title, body)
    return {"mr": mr_path}
