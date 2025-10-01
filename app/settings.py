import os

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
REPO_PATH = os.getenv("REPO_PATH", "/workspace/repo")
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")
PROJECT_STATUS_FILENAME = os.getenv("PROJECT_STATUS_FILENAME")
