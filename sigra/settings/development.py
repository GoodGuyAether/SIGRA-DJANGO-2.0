"""Settings used by local development commands."""
from pathlib import Path

import environ

# Development is the only settings module that reads a local .env file.  It
# must happen before importing base so every shared setting has one source.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(BASE_DIR / ".env")

from .base import *  # noqa: E402,F403

DEBUG = True
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),  # noqa: F405
}
