import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from rapidfuzz import fuzz

from kavach.config import load_config, load_yaml
from kavach.schemas import Answer, Choice, RuleHit, RulesResult, TransactionContext
from kavach.textnorm import fold, is_negated, normalize

RULES_PATH = Path(__file__).with_name("red_flags.yaml")


@dataclass(frozen=True)
class Rule:
    id: str
    label_en: str
    label_hi: str
    weight: float
    answer_question: str | None = None
    answer_choice: str | None = None
    patterns: tuple[re.Pattern, ...] = field(default_factory=tuple)
    fuzzy_terms: tuple[str, ...] = field(default_factory=tuple)
    negatable: bool = True
    transaction_flag: str | None = None


@lru_cache(maxsize=None)
def load_rules(path: Path = RULES_PATH) -> tuple[Rule, ...]:
    rules = []
    for r in load_yaml(path)["rules"]:
        answer = r.get("answer") or {}
        rules.append(Rule(
            id=r["id"], label_en=r["label_en"], label_hi=r["label_hi"], weight=float(r["weight"]),
            answer_question=answer.get("question"), answer_choice=answer.get("choice"),
            patterns=tuple(re.compile(fold(p), re.IGNORECASE) for p in r.get("patterns", [])),
            fuzzy_terms=tuple(normalize(t) for t in r.get("fuzzy_terms", [])),
            negatable=r.get("negatable", True),
            transaction_flag=r.get("transaction_flag"),
        ))
    return tuple(rules)


def rules_by_id() -> dict[str, Rule]:
    return {r.id: r for r in load_rules()}


def text_rule_ids() -> set[str]:
    return {r.id for r in load_rules() if r.patterns or r.fuzzy_terms}


def risk_choices() -> dict[str, str]:
    """Question id -> the button choice that is a red flag."""
    return {r.answer_question: r.answer_choice for r in load_rules() if r.answer_question}


def _match(rule: Rule, text: str, rc: dict) -> str | None:
    for pattern in rule.patterns:
        for m in pattern.finditer(text):
            if rule.negatable and is_negated(text, m.start(), m.end(), rc):
                continue
            return m.group(0)
    for term in rule.fuzzy_terms:
        if len(term) < rc["fuzzy_min_term_len"] or len(text) < len(term):
            continue
        al = fuzz.partial_ratio_alignment(term, text)
        if al is None or al.score < rc["fuzzy_threshold"]:
            continue
        if rule.negatable and is_negated(text, al.dest_start, al.dest_end, rc):
            continue
        return text[al.dest_start:al.dest_end]
    return None


def evaluate(answers: dict[str, Answer], ctx: TransactionContext | None = None,
             notice_text: str = "", cfg: dict | None = None) -> RulesResult:
    rc = (cfg or load_config())["rules"]
    rules = load_rules()
    best: dict[str, RuleHit] = {}

    def add(hit: RuleHit) -> None:
        cur = best.get(hit.rule_id)
        if cur is None or (hit.full, hit.weight) > (cur.full, cur.weight):
            best[hit.rule_id] = hit

    for r in rules:
        a = answers.get(r.answer_question) if r.answer_question else None
        if a is None or a.choice is None:
            continue
        if a.choice == r.answer_choice:
            add(RuleHit(rule_id=r.id, weight=r.weight, matched_text=f"{r.answer_question}: {a.choice.value}",
                        source=r.answer_question, via="answer"))
        elif a.choice == Choice.UNSURE:
            add(RuleHit(rule_id=r.id, weight=r.weight * rc["unsure_factor"], full=False,
                        matched_text=f"{r.answer_question}: unsure", source=r.answer_question, via="answer"))

    if ctx is not None:
        for r in rules:
            if r.transaction_flag and getattr(ctx, r.transaction_flag):
                add(RuleHit(rule_id=r.id, weight=r.weight, matched_text=r.transaction_flag,
                            source="transaction", via="transaction"))

    risk = risk_choices()
    sources: list[tuple[str, str]] = []
    for qid, a in answers.items():
        if a.detail.strip() and (a.choice is None or a.choice == Choice.UNSURE or a.choice == risk.get(qid)):
            sources.append((qid, a.detail))
    if ctx is not None and ctx.staff_notes.strip():
        sources.append(("staff_notes", ctx.staff_notes))
    if notice_text.strip():
        sources.append(("notice", notice_text))

    for src, raw in sources:
        text = normalize(raw)
        for r in rules:
            matched = _match(r, text, rc)
            if matched:
                add(RuleHit(rule_id=r.id, weight=r.weight, matched_text=matched, source=src, via="text"))

    hits = sorted(best.values(), key=lambda h: (-h.weight, h.rule_id))
    return RulesResult(score=min(100.0, sum(h.weight for h in hits)), hits=hits)
