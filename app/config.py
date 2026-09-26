import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fitbuddy.db")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_WORKOUT_MODEL = os.getenv("GEMINI_WORKOUT_MODEL", "gemini-flash-lite-latest")
GEMINI_TIP_MODEL = os.getenv("GEMINI_TIP_MODEL", "gemini-flash-lite-latest")
STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATES_DIR = BASE_DIR / "templates"