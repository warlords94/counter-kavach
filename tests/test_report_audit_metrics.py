import json
import os
import time

from kavach import audit, metrics, report
from kavach.pipeline import run_check
from kavach.schemas import Answer
from tests.conftest import make_ctx
from tests.test_analyzer import FakeBackend, assessment


def _result(scenario, suspected_fraud=False):
    s = scenario("da_01")
    ctx = make_ctx(**s["transaction"])
    qa = {k: Answer(**v) for k, v in s["answers"].items()}
    qa["Q1"] = Answer(detail=qa["Q1"].detail + " Aadhaar 1234 5678 9012")
    res = run_check(ctx, qa, backend=FakeBackend([assessment("high", [("threat", "गिरफ्तार कर लेंगे", "Q8")])]))
    note = report.build_note(res, ctx, qa, staff_name="Staff A (synthetic)", officer_name="Manager B (synthetic)",
                             action_taken="Escalated to branch manager", suspected_fraud=suspected_fraud)
    return res, note


def test_run_check_returns_risk_and_stage_timings(scenario):
    res, _ = _result(scenario)
    assert res.risk.level == "HIGH"
    assert {"anomaly", "rules", "llm", "fusion"} <= set(res.timings)
    assert res.total_seconds >= 0


def test_markdown_report_masks_aadhaar_and_payee(scenario):
    _, note = _result(scenario)
    md = report.render_markdown(note)
    assert "HIGH" in md and "XXXX XXXX 9012" in md and "1234 5678 9012" not in md
    assert "SAMPLE-ACCT-000011112222" not in md


def test_payee_kept_in_full_when_suspected_fraud(scenario):
    _, note = _result(scenario, suspected_fraud=True)
    assert "SAMPLE-ACCT-000011112222" in report.complaint_summary(note)


def test_complaint_summary_is_five_lines(scenario):
    _, note = _result(scenario)
    lines = report.complaint_summary(note).splitlines()
    assert len(lines) == 5 and "₹18,00,000" in lines[1]


def test_html_report_escapes_answer_text(scenario):
    res, note = _result(scenario)
    note.qa[0].detail = "<script>alert(1)</script>"
    html = report.render_html(note)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_audit_log_appends_and_hash_chain_detects_edits(scenario, tmp_path):
    _, note = _result(scenario)
    log = tmp_path / "audit.jsonl"
    audit.append(note, log)
    audit.append(note, log)
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2
    assert audit.verify_chain(log)
    lines = log.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["level"] = "LOW"
    log.write_text(json.dumps(rec, ensure_ascii=False) + "\n" + lines[1] + "\n", encoding="utf-8")
    assert not audit.verify_chain(log)


def test_purge_deletes_files_older_than_retention(tmp_path):
    old, new = tmp_path / "old.md", tmp_path / "new.md"
    old.write_text("x", encoding="utf-8")
    new.write_text("y", encoding="utf-8")
    past = time.time() - 40 * 86400
    os.utime(old, (past, past))
    assert audit.purge_older_than(tmp_path, days=30) == 1
    assert not old.exists() and new.exists()


def test_stage_timer_records_named_stages():
    t = metrics.StageTimer()
    with t.stage("rules"):
        sum(range(1000))
    assert "rules" in t.timings and t.timings["rules"] >= 0


def test_energy_from_rapl_counter_is_measured(tmp_path):
    counter = tmp_path / "energy_uj"
    counter.write_text("1000000", encoding="utf-8")
    m = metrics.EnergyMeter(rapl_path=counter, tdp_watts=28)
    m.start()
    counter.write_text("3500000", encoding="utf-8")
    joules, kind = m.stop()
    assert joules == 2.5 and kind == "measured"


def test_energy_without_rapl_is_labelled_estimated(tmp_path):
    m = metrics.EnergyMeter(rapl_path=tmp_path / "missing", tdp_watts=28)
    m.start()
    joules, kind = m.stop()
    assert kind == "estimated" and joules >= 0


def test_system_info_has_cpu_cores_and_ram():
    info = metrics.system_info()
    assert info["physical_cores"] >= 1 and info["ram_gb"] > 0 and info["cpu"]
