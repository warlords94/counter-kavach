import pytest
from streamlit.testing.v1 import AppTest

from kavach.config import ROOT


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("KAVACH_NO_LLM", "1")
    at = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception


def text_of(at) -> str:
    return " ".join(m.value for m in at.markdown) + " " + " ".join(c.value for c in at.caption)


def run_demo(at, demo_label):
    at.selectbox(key="demo_pick").select(demo_label).run()
    click(at, "Check anyway")
    for _ in range(9):
        click(at, "Next →")
    click(at, "Analyse →")


def test_intake_shows_anomaly_score_and_offline_state(app):
    app.selectbox(key="demo_pick").select("Demo 1 · digital arrest (Hindi)").run()
    assert "Transaction anomaly score: 100/100" in text_of(app)


def test_demo_1_flows_to_high_risk_card_and_report(app):
    run_demo(app, "Demo 1 · digital arrest (Hindi)")
    assert "HIGH" in text_of(app)
    app.selectbox(key="action_taken").select("Escalated to branch manager").run()
    app.text_input(key="officer_name").input("Manager (synthetic)").run()
    click(app, "Create report →")
    assert app.code and "Risk HIGH" in app.code[0].value
    assert len(app.code[0].value.splitlines()) == 5


def test_demo_3_wedding_is_low(app):
    run_demo(app, "Demo 3 · genuine wedding payment")
    assert "LOW" in text_of(app) and "HIGH" not in text_of(app)


def test_answers_survive_navigating_back(app):
    app.selectbox(key="demo_pick").select("Demo 1 · digital arrest (Hindi)").run()
    click(app, "Check anyway")
    click(app, "Next →")
    click(app, "← Back")
    assert "सीबीआई" in app.text_area(key="detail_Q1").value
