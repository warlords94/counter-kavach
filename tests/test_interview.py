from kavach import interview
from kavach.rules.engine import risk_choices
from tests.conftest import answers


def test_bank_has_ten_questions_q1_open_rest_yes_no():
    qs = interview.questions()
    assert [q.id for q in qs] == [f"Q{i}" for i in range(1, 11)]
    assert qs[0].type == "open" and all(q.type == "yes_no" for q in qs[1:])


def test_risk_answers_match_rules_engine():
    bank = {q.id: q.risk_answer for q in interview.questions() if q.type == "yes_no"}
    assert bank == risk_choices()


def test_every_question_has_hindi_in_devanagari():
    for q in interview.questions():
        assert any("ऀ" <= ch <= "ॿ" for ch in q.hi), q.id


def test_probe_only_on_risk_answer_and_in_language():
    assert interview.probe("Q4", "yes", "hi").startswith("कौन-सा")
    assert interview.probe("Q4", "no", "en") is None
    assert interview.probe("Q3", "no", "en") is None  # Q3 has no probe


def test_next_question():
    assert interview.next_id("Q1") == "Q2"
    assert interview.next_id("Q10") is None


def test_escalation_ready_when_override_already_fires():
    assert interview.escalation_ready(answers(Q4="yes", Q8="yes")) == ["authority_plus_coercion"]
    assert interview.escalation_ready(answers(Q4="unsure", Q8="yes")) == []
