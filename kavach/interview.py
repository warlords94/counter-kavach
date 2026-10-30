from functools import lru_cache
from typing import Literal

from pydantic import BaseModel

from kavach.config import load_config, load_yaml
from kavach.fusion import rules_hold
from kavach.rules.engine import evaluate
from kavach.schemas import Answer, TransactionContext


class Probe(BaseModel):
    en: str
    hi: str


class Question(BaseModel):
    id: str
    topic: str
    type: Literal["open", "yes_no"]
    en: str
    hi: str
    risk_answer: str | None = None
    probes: Probe | None = None
    branch_to: str | None = None


@lru_cache(maxsize=None)
def _bank() -> dict:
    return load_yaml("data/question_bank.yaml")


def questions() -> list[Question]:
    return [Question(**q) for q in _bank()["questions"]]


def get(qid: str) -> Question:
    return next(q for q in questions() if q.id == qid)


def text(qid: str, lang: str) -> str:
    return getattr(get(qid), lang)


def staff_tips(lang: str) -> list[str]:
    return _bank()["staff_tips"][lang]


def probe(qid: str, choice: str | None, lang: str) -> str | None:
    q = get(qid)
    if q.probes and q.risk_answer and choice == q.risk_answer:
        return getattr(q.probes, lang)
    return None


def next_id(qid: str) -> str | None:
    ids = [q.id for q in questions()]
    i = ids.index(qid)
    return ids[i + 1] if i + 1 < len(ids) else None


def escalation_ready(answers: dict[str, Answer], ctx: TransactionContext | None = None,
                     cfg: dict | None = None) -> list[str]:
    """HIGH overrides that already fire from the answers so far ("Enough to escalate")."""
    cfg = cfg or load_config()
    full = evaluate(answers, ctx, cfg=cfg).full_ids()
    return [o["name"] for o in cfg["fusion"]["overrides_high"] if rules_hold(o, full)]
