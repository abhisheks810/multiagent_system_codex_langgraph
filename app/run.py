import sys, os
from app.graph import build_graph
from app.utils.logging import log_event

def _read_feature_from_stdin() -> str:
    print("Enter feature description (end with blank line):")
    lines = []
    try:
        while True:
            line = input()
            if not line and lines:
                break
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()

def main():
    feature = sys.argv[1] if len(sys.argv) > 1 else _read_feature_from_stdin()
    if not feature:
        print("No feature description provided. Exiting.")
        return

    graph = build_graph()
    final = graph.invoke({"feature": feature})
    parts = []
    if final.get("integration_report"):
        parts.append("## Integration Report\n" + final["integration_report"])
    if final.get("project_status_path"):
        parts.append(f"\n\n**Project Status updated:** `{final['project_status_path']}`")
        if final.get("project_status_preview"):
            parts.append("\n\n## Project Status Preview\n" + final["project_status_preview"])
    if final.get("mr"):
        parts.append(f"\n\n**MR/PR artifact:** {final['mr']}")

    summary_response = "\n".join(parts) or "(no output produced)"
    log_event(query=feature, response=summary_response, source="pipeline")


    print("\n=== Integration Report ===")
    print(final.get("integration_report", ""))

    print("\n=== Project Status Updated ===")
    print(final.get("project_status_path", ""))
    preview = final.get("project_status_preview", "")
    if preview:
        print("--- preview ---")
        print(preview)

    print("\n=== MR Artifact (placeholder) ===")
    print(final.get("mr", ""))

if __name__ == "__main__":
    if os.getenv("OPENAI_API_KEY") is None:
        print("WARNING: OPENAI_API_KEY is not set.")
    main()
