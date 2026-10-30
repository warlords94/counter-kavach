import uuid
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from kavach import actions, interview
from kavach.config import load_config, resolve
from kavach.fmt import format_inr
from kavach.pipeline import CheckResult
from kavach.privacy import mask_customer, mask_free_text
from kavach.schemas import Answer, EvidenceItem, TransactionContext

TEMPLATES = Path(__file__).with_name("templates")
SCAM_LABELS = {
    "digital_arrest": "digital arrest / impersonation", "investment": "investment fraud",
    "kyc_or_account_block": "KYC / account-block fraud", "relative_in_trouble": "relative-in-trouble fraud",
    "lottery_or_refund": "lottery / refund fraud", "other": "other coercion", "none_detected": "none detected",
}


class QAItem(BaseModel):
    qid: str
    question: str
    choice: str | None
    detail: str


class IncidentNote(BaseModel):
    id: str
    timestamp: str
    branch: str
    staff_name: str
    officer_name: str
    customer_ref: str
    customer_age: int
    txn_type: str
    amount_inr: float
    amount_display: str
    amount_ratio: float
    payee: str
    beneficiary_is_new: bool
    on_call: bool
    anomaly_score: int
    anomaly_reasons: list[str]
    qa: list[QAItem]
    evidence: list[EvidenceItem]
    level: str
    score: float
    scam_type: str
    scam_label: str
    overrides: list[str]
    floors: list[str]
    component_scores: dict[str, float | None]
    llm_available: bool
    llm_summary: str
    recommended_actions: list[str]
    action_taken: str
    suspected_fraud: bool
    staff_notes: str
    models: dict[str, str]
    timings: dict[str, float]
    energy_joules: float | None
    energy_kind: str | None


def build_note(res: CheckResult, ctx: TransactionContext, answers: dict[str, Answer], staff_name: str,
               officer_name: str, action_taken: str, suspected_fraud: bool, customer_ref: str = "SYNTHETIC",
               models: dict[str, str] | None = None, cfg: dict | None = None) -> IncidentNote:
    cfg = cfg or load_config()
    mask = lambda s: mask_free_text(s, suspected_fraud)  # noqa: E731
    payee = ctx.payee_reference
    if not suspected_fraud and payee:
        payee = "XXXX" + payee[-4:]
    qa = [QAItem(qid=qid, question=interview.text(qid, "en"), choice=a.choice.value if a.choice else None,
                 detail=mask(a.detail)) for qid, a in sorted(answers.items(), key=lambda kv: int(kv[0][1:]))]
    risk = res.risk
    summary = res.analyzer.assessment.staff_summary if res.analyzer.available and res.analyzer.assessment else ""
    return IncidentNote(
        id=f"CK-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}",
        timestamp=datetime.now().isoformat(timespec="seconds"),
        branch=cfg["branch"], staff_name=staff_name, officer_name=officer_name,
        customer_ref=mask_customer(customer_ref), customer_age=ctx.customer_age,
        txn_type=ctx.txn_type.value, amount_inr=ctx.txn_amount_inr, amount_display=format_inr(ctx.txn_amount_inr),
        amount_ratio=res.anomaly.amount_ratio, payee=payee or "-", beneficiary_is_new=ctx.beneficiary_is_new,
        on_call=ctx.customer_on_call_at_counter, anomaly_score=res.anomaly.score, anomaly_reasons=res.anomaly.reasons,
        qa=qa, evidence=[e.model_copy(update={"text": mask(e.text)}) for e in risk.evidence],
        level=risk.level, score=risk.score, scam_type=risk.scam_type, scam_label=SCAM_LABELS[risk.scam_type],
        overrides=risk.overrides_applied, floors=risk.floors_applied, component_scores=risk.component_scores,
        llm_available=risk.llm_available, llm_summary=mask(summary),
        recommended_actions=actions.recommended(risk.level, "en"), action_taken=action_taken,
        suspected_fraud=suspected_fraud, staff_notes=mask(ctx.staff_notes),
        models=models or {"llm": res.model_name or "not used"},
        timings={k: round(v, 3) for k, v in res.timings.items()},
        energy_joules=round(res.energy_joules, 1) if res.energy_joules is not None else None,
        energy_kind=res.energy_kind,
    )


def _env(autoescape: bool) -> Environment:
    # select_autoescape matches the full suffix, so "report.html.j2" needs "html.j2".
    return Environment(loader=FileSystemLoader(TEMPLATES), trim_blocks=True, lstrip_blocks=True,
                       autoescape=select_autoescape(["html.j2"]) if autoescape else False)


def render_markdown(note: IncidentNote) -> str:
    return _env(False).get_template("report.md.j2").render(n=note)


def render_html(note: IncidentNote) -> str:
    return _env(True).get_template("report.html.j2").render(n=note)


def complaint_summary(note: IncidentNote) -> str:
    """Five plain-text lines staff can paste into a cybercrime complaint."""
    when = datetime.fromisoformat(note.timestamp).strftime("%d %b %Y, %H:%M")
    evidence = "; ".join(e.text for e in note.evidence[:3]) or "none recorded"
    lines = [
        f"Suspected {note.scam_label} attempt stopped at {note.branch} on {when}.",
        f"Customer (ref {note.customer_ref}, age {note.customer_age}) attempted a {note.txn_type} of "
        f"{note.amount_display} to payee {note.payee}.",
        f"Key evidence: {evidence}",
        f"Risk {note.level} (score {note.score:.0f}); action taken: {note.action_taken}.",
        f"Recorded by {note.staff_name}; decision by {note.officer_name}. Counter Kavach prototype, offline.",
    ]
    return "\n".join(" ".join(line.split()) for line in lines)


def save(note: IncidentNote, directory: Path | str | None = None) -> dict[str, Path]:
    out = resolve(directory or "var/reports")
    out.mkdir(parents=True, exist_ok=True)
    paths = {"md": out / f"{note.id}.md", "html": out / f"{note.id}.html"}
    paths["md"].write_text(render_markdown(note), encoding="utf-8")
    paths["html"].write_text(render_html(note), encoding="utf-8")
    return paths
