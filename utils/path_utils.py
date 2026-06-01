import sys
from pathlib import Path


def get_app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_app_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return get_app_base_dir() / candidate


def ensure_app_parent(path: str | Path) -> Path:
    resolved_path = resolve_app_path(path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return resolved_path
