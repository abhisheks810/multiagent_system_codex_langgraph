# app/agent_chat.py
import argparse
import os
from typing import List, Dict
from openai import OpenAI

from app.settings import OPENAI_MODEL
from app.prompts import (
    PLANNER_SYSTEM,
    TESTER_SYSTEM,
    UIUX_SYSTEM,
    QAGEO_SYSTEM,
)
from app.nodes.tools_mcp import read_project_status, fs_read
from app.utils.logging import log_event

ROLE_TO_SYSTEM = {
    "planner": PLANNER_SYSTEM,       # RAG: reads Project Status
    "tester": TESTER_SYSTEM,
    "uiux": UIUX_SYSTEM,
    "qa_geo": QAGEO_SYSTEM,
}

def _build_messages(role: str, message: str, feature: str, files: List[str]) -> List[Dict[str, str]]:
    system_prompt = ROLE_TO_SYSTEM[role]

    # Optional grounding for Planner using the RAG file:
    rag = ""
    if role == "planner":
        try:
            rag = read_project_status()
        except Exception:
            rag = ""

    files_blob = ""
    if files:
        parts = []
        for p in files:
            try:
                content = fs_read(p)
            except Exception:
                content = ""
            parts.append(f"--- FILE: {p} ---\n```\n{content}\n```")
        files_blob = "\n\n".join(parts)

    # Compose the user message for the agent
    user = []
    if rag:
        user.append(f"PROJECT STATUS (context):\n\n{rag}")
    if feature:
        user.append(f"FEATURE (context):\n{feature}")
    if files_blob:
        user.append(f"CODE CONTEXT:\n{files_blob}")
    if message:
        user.append(f"ISSUE / QUESTION:\n{message}")

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n".join(user) or "No message provided."},
    ]

def main():
    parser = argparse.ArgumentParser(description="Chat with a specific agent (planner|tester|uiux|qa_geo)")
    parser.add_argument("--role", required=True, choices=["planner", "tester", "uiux", "qa_geo"], help="Agent role to talk to")
    parser.add_argument("--message", "-m", default="", help="Issue/question to the agent")
    parser.add_argument("--feature", "-f", default="", help="(Optional) feature description context")
    parser.add_argument("--file", "-F", action="append", default=[], help="(Optional) repo-relative file(s) to include as context; repeatable")

    args = parser.parse_args()

    client = OpenAI()

    messages = _build_messages(args.role, args.message, args.feature, args.file)

    # Do NOT pass temperature; some models require default only.
    print(f"[agent_chat] {args.role} using MODEL={OPENAI_MODEL}")
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages
    )
    out = resp.choices[0].message.content
    print(f"\n[{args.role.upper()} RESPONSE]\n")
    print(out)
    feature_for_log = (args.feature or args.message or "").strip() or "(no feature provided)"
    log_event(query=feature_for_log, response=out, source=f"agent_chat:{args.role}")
    print()

if __name__ == "__main__":
    if os.getenv("OPENAI_API_KEY") is None:
        print("WARNING: OPENAI_API_KEY is not set.")
    main()
