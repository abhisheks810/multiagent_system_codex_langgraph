from typing import Dict, Any
from openai import OpenAI
from app.settings import OPENAI_MODEL
from app.prompts import PLANNER_SYSTEM
from app.nodes.tools_mcp import read_project_status

client = OpenAI()

def node_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    feature = state["feature"]
    project_status = read_project_status()
    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": f"PROJECT STATUS (context):\n\n{project_status}\n\nFEATURE:\n{feature}"}
    ]
    resp = client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
    out = resp.choices[0].message.content
    return {"plan": out}
