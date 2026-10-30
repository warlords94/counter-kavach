from functools import lru_cache
from pathlib import Path

from kavach.config import load_yaml

ACTIONS_PATH = Path(__file__).with_name("actions.yaml")


@lru_cache(maxsize=None)
def _data() -> dict:
    return load_yaml(ACTIONS_PATH)


def recommended(level: str, lang: str) -> list[str]:
    return [item[lang] for item in _data()["levels"][level]]


def customer_message(scam_type: str, level: str, lang: str) -> str:
    msgs = _data()["customer_messages"]
    if level == "LOW":
        return msgs["LOW"][lang]
    return (msgs.get(scam_type) or msgs["default"])[lang]


def action_options() -> list[str]:
    return list(_data()["action_options"])
