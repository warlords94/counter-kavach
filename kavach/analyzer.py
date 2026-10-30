from pathlib import Path

from rapidfuzz import fuzz

from kavach.config import load_config, load_yaml
from kavach.fmt import format_inr
from kavach.llm.backend import LLMBackend
from kavach.schemas import AnalyzerResult, Answer, Choice, LLMAssessment, RedFlag, TransactionContext
from kavach.textnorm import normalize

PROMPT_PATH = Path(__file__).with_name("llm") / "prompts" / "analyzer.md"
QUESTION_IDS = [f"Q{i}" for i in range(1, 11)]
_CHOICE_LABEL = {Choice.YES: "[Yes]", Choice.NO: "[No]", Choice.UNSURE: "[Unsure]", Choice.SKIP: "[Skipped]"}
_QUOTE_STRIP = " \"'“”‘’.,!?;:।"

# Evidence before verdict: grammar-constrained decoding emits properties in this order.
ANALYZER_SCHEMA = {
    "type": "object",
    "properties": {
        "red_flags": {
            "type": "array", "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "flag": {"type": "string", "maxLength": 30},
                    "evidence": {"type": "string", "maxLength": 60},
                    "question_id": {"type": "string", "enum": QUESTION_IDS + ["notice"]},
                },
                "required": ["flag", "evidence", "question_id"],
            },
        },
        "inconsistencies": {"type": "array", "maxItems": 2, "items": {"type": "string", "maxLength": 100}},
        "scam_type": {"type": "string", "enum": [
            "digital_arrest", "investment", "kyc_or_account_block", "relative_in_trouble",
            "lottery_or_refund", "other", "none_detected"]},
        "coercion_likelihood": {"type": "string", "enum": ["low", "medium", "high"]},
        "staff_summary": {"type": "string", "maxLength": 160},
    },
    "required": ["red_flags", "inconsistencies", "scam_type", "coercion_likelihood", "staff_summary"],
}


def _qkey(qid: str) -> tuple[int, str]:
    return (int(qid[1:]), qid) if qid[1:].isdigit() else (999, qid)


def question_texts() -> dict[str, str]:
    return {q["id"]: q["en"] for q in load_yaml("data/question_bank.yaml")["questions"]}


def system_prompt() -> str:
    """Static across checks, so llama.cpp reuses its KV cache; the question list lives here, not per check."""
    qs = "\n".join(f"{qid}. {text}" for qid, text in question_texts().items())
    return PROMPT_PATH.read_text(encoding="utf-8").strip() + "\n\nScreening questions:\n" + qs


def build_messages(ctx: TransactionContext, answers: dict[str, Answer], notice_text: str = "") -> list[dict]:
    system = system_prompt()
    ratio = ctx.txn_amount_inr / max(ctx.avg_monthly_debit_inr, 1)
    yn = lambda b: "yes" if b else "no"  # noqa: E731
    lines = [
        f"Transaction: {ctx.txn_type.value} of {format_inr(ctx.txn_amount_inr)}; {ratio:.1f}x the customer's "
        f"average monthly debit; new beneficiary: {yn(ctx.beneficiary_is_new)}; customer age {ctx.customer_age}; "
        f"on a phone or video call at the counter: {yn(ctx.customer_on_call_at_counter)}; "
        f"accompanied by an unknown person: {yn(ctx.accompanied_by_unknown_person)}.",
    ]
    if ctx.staff_notes.strip():
        lines.append(f"Staff notes: {ctx.staff_notes.strip()}")
    lines += ["", "Answers ([Yes]/[No]/[Unsure] are the customer's button answers):"]
    for qid in sorted(answers, key=_qkey):
        a = answers[qid]
        label = f" {_CHOICE_LABEL[a.choice]}" if a.choice else ""
        lines.append(f"{qid}{label}: {a.detail.strip() or '-'}")
    if notice_text.strip():
        lines += ["", f"Notice text (id: notice): {notice_text.strip()}"]
    return [{"role": "system", "content": system}, {"role": "user", "content": "\n".join(lines)}]


def evidence_guard(flags: list[RedFlag], answers: dict[str, Answer], notice_text: str = "",
                   threshold: float | None = None) -> tuple[list[RedFlag], int]:
    """Keep only red flags whose quote really appears in an answer (or the notice)."""
    if threshold is None:
        threshold = load_config()["llm_scoring"]["evidence_match_threshold"]
    texts = {qid: normalize(a.detail) for qid, a in answers.items() if a.detail.strip()}
    if notice_text.strip():
        texts["notice"] = normalize(notice_text)

    def found(ev: str, text: str) -> bool:
        return ev in text or (len(ev) <= len(text) and fuzz.partial_ratio(ev, text) >= threshold)

    kept = []
    for f in flags:
        ev = normalize(f.evidence).strip(_QUOTE_STRIP)
        if not ev:
            continue
        order = ([f.question_id] if f.question_id in texts else []) + [q for q in texts if q != f.question_id]
        where = next((q for q in order if found(ev, texts[q])), None)
        if where:
            kept.append(f.model_copy(update={"question_id": where}))
    return kept, len(flags) - len(kept)


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    return t.strip()


def analyze(backend: LLMBackend | None, ctx: TransactionContext, answers: dict[str, Answer],
            notice_text: str = "", cfg: dict | None = None) -> AnalyzerResult:
    cfg = cfg or load_config()
    if backend is None:
        return AnalyzerResult(available=False, error="No LLM backend loaded")
    messages = build_messages(ctx, answers, notice_text)
    # Grammar-constrained sampling costs ~0.08 s/token on CPU, so try unconstrained first and use the
    # schema grammar (guaranteed-valid JSON) only for the one retry; then fall back to rules + anomaly.
    schemas = [None if cfg["llm"].get("unconstrained_first_attempt", True) else ANALYZER_SCHEMA, ANALYZER_SCHEMA]
    error, gen, parsed, attempts = None, None, None, 0
    for schema in schemas:
        attempts += 1
        try:
            gen = backend.generate(messages, json_schema=schema, max_tokens=cfg["llm"]["max_tokens"],
                                   temperature=cfg["llm"]["temperature"])
            parsed = LLMAssessment.model_validate_json(_strip_fences(gen.text))
            break
        except Exception as e:  # invalid JSON, schema mismatch, or backend failure
            error = f"{type(e).__name__}: {e}"
    stats = gen.stats if gen else AnalyzerResult.model_fields["stats"].default_factory()
    if parsed is None:
        return AnalyzerResult(available=False, attempts=attempts, error=error, stats=stats)

    sc = cfg["llm_scoring"]
    kept, dropped = evidence_guard(parsed.red_flags, answers, notice_text, sc["evidence_match_threshold"])
    score = float(sc["likelihood_scores"][parsed.coercion_likelihood])
    if not kept:
        score = min(score, float(sc["no_evidence_cap"]))
    return AnalyzerResult(available=True, assessment=parsed, llm_score=score, kept_flags=kept,
                          dropped_flags=dropped, stats=stats, attempts=attempts)
