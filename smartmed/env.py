"""
Minimal .env file loader.

We intentionally avoid a third-party dependency (django-environ / python-dotenv)
for this single piece of functionality, so the project has one less thing that
can fail to install in constrained environments. Values already present in
os.environ always take precedence over the .env file.
"""
import os
from pathlib import Path


def load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def env_list(key: str, default=None, sep=","):
    val = os.environ.get(key)
    if val is None:
        return default or []
    return [item.strip() for item in val.split(sep) if item.strip()]
