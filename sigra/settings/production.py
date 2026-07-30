"""Settings used by deployed SIGRA instances."""
from .base import *  # noqa: F403

DEBUG = False
DATABASES = {
    "default": env.db("DATABASE_URL"),  # noqa: F405
}
