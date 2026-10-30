import pytest

from kavach.anomaly import score_transaction
from kavach.fusion import fuse
from kavach.rules.engine import evaluate
from kavach.schemas import AnalyzerResult, Answer, LLMAssessment, RedFlag
from tests.conftest import answers, make_ctx

DA_TXN = dict(customer_age=72, avg_monthly_debit_inr=40000, max_single_debit_inr_12m=150000,
              txn_amount_inr=1800000, txn_type="RTGS", beneficiary_is_new=True,
              customer_on_call_at_counter=True)
ALL_NO = {f"Q{i}": "no" for i in range(2, 10)} | {"Q3": "yes", "Q10": "yes"}


def llm(likelihood: str | None, score: float | None = None, flags=(), scam_type="digital_arrest"):
    if likelihood is None:
        return AnalyzerResult(available=False, error="LLM unavailable")
    kept = [RedFlag(flag=f, evidence=e, question_id=q) for f, e, q in flags]
    a = LLMAssessment(coercion_likelihood=likelihood, scam_type=scam_type, red_flags=kept)
    return AnalyzerResult(available=True, assessment=a, llm_score=score, kept_flags=kept)


def run(ctx, qa, analyzer):
    return fuse(score_transaction(ctx), evaluate(qa, ctx), analyzer, ctx)


def case_a(scenario):
    s = scenario("da_01")
    return make_ctx(**s["transaction"]), {k: Answer(**v) for k, v in s["answers"].items()}


def case_b():
    return make_ctx(**DA_TXN), answers(Q1="buying a flat, paying the builder", **ALL_NO)


def test_case_a_candid_digital_arrest_is_high(scenario):
    ctx, qa = case_a(scenario)
    r = run(ctx, qa, llm("high", 85, [("threat", "गिरफ्तार कर लेंगे", "Q8")]))
    assert r.level == "HIGH" and r.score == pytest.approx(94)
    assert "authority_plus_coercion" in r.overrides_applied


def test_case_b_coached_victim_floored_to_medium():
    ctx, qa = case_b()
    r = run(ctx, qa, llm("low", 10, scam_type="none_detected"))
    assert r.score == pytest.approx(34.25)
    assert r.level == "MEDIUM" and r.floors_applied == ["live_call_large_new_payee"]


def test_case_c_genuine_wedding_is_low():
    ctx = make_ctx(customer_age=62, avg_monthly_debit_inr=60000, max_single_debit_inr_12m=200000,
                   txn_amount_inr=1200000, txn_type="RTGS", beneficiary_is_new=True)
    qa = answers(Q1="बेटी की शादी के लिए वेन्यू का भुगतान", **ALL_NO)
    r = run(ctx, qa, llm("low", 10, scam_type="none_detected"))
    assert r.level == "LOW" and r.score == pytest.approx(24)
    assert r.overrides_applied == [] and r.floors_applied == []


def test_case_d_passport_hard_negative_is_low():
    ctx = make_ctx(beneficiary_is_new=True)
    qa = answers(Q1="passport fees", Q4=("yes", "police came for my passport verification"))
    r = run(ctx, qa, llm("low", 10, scam_type="none_detected"))
    assert r.level == "LOW" and r.score == pytest.approx(16.5)
    assert r.overrides_applied == []


def test_case_a_without_llm_reweights_and_stays_high(scenario):
    ctx, qa = case_a(scenario)
    r = run(ctx, qa, llm(None))
    assert r.level == "HIGH" and r.score == pytest.approx(100) and not r.llm_available
    assert r.component_scores["llm"] is None


def test_case_b_without_llm_reweights_to_medium():
    ctx, qa = case_b()
    r = run(ctx, qa, llm(None))
    assert r.level == "MEDIUM" and r.score == pytest.approx(50.42, abs=0.01)


def test_live_call_authority_instructed_override():
    ctx = make_ctx(customer_on_call_at_counter=True)
    r = run(ctx, answers(Q2="yes", Q4="yes"), llm("low", 10))
    assert r.level == "HIGH" and r.overrides_applied == ["live_call_authority_instructed"]


def test_unsure_answers_never_fire_overrides_or_floors():
    r = run(make_ctx(), answers(Q4="unsure", Q8="yes", Q5="unsure"), llm("low", 10))
    assert r.overrides_applied == [] and r.floors_applied == []


def test_secrecy_floor_lifts_low_to_medium():
    r = run(make_ctx(), answers(Q5="yes"), llm("low", 10))
    assert r.level == "MEDIUM" and r.floors_applied == ["secrecy_instruction"]


def test_evidence_has_source_tags_and_is_capped_at_top_five(scenario):
    ctx, qa = case_a(scenario)
    r = run(ctx, qa, llm("high", 85, [("threat", "गिरफ्तार कर लेंगे", "Q8")]))
    assert len(r.evidence) == 5
    assert {e.source for e in r.evidence} <= {"Transaction", "Answer", "Rule", "LLM", "Notice"}
    weights = [e.weight for e in r.evidence]
    assert weights == sorted(weights, reverse=True)


def test_scam_type_falls_back_to_rules_when_llm_unavailable(scenario):
    ctx, qa = case_a(scenario)
    assert run(ctx, qa, llm(None)).scam_type == "digital_arrest"
    assert run(make_ctx(), answers(Q1="guaranteed returns on the trading app"), llm(None)).scam_type == "investment"
    assert run(make_ctx(), answers(Q1="wedding"), llm(None)).scam_type == "none_detected"
