import json

from kavach.analyzer import ANALYZER_SCHEMA, analyze, build_messages, evidence_guard
from kavach.config import load_config
from kavach.llm.backend import GenerationResult, LLMBackend
from kavach.schemas import Answer, GenerationStats, RedFlag
from tests.conftest import answers, make_ctx

QA = answers(
    Q1="मेरे खाते की जांच चल रही है",
    Q4=("yes", "हाँ, सीबीआई से फोन आया था"),
    Q8=("yes", "they said I will be arrested today"),
)


class FakeBackend(LLMBackend):
    name = "fake"
    model_name = "fake-model"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def generate(self, messages, json_schema=None, max_tokens=384, temperature=0.1):
        self.calls += 1
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return GenerationResult(text=out, stats=GenerationStats(prompt_tokens=100, output_tokens=50, seconds=1.0))


def assessment(likelihood="high", flags=()):
    return json.dumps({
        "red_flags": [{"flag": f, "evidence": e, "question_id": q} for f, e, q in flags],
        "inconsistencies": [], "scam_type": "digital_arrest",
        "coercion_likelihood": likelihood, "staff_summary": "Possible digital arrest.",
    }, ensure_ascii=False)


def test_prompt_states_required_facts_and_lists_answers_with_choices():
    msgs = build_messages(make_ctx(customer_age=72), QA)
    system, user = msgs[0]["content"].lower(), msgs[1]["content"]
    for phrase in ("video call", "verify", "verbatim", "genuine large payments", "json"):
        assert phrase in system
    assert "Q4" in user and "[Yes]" in user and "हाँ, सीबीआई से फोन आया था" in user
    assert "age 72" in user


def test_schema_puts_evidence_before_verdict():
    keys = list(ANALYZER_SCHEMA["properties"])
    assert keys.index("red_flags") < keys.index("coercion_likelihood")


def test_evidence_guard_keeps_verbatim_devanagari_quote():
    kept, dropped = evidence_guard([RedFlag(flag="authority", evidence="सीबीआई से फोन आया", question_id="Q4")], QA)
    assert len(kept) == 1 and dropped == 0


def test_evidence_guard_drops_invented_quote():
    flags = [RedFlag(flag="secrecy", evidence="they told me to keep it secret from my son", question_id="Q5")]
    kept, dropped = evidence_guard(flags, QA)
    assert kept == [] and dropped == 1


def test_evidence_guard_tolerates_small_differences_and_fixes_question_id():
    flags = [RedFlag(flag="threat", evidence="They said I will be arrested today!", question_id="Q2")]
    kept, _ = evidence_guard(flags, QA)
    assert kept and kept[0].question_id == "Q8"


def test_analyze_maps_likelihood_to_score():
    r = analyze(FakeBackend([assessment("medium", [("threat", "I will be arrested today", "Q8")])]),
                make_ctx(), QA)
    assert r.available and r.llm_score == 50 and r.dropped_flags == 0


def test_analyze_caps_score_when_no_evidence_survives():
    r = analyze(FakeBackend([assessment("high", [("x", "invented quote about safe account", "Q7")])]),
                make_ctx(), QA)
    assert r.llm_score == load_config()["llm_scoring"]["no_evidence_cap"]
    assert r.dropped_flags == 1


def test_analyze_retries_once_after_invalid_json():
    backend = FakeBackend(["not json", assessment("low")])
    r = analyze(backend, make_ctx(), QA)
    assert r.available and r.attempts == 2 and r.llm_score == 10


def test_analyze_unavailable_after_two_failures():
    backend = FakeBackend(["{}", RuntimeError("model crashed")])
    r = analyze(backend, make_ctx(), QA)
    assert not r.available and r.attempts == 2 and r.llm_score is None and "model crashed" in r.error


def test_analyze_unavailable_without_backend():
    r = analyze(None, make_ctx(), {"Q1": Answer(detail="wedding")})
    assert not r.available and r.attempts == 0
