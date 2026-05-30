import os
import json
import sys
from pathlib import Path


def _candidate_config_paths() -> list[Path]:
    paths: list[Path] = []

    if getattr(sys, "frozen", False):
        paths.append(Path(sys.executable).resolve().parent / "config.local.json")

    project_dir = Path(__file__).resolve().parent
    paths.append(project_dir / "config.local.json")
    paths.append(Path.cwd() / "config.local.json")

    unique_paths: list[Path] = []
    seen = set()
    for path in paths:
        resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_paths.append(path)
    return unique_paths


def _load_file_config() -> dict:
    for path in _candidate_config_paths():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                return data
        except Exception as exc:
            print(f"Config locale ignorée ({path}) : {exc}")
    return {}


_FILE_CONFIG = _load_file_config()


def _get_setting(key: str, default: str = "") -> str:
    if key in os.environ and str(os.environ[key]).strip():
        return str(os.environ[key]).strip()
    value = _FILE_CONFIG.get(key, default)
    return str(value).strip() if value is not None else str(default).strip()


def _get_int_setting(key: str, default: int) -> int:
    raw_value = _get_setting(key, str(default))
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return default


DATABASE_URL = _get_setting("DATABASE_URL")

DB_HOST = _get_setting("DB_HOST", "localhost")
DB_NAME = _get_setting("DB_NAME", "school_management")
DB_USER = _get_setting("DB_USER", "beni")
DB_PASSWORD = _get_setting("DB_PASSWORD", "orbitb4")
DB_PORT = _get_setting("DB_PORT", "5432")
DB_SSLMODE = _get_setting("DB_SSLMODE")
DB_CONNECT_TIMEOUT = _get_int_setting("DB_CONNECT_TIMEOUT", 10)
DB_POOL_MINCONN = _get_int_setting("DB_POOL_MINCONN", 1)
DB_POOL_MAXCONN = _get_int_setting("DB_POOL_MAXCONN", 6)
