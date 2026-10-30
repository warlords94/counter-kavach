from kavach.config import load_config
from kavach.schemas import AnomalyResult, TransactionContext, TxnType


def score_transaction(ctx: TransactionContext, cfg: dict | None = None) -> AnomalyResult:
    c = (cfg or load_config())["anomaly"]
    ratio = ctx.txn_amount_inr / max(ctx.avg_monthly_debit_inr, 1)
    points: list[tuple[int, str]] = []

    for threshold, pts in c["ratio_points"]:
        if ratio >= threshold:
            points.append((pts, f"Amount is {ratio:.1f}x the average monthly debit"))
            break
    if ctx.txn_amount_inr >= c["above_max_single_debit_factor"] * ctx.max_single_debit_inr_12m:
        points.append((c["above_max_single_debit_points"],
                       f"Amount is at least {c['above_max_single_debit_factor']}x the largest debit in 12 months"))
    if ctx.customer_age >= c["senior_age"]:
        points.append((c["senior_points"], f"Customer is {ctx.customer_age} (senior citizen)"))
    if ctx.beneficiary_is_new:
        points.append((c["new_beneficiary_points"], "New beneficiary"))
        if ctx.txn_type.value in c["large_transfer_types"] and ctx.txn_amount_inr >= c["large_transfer_inr"]:
            points.append((c["large_transfer_new_payee_points"],
                           f"{ctx.txn_type.value} of ₹{c['large_transfer_inr']:,} or more to a new beneficiary"))
    if ctx.txn_type == TxnType.FD_BREAK:
        points.append((c["fd_break_points"], "Premature FD break"))
    if ctx.customer_on_call_at_counter:
        points.append((c["on_call_points"], "Customer is on a phone or video call at the counter"))
    if ctx.accompanied_by_unknown_person:
        points.append((c["unknown_companion_points"], "Accompanied by an unknown person"))

    score = min(100, sum(p for p, _ in points))
    return AnomalyResult(
        score=score,
        amount_ratio=round(ratio, 2),
        reasons=[f"{reason} (+{p})" for p, reason in points],
        check_recommended=score >= c["trigger_score"] and ctx.txn_amount_inr >= c["min_check_amount_inr"],
    )
