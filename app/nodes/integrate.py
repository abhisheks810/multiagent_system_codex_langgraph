import re
from typing import Dict, Any, List
from openai import OpenAI
from app.settings import OPENAI_MODEL
from app.prompts import INTEGRATOR_SYSTEM
from app.nodes.tools_mcp import fs_read, fs_write

INTEGRATOR_MODEL = "gpt-5"
client = OpenAI()

def _extract_paths(text: str) -> List[str]:
    cleaned = re.sub(r'[`*\[\]\(\)]', '', text)
    pattern = r'([\w\-/]+\.(?:py|js|jsx|ts|tsx|md|json|yml|yaml))'
    return sorted(set(m.group(1).lstrip("./") for m in re.finditer(pattern, cleaned, flags=re.IGNORECASE)))

def _compile_contributions(state: Dict[str, Any]) -> Dict[str, str]:
    by_role = {
        "Planner": state.get("plan", ""),
        "UIUX": state.get("uiux", ""),
        "Tester": state.get("tester", ""),
        "QAGeo": state.get("qa_geo", "")
    }
    paths = set()
    for txt in by_role.values():
        paths.update(_extract_paths(txt))
    return {p: "\n\n".join([f"From {r}:\n{by_role[r]}" for r in by_role]) for p in paths}

def node_integrate(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.get("integration_report"):
        return {}
    feature = state["feature"]
    contrib_by_file = _compile_contributions(state)
    report_parts = []

    for path, contributions in contrib_by_file.items():
        original = fs_read(path)
        user_prompt = (
            f"{INTEGRATOR_SYSTEM}\n\n"
            f"Feature: {feature}\nTarget file: {path}\n\n"
            f"--- Original ({path}) ---\n```\n{original}\n```\n\n"
            f"--- Team contributions ---\n{contributions}\n\n"
            f"Output the COMPLETE updated file content ONLY."
        )
        print(f"[integrator] using model: {INTEGRATOR_MODEL}")
        resp = client.chat.completions.create(
            model=INTEGRATOR_MODEL,
            messages=[{"role": "user", "content": user_prompt}]
        )
        updated = resp.choices[0].message.content.strip()
        updated = re.sub(r'^```[a-zA-Z0-9]*\s*', '', updated)
        updated = re.sub(r'```$', '', updated).strip()
        fs_write(path, updated)
        ext = path.split(".")[-1]
        report_parts.append(f"**Updated File: {path}**\n```{ext}\n{updated}\n```\n")

    if not report_parts:
        report_parts.append("_No file paths detected in contributions. Ensure agents mention exact file paths._")

    return {"integration_report": "\n".join(report_parts)}
