"""
config.py - reads settings from the backend/.env file.

The Groq API key lives ONLY here, on the backend. It is never sent to the browser.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent

# Load backend/.env (if it exists) into environment variables.
load_dotenv(BACKEND_DIR / ".env")


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

# "groq" = real model. "mock" = offline fake model (no key or internet needed).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()

# true = hide personal data (emails, phones, cards...) from the model.
# See app/masking.py.
MASK_PII = _as_bool(os.getenv("MASK_PII", "true"))

DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "shop.db"
FRONTEND_DIR = PROJECT_DIR / "frontend"


def api_key_is_set() -> bool:
    """True if a real-looking key is configured (not the placeholder)."""
    return bool(GROQ_API_KEY) and not GROQ_API_KEY.startswith("your_")
