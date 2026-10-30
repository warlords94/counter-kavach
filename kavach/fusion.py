import re

from kavach.config import load_config
from kavach.rules.engine import rules_by_id
from kavach.schemas import (AnalyzerResult, AnomalyResult, EvidenceItem, RiskAssessment, RulesResult,
                            TransactionContext)

# Rule hits that point to a scam type when the LLM is unavailable or undecided (first match wins).
RULE_SCAM_TYPES = [
    ({"DIGITAL_ARREST", "AUTHORITY_IMPERSONATION", "PARCEL_OR_DRUGS", "LAUNDERING_ACCUSATION",
      "TRANSFER_FOR_VERIFICATION", "ARREST_THREAT"}, "digital_arrest"),
    ({"INVESTMENT_LURE"}, "investment"),
    ({"KYC_OR_ACCOUNT_BLOCK"}, "kyc_or_account_block"),
    ({"RELATIVE_IN_TROUBLE"}, "relative_in_trouble"),
]
_POINTS = re.compile(r"\s*\(\+(\d+)\)$")


def rules_hold(cond: dict, full: set[str]) -> bool:
    any_of = cond.get("rules_any")
    return all(r in full for r in cond.get("rules_all", [])) and (not any_of or any(r in full for r in any_of))


def _floor_holds(floor: dict, full: set[str], ctx: TransactionContext, anomaly: AnomalyResult) -> bool:
    if "rules_all" in floor or "rules_any" in floor:
        return rules_hold(floor, full)
    when = floor.get("when", {})
    checks = []
    if "live_call" in when:
        checks.append((ctx.customer_on_call_at_counter or "LIVE_CALL" in full) == when["live_call"])
    if "beneficiary_is_new" in when:
        checks.append(ctx.beneficiary_is_new == when["beneficiary_is_new"])
    if "min_amount_ratio" in when:
        checks.append(anomaly.amount_ratio >= when["min_amount_ratio"])
    return bool(checks) and all(checks)


def _scam_type(full: set[str], analyzer: AnalyzerResult | None) -> str:
    llm_type = analyzer.assessment.scam_type if analyzer and analyzer.available and analyzer.assessment else None
    if llm_type and llm_type not in ("none_detected", "other"):
        return llm_type
    rule_type = next((t for ids, t in RULE_SCAM_TYPES if ids & full), None)
    if rule_type:
        return rule_type
    if llm_type:
        return llm_type
    return "other" if full - {"LIVE_CALL"} else "none_detected"


def _evidence(anomaly: AnomalyResult, rules: RulesResult, analyzer: AnalyzerResult | None,
              llm_weight: float) -> list[EvidenceItem]:
    labels = {rid: r.label_en for rid, r in rules_by_id().items()}
    items = []
    for reason in anomaly.reasons:
        m = _POINTS.search(reason)
        items.append(EvidenceItem(source="Transaction", text=_POINTS.sub("", reason),
                                  weight=float(m.group(1)) if m else 0.0))
    for h in rules.hits:
        label = labels.get(h.rule_id, h.rule_id)
        if h.via == "answer":
            items.append(EvidenceItem(source="Answer", text=f"{label} ({h.matched_text})", weight=h.weight))
        elif h.via == "transaction":
            items.append(EvidenceItem(source="Transaction", text=label, weight=h.weight))
        else:
            src = "Notice" if h.source == "notice" else "Rule"
            items.append(EvidenceItem(source=src, text=f"{label}: “{h.matched_text}” ({h.source})", weight=h.weight))
    if analyzer and analyzer.available:
        for f in analyzer.kept_flags:
            items.append(EvidenceItem(source="LLM", text=f"{f.flag}: “{f.evidence}” ({f.question_id})",
                                      weight=llm_weight))
    return sorted(items, key=lambda e: -e.weight)


def fuse(anomaly: AnomalyResult, rules: RulesResult, analyzer: AnalyzerResult | None,
         ctx: TransactionContext, cfg: dict | None = None) -> RiskAssessment:
    f = (cfg or load_config())["fusion"]
    llm_ok = bool(analyzer and analyzer.available and analyzer.llm_score is not None)
    components = {"anomaly": float(anomaly.score), "rules": float(rules.score),
                  "llm": analyzer.llm_score if llm_ok else None}
    present = {k: v for k, v in components.items() if v is not None}
    total_weight = sum(f["weights"][k] for k in present)
    score = round(sum(f["weights"][k] * v for k, v in present.items()) / total_weight, 2)

    levels = f["levels"]
    level = "HIGH" if score >= levels["high"] else "MEDIUM" if score >= levels["medium"] else "LOW"
    full = rules.full_ids()
    overrides = [o["name"] for o in f["overrides_high"] if rules_hold(o, full)]
    floors = [fl["name"] for fl in f["floors_medium"] if _floor_holds(fl, full, ctx, anomaly)]
    if overrides:
        level = "HIGH"
    elif floors and level == "LOW":
        level = "MEDIUM"

    return RiskAssessment(
        level=level, score=score, scam_type=_scam_type(full, analyzer),
        evidence=_evidence(anomaly, rules, analyzer, f["llm_evidence_weight"])[: f["top_evidence"]],
        overrides_applied=overrides, floors_applied=floors, component_scores=components, llm_available=llm_ok,
    )
