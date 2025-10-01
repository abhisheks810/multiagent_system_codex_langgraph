from typing import Dict, Any
from openai import OpenAI
from app.settings import OPENAI_MODEL
from app.prompts import PRODUCT_MANAGER_SYSTEM
from app.nodes.tools_mcp import read_project_status, write_project_status, now_iso_local

client = OpenAI()

def node_product_manager(state: Dict[str, Any]) -> Dict[str, Any]:
    feature = state["feature"]
    plan = state.get("plan", "")
    uiux = state.get("uiux", "")
    tester = state.get("tester", "")
    qa_geo = state.get("qa_geo", "")
    integration_report = state.get("integration_report", "")
    stamped_title = f"[{now_iso_local()}] Feature: {feature.splitlines()[0][:80]}"

    current_status = read_project_status()

    user = (
        f"CURRENT PROJECT STATUS (markdown):\n\n{current_status}\n\n"
        f"NEW INTEGRATION DETAILS:\n"
        f"- Feature: {feature}\n\n"
        f"- Plan: {plan}\n\n"
        f"- UI/UX: {uiux}\n\n"
        f"- Tester: {tester}\n\n"
        f"- QA Geo: {qa_geo}\n\n"
        f"- Integration Report: {integration_report}\n\n"
        f"Update the Project Status markdown as required. Use the title {stamped_title} for the new entry.\n"
    )

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": PRODUCT_MANAGER_SYSTEM},
            {"role": "user", "content": user},
        ]
    )
    updated_md = resp.choices[0].message.content
    path = write_project_status(updated_md)
    return {"project_status_path": path, "project_status_preview": updated_md[:500]}
