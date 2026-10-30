from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_yaml(path: Path | str) -> Any:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return yaml.safe_load(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_config() -> dict:
    """Project config; callers must not mutate it (deepcopy first)."""
    return load_yaml(ROOT / "config.yaml")


def resolve(rel: str | Path) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p
