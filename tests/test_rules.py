import pytest

from kavach.rules.engine import evaluate, text_rule_ids
from kavach.schemas import Answer
from tests.conftest import answers, make_ctx


def q1_hits(text: str) -> set[str]:
    return {h.rule_id for h in evaluate(answers(Q1=text)).hits}


POSITIVES = {
    "AUTHORITY_IMPERSONATION": [
        "A CBI officer called me yesterday",
        "he said he was from the police",
        "police wale ne bola paise bhejo",
        "सीबीआई के अधिकारी ने कहा",
        "सीबीआई वालों ने कहा",
    ],
    "DIGITAL_ARREST": [
        "they said I am under digital arrest",
        "video call par raho, camera on rakho",
        "डिजिटल अरेस्ट है, कैमरा चालू रखने को कहा",
    ],
    "SECRECY_INSTRUCTION": [
        "They said don't tell anyone, not even the bank staff",
        "kisi ko mat batana",
        "किसी को मत बताना",
    ],
    "TRANSFER_FOR_VERIFICATION": [
        "transfer the money to the safe account for verification",
        "paisa wapas aa jayega",
        "आरबीआई के सुरक्षित खाते में डालना है",
    ],
    "PARCEL_OR_DRUGS": [
        "a courier said my parcel had drugs in it",
        "पार्सल में ड्रग्स मिले हैं",
    ],
    "LAUNDERING_ACCUSATION": [
        "they said my Aadhaar was used in money laundering",
        "मेरे आधार से मनी लॉन्ड्रिंग हुई है",
    ],
    "ARREST_THREAT": [
        "you will be arrested today",
        "पैसे नहीं भेजे तो गिरफ्तार कर लेंगे",
    ],
    "URGENCY": [
        "must send within 2 hours",
        "आज ही भेजना है",
    ],
    "INVESTMENT_LURE": [
        "guaranteed returns on the trading app",
        "WhatsApp group gives stock tips with double money",
    ],
    "KYC_OR_ACCOUNT_BLOCK": [
        "your KYC is pending, account will be blocked",
        "खाता बंद हो जाएगा, केवाईसी अपडेट करो",
    ],
    "RELATIVE_IN_TROUBLE": [
        "my grandson has been arrested in Dubai",
        "बेटा गिरफ्तार हो गया है",
    ],
}

NEGATIVES = {
    "AUTHORITY_IMPERSONATION": [
        "police verification for my passport",
        "court case over my land",
        "my lawyer called about the high court hearing",
        "No, nobody from police or CBI called me",
    ],
    "DIGITAL_ARREST": ["video call with my son in Canada"],
    "SECRECY_INSTRUCTION": ["keep it secret, it's a surprise for my daughter"],
    "TRANSFER_FOR_VERIFICATION": [
        "police verification for my passport",
        "पुलिस वेरिफिकेशन पासपोर्ट के लिए",
    ],
    "PARCEL_OR_DRUGS": ["paying the courier company invoice"],
    "LAUNDERING_ACCUSATION": ["my Aadhaar is linked to this account"],
    "ARREST_THREAT": ["They didn't say I will be arrested"],
    "URGENCY": ["for my daughter's wedding next month"],
    "INVESTMENT_LURE": ["family WhatsApp group photo"],
    "KYC_OR_ACCOUNT_BLOCK": ["closing my old account after the move"],
    "RELATIVE_IN_TROUBLE": ["school fees for my son"],
}


@pytest.mark.parametrize("rule_id,text", [(r, t) for r, ts in POSITIVES.items() for t in ts])
def test_text_rule_positive(rule_id, text):
    assert rule_id in q1_hits(text)


@pytest.mark.parametrize("rule_id,text", [(r, t) for r, ts in NEGATIVES.items() for t in ts])
def test_text_rule_hard_negative(rule_id, text):
    assert rule_id not in q1_hits(text)


def test_every_text_rule_has_positive_and_negative_tests():
    assert set(POSITIVES) == set(NEGATIVES) == text_rule_ids()


def test_answer_yes_hits_rule_at_full_weight():
    hit = evaluate(answers(Q4="yes")).hits[0]
    assert (hit.rule_id, hit.weight, hit.full, hit.via, hit.source) == (
        "AUTHORITY_IMPERSONATION", 25, True, "answer", "Q4")


def test_unsure_answer_counts_half_and_is_not_full():
    hit = evaluate(answers(Q4="unsure")).hits[0]
    assert hit.weight == 12.5 and not hit.full


def test_non_risk_answer_hits_nothing():
    assert evaluate(answers(Q4="no", Q3="yes", Q10="yes")).hits == []


def test_risk_answer_no_hits_for_payee_and_family_questions():
    ids = {h.rule_id for h in evaluate(answers(Q3="no", Q10="no")).hits}
    assert ids == {"UNKNOWN_PAYEE", "DECLINES_FAMILY_CALL"}


def test_live_call_comes_from_transaction_flag():
    r = evaluate({}, make_ctx(customer_on_call_at_counter=True))
    assert [(h.rule_id, h.via, h.weight) for h in r.hits] == [("LIVE_CALL", "transaction", 15)]


def test_each_rule_counted_once_at_highest_weight():
    r = evaluate(answers(Q4=("unsure", "a CBI officer called"), Q1="CBI officer said so"))
    auth = [h for h in r.hits if h.rule_id == "AUTHORITY_IMPERSONATION"]
    assert len(auth) == 1 and auth[0].full and auth[0].weight == 25
    assert r.score == 25


def test_detail_of_non_risk_answer_is_not_scanned():
    assert evaluate(answers(Q4=("no", "no CBI officer, a police officer from Delhi called"))).hits == []


def test_staff_notes_and_notice_text_are_scanned():
    r = evaluate({}, make_ctx(staff_notes="customer says officer from CBI on phone"),
                 notice_text="DIGITAL ARREST WARRANT")
    sources = {h.rule_id: h.source for h in r.hits}
    assert sources["AUTHORITY_IMPERSONATION"] == "staff_notes"
    assert sources["DIGITAL_ARREST"] == "notice"


def test_rule_score_capped_at_100():
    qs = {f"Q{i}": Answer(choice="yes") for i in range(2, 10)}
    assert evaluate(qs, make_ctx(customer_on_call_at_counter=True)).score == 100


def test_demo_scenario_1_hits_core_digital_arrest_rules(scenario):
    s = scenario("da_01")
    qa = {k: Answer(**v) for k, v in s["answers"].items()}
    r = evaluate(qa, make_ctx(**s["transaction"]))
    ids = {h.rule_id for h in r.hits if h.full}
    assert {"AUTHORITY_IMPERSONATION", "DIGITAL_ARREST", "TRANSFER_FOR_VERIFICATION",
            "SECRECY_INSTRUCTION", "ARREST_THREAT", "LIVE_CALL"} <= ids
    assert r.score == 100
