from typing import Dict, Any
from openai import OpenAI
from app.settings import OPENAI_MODEL
from app.prompts import TESTER_SYSTEM

client = OpenAI()

def node_tester(state: Dict[str, Any]) -> Dict[str, Any]:
    feature = state["feature"]
    plan = state.get("plan", "")
    messages = [
        {"role": "system", "content": TESTER_SYSTEM},
        {"role": "user", "content": f"Feature:\n{feature}\n\nPlan:\n{plan}"}
    ]
    resp = client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
    out = resp.choices[0].message.content
    return {"tester": out}
