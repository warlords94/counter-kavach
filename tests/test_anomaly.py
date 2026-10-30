from kavach.anomaly import score_transaction
from tests.conftest import make_ctx


def test_classic_digital_arrest_transaction_scores_100():
    ctx = make_ctx(customer_age=72, avg_monthly_debit_inr=40000, max_single_debit_inr_12m=150000,
                   txn_amount_inr=1800000, txn_type="RTGS", beneficiary_is_new=True,
                   customer_on_call_at_counter=True)
    r = score_transaction(ctx)
    assert r.score == 100
    assert r.amount_ratio == 45
    assert r.check_recommended


def test_genuine_wedding_transaction_scores_80():
    ctx = make_ctx(customer_age=62, avg_monthly_debit_inr=60000, max_single_debit_inr_12m=200000,
                   txn_amount_inr=1200000, txn_type="RTGS", beneficiary_is_new=True)
    assert score_transaction(ctx).score == 80


def test_small_payment_by_senior_to_new_payee_does_not_recommend_check():
    ctx = make_ctx(customer_age=61, avg_monthly_debit_inr=30000, txn_amount_inr=2000,
                   beneficiary_is_new=True)
    r = score_transaction(ctx)
    assert r.score == 30
    assert not r.check_recommended


def test_ratio_bands():
    assert score_transaction(make_ctx(txn_amount_inr=150000)).score == 10   # 3x
    assert score_transaction(make_ctx(txn_amount_inr=250000)).score == 30   # 5x (+10 above 2x max single)


def test_fd_break_and_unknown_companion_add_points():
    r = score_transaction(make_ctx(txn_type="FD_BREAK", accompanied_by_unknown_person=True))
    assert r.score == 20
    assert len(r.reasons) == 2


def test_zero_average_debit_uses_one_rupee_floor():
    r = score_transaction(make_ctx(avg_monthly_debit_inr=0, txn_amount_inr=60000))
    assert r.amount_ratio == 60000


def test_score_is_capped_at_100():
    ctx = make_ctx(customer_age=80, avg_monthly_debit_inr=1000, max_single_debit_inr_12m=1000,
                   txn_amount_inr=900000, txn_type="RTGS", beneficiary_is_new=True,
                   customer_on_call_at_counter=True, accompanied_by_unknown_person=True)
    assert score_transaction(ctx).score == 100
