"""Local settings. Credentials must be supplied through the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))

host = os.getenv("MYSQL_HOST", "127.0.0.1")
port = int(os.getenv("MYSQL_PORT", "3306"))
user = os.getenv("MYSQL_USER", "ai_mentor")
password = os.getenv("MYSQL_PASSWORD", "")
database = os.getenv("MYSQL_DATABASE", "ai_mentor")
api_key = os.getenv("OPENAI_API_KEY", "")
chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
curriculum_model = os.getenv("OPENAI_CURRICULUM_MODEL", "gpt-4o")
app_host = os.getenv("APP_HOST", "127.0.0.1")
app_port = int(os.getenv("APP_PORT", "8080"))
