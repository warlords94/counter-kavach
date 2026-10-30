import json

import pytest

from kavach.config import ROOT
from kavach.schemas import Answer, TransactionContext


def make_ctx(**overrides) -> TransactionContext:
    base = dict(
        customer_age=45, avg_monthly_debit_inr=50000, max_single_debit_inr_12m=100000,
        txn_amount_inr=60000, txn_type="NEFT", beneficiary_is_new=False,
        customer_on_call_at_counter=False, accompanied_by_unknown_person=False,
    )
    base.update(overrides)
    return TransactionContext(**base)


def answers(**qs) -> dict[str, Answer]:
    """answers(Q1="detail", Q4=("yes", "detail"), Q5="no")"""
    out = {}
    for qid, val in qs.items():
        if isinstance(val, tuple):
            out[qid] = Answer(choice=val[0], detail=val[1])
        elif qid == "Q1":
            out[qid] = Answer(detail=val)
        else:
            out[qid] = Answer(choice=val)
    return out


@pytest.fixture
def scenario():
    def load(name: str) -> dict:
        return json.loads((ROOT / "data" / "scenarios" / f"{name}.json").read_text(encoding="utf-8"))
    return load
