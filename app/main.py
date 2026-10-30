"""Counter Kavach: five-step wizard for counter staff. UI only; all logic lives in kavach/."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kavach import privacy  # noqa: E402

privacy.install_from_env()  # before any model library is imported

import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402

import streamlit as st  # noqa: E402

from app import components as ui  # noqa: E402
from kavach import actions, audit, interview, report  # noqa: E402
from kavach.anomaly import score_transaction  # noqa: E402
from kavach.config import load_config, resolve  # noqa: E402
from kavach.metrics import system_info  # noqa: E402
from kavach.pipeline import preliminary, run_check  # noqa: E402
from kavach.schemas import Answer, TransactionContext, TxnType  # noqa: E402

st.set_page_config(page_title="Counter Kavach", page_icon="🛡️", layout="wide")
CFG = load_config()
DEMOS = {"Demo 1 · digital arrest (Hindi)": "da_01", "Demo 2 · investment scam": "inv_01",
         "Demo 3 · genuine wedding payment": "gen_01"}
CHOICES = ["yes", "no", "unsure", "skip"]
CHOICE_LABELS = {"en": {"yes": "Yes", "no": "No", "unsure": "Unsure", "skip": "Skip"},
                 "hi": {"yes": "हाँ", "no": "नहीं", "unsure": "पता नहीं", "skip": "छोड़ें"}}
DEFAULT_CTX = {"customer_age": 60, "avg_monthly_debit_inr": 40000, "max_single_debit_inr_12m": 100000,
               "txn_amount_inr": 100000, "txn_type": "NEFT", "beneficiary_is_new": False,
               "customer_on_call_at_counter": False, "accompanied_by_unknown_person": False,
               "payee_reference": "", "staff_notes": ""}
QUESTIONS = interview.questions()
ss = st.session_state


@st.cache_resource(show_spinner="Loading the local LLM (one time)…")
def load_backend():
    from kavach.llm.backend import get_backend
    if os.environ.get("KAVACH_NO_LLM") == "1":
        return None, "disabled by KAVACH_NO_LLM=1"
    try:
        return get_backend(CFG), None
    except Exception as e:  # missing model file, bad build
        return None, f"{type(e).__name__}: {e}"


@st.cache_resource(show_spinner="Loading speech-to-text (one time)…")
def load_asr():
    from kavach.asr import ASR
    try:
        return ASR(CFG), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


@st.cache_resource
def startup_cleanup() -> int:
    return audit.purge_older_than("var/reports", CFG["retention_days"]) if resolve("var/reports").exists() else 0


@st.cache_data
def sysinfo() -> dict:
    return system_info()


def init_state() -> None:
    ss.setdefault("step", "intake")
    ss.setdefault("qidx", 0)
    ss.setdefault("ctx_data", dict(DEFAULT_CTX))
    ss.setdefault("answers", {})
    ss.setdefault("result", None)
    ss.setdefault("note", None)
    ss.setdefault("asr_times", [])
    ss.setdefault("staff_name", "Counter staff (synthetic)")


def reset() -> None:
    keep = {"lang"}
    for k in list(ss.keys()):
        if k not in keep:
            del ss[k]


def load_demo() -> None:
    label = ss.get("demo_pick")
    if label not in DEMOS:
        return
    s = json.loads((resolve("data/scenarios") / f"{DEMOS[label]}.json").read_text(encoding="utf-8"))
    ss.ctx_data = dict(s["transaction"])
    for k, v in ss.ctx_data.items():
        ss[f"f_{k}"] = v
    ss.answers = {qid: {"choice": a.get("choice"), "detail": a.get("detail", "")} for qid, a in s["answers"].items()}
    for qid in ss.answers:
        ss.pop(f"choice_{qid}", None)
        ss.pop(f"detail_{qid}", None)
    ss.result = None


def current_ctx() -> TransactionContext:
    return TransactionContext(**ss.ctx_data)


def collected_answers() -> dict[str, Answer]:
    return {qid: Answer(choice=a.get("choice"), detail=a.get("detail", ""))
            for qid, a in ss.answers.items() if a.get("choice") or a.get("detail", "").strip()}


# --- sidebar --------------------------------------------------------------------------------------------

def sidebar() -> None:
    with st.sidebar:
        st.markdown("### 🛡️ Counter Kavach")
        ui.offline_badge(privacy.offline_guard_active())
        st.radio("Language / भाषा", ["en", "hi"], key="lang", horizontal=True,
                 format_func=lambda c: {"en": "English", "hi": "हिन्दी"}[c])
        m = CFG["models"]
        llm_file = Path(m["llm_fallback_path"] if m.get("use_fallback") else m["llm_path"]).name
        st.caption(f"**LLM** {llm_file}  \n**Speech** faster-whisper small ({CFG['asr']['compute_type']})  \n"
                   f"**Runtime** llama.cpp (CPU)")
        info = sysinfo()
        st.caption(f"**CPU** {info['cpu']}  \n{info['physical_cores']} cores / {info['logical_cores']} threads · "
                   f"{info['ram_gb']} GB RAM · no GPU")
        if ss.result is not None:
            st.markdown("**Last check**")
            ui.metrics_panel(ss.result, ss.asr_times)
        st.button("Reset", on_click=reset, width="stretch")


# --- step 1: intake -------------------------------------------------------------------------------------

def step_intake() -> None:
    st.subheader("1 · Transaction")
    st.selectbox("Load demo scenario", ["—"] + list(DEMOS), key="demo_pick", on_change=load_demo)
    for k, v in ss.ctx_data.items():
        ss.setdefault(f"f_{k}", v)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.number_input("Customer age", 18, 110, key="f_customer_age")
        st.number_input("Amount (₹)", 1, 100_000_000, step=10000, key="f_txn_amount_inr")
        st.selectbox("Type", [t.value for t in TxnType], key="f_txn_type")
    with c2:
        st.number_input("Average monthly debit, last 6 months (₹)", 0, 100_000_000, step=5000,
                        key="f_avg_monthly_debit_inr")
        st.number_input("Largest single debit, last 12 months (₹)", 0, 100_000_000, step=5000,
                        key="f_max_single_debit_inr_12m")
        st.text_input("Payee account / UPI ID (masked unless marked fraud)", key="f_payee_reference")
    with c3:
        st.toggle("New beneficiary", key="f_beneficiary_is_new")
        st.toggle("Customer on a phone / video call at the counter", key="f_customer_on_call_at_counter")
        st.toggle("Accompanied by an unknown person", key="f_accompanied_by_unknown_person")
        st.text_area("Staff notes", key="f_staff_notes", height=68)
    ss.ctx_data = {k: ss[f"f_{k}"] for k in DEFAULT_CTX}

    a = score_transaction(current_ctx(), CFG)
    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"**Transaction anomaly score: {a.score}/100**")
        for r in a.reasons:
            st.markdown(f"- {r}")
    with right:
        if a.check_recommended:
            st.warning("Guided check recommended before processing.")
        st.text_input("Staff name", key="staff_name")
        b1, b2 = st.columns(2)
        if b1.button("Start guided check", type="primary", disabled=not a.check_recommended,
                     width="stretch"):
            ss.step, ss.qidx = "interview", 0
            st.rerun()
        if b2.button("Check anyway", width="stretch"):
            ss.step, ss.qidx = "interview", 0
            st.rerun()


# --- step 2: guided check --------------------------------------------------------------------------------

def transcribe_if_new(q, audio) -> None:
    data = audio.getvalue()
    digest = hashlib.sha1(data).hexdigest()
    if ss.get(f"audio_hash_{q.id}") == digest:
        return
    asr, err = load_asr()
    if asr is None:
        st.error(f"Speech-to-text unavailable, please type. ({err})")
        return
    with st.spinner("Stage: speech to text…"):
        tr = asr.transcribe(data, ss.lang)
    from kavach.asr import needs_typing
    ss[f"audio_hash_{q.id}"] = digest
    ss.asr_times.append(tr.seconds)
    ss[f"detail_{q.id}"] = tr.text
    ss[f"asr_note_{q.id}"] = (tr, needs_typing(tr, CFG))


def step_interview() -> None:
    lang = ss.lang
    q = QUESTIONS[ss.qidx]
    stored = ss.answers.get(q.id, {})
    ss.setdefault(f"detail_{q.id}", stored.get("detail", ""))
    if q.type == "yes_no" and f"choice_{q.id}" not in ss:
        ss[f"choice_{q.id}"] = stored.get("choice")

    main, tips = st.columns([3, 1])
    with main:
        st.progress((ss.qidx + 1) / len(QUESTIONS), text=f"2 · Guided check · question {ss.qidx + 1} of {len(QUESTIONS)}")
        st.markdown(f"#### {q.id}. {getattr(q, lang)}")
        st.caption(q.hi if lang == "en" else q.en)
        choice = None
        if q.type == "yes_no":
            choice = st.radio("Answer", CHOICES, key=f"choice_{q.id}", horizontal=True, index=None,
                              format_func=lambda c: CHOICE_LABELS[lang][c], label_visibility="collapsed")
            probe = interview.probe(q.id, choice, lang)
            if probe:
                st.info(f"Ask next: {probe}")
        audio = st.audio_input("Record the answer (optional)", key=f"audio_{q.id}")
        if audio is not None:
            transcribe_if_new(q, audio)
        note = ss.get(f"asr_note_{q.id}")
        if note:
            tr, bad = note
            msg = f"Transcribed in {tr.seconds:.1f} s (confidence {tr.avg_logprob:.2f}). Check and edit below."
            (st.warning("Low-confidence transcript: please type or correct the answer.") if bad else st.caption(msg))
        st.text_area("Answer in the customer's words (edit before analysis)", key=f"detail_{q.id}", height=80)
        ss.answers[q.id] = {"choice": choice, "detail": ss[f"detail_{q.id}"]}

        b1, b2, b3 = st.columns([1, 1, 2])
        if b1.button("← Back", width="stretch"):
            if ss.qidx == 0:
                ss.step = "intake"
            else:
                ss.qidx -= 1
            st.rerun()
        last = ss.qidx == len(QUESTIONS) - 1
        if b2.button("Analyse →" if last else "Next →", type="primary", width="stretch"):
            if last:
                ss.step, ss.result = "risk", None
            else:
                ss.qidx += 1
            st.rerun()
        ready = interview.escalation_ready(collected_answers(), current_ctx(), CFG)
        if ready and not last and b3.button("Enough to escalate → risk card", width="stretch"):
            ss.step, ss.result = "risk", None
            st.rerun()
    with tips:
        st.markdown("**Staff tips**")
        for tip in interview.staff_tips(lang):
            st.caption(f"• {tip}")


# --- step 4: risk card ------------------------------------------------------------------------------------

def render_card(risk, lang: str, prelim: bool, summary: str = "") -> None:
    ui.risk_badge(risk.level, risk.score, risk.scam_type, lang, prelim)
    fired = risk.overrides_applied + risk.floors_applied
    if fired:
        st.caption("Fired: " + ", ".join(fired))
    st.markdown("**Why**")
    ui.evidence_list(risk.evidence)
    if summary:
        st.caption(f"LLM summary: {summary}")


def step_risk() -> None:
    lang = ss.lang
    ctx, answers = current_ctx(), collected_answers()
    if ss.result is None:
        ph = st.empty()
        with ph.container():
            render_card(preliminary(ctx, answers, cfg=CFG), lang, prelim=True)
        backend, err = load_backend()
        if err:
            st.error(f"LLM unavailable, using rules and transaction signals only. ({err})")
        with st.spinner("Stage: LLM analysis on CPU… the preliminary card above is already usable"):
            ss.result = run_check(ctx, answers, backend=backend, cfg=CFG, use_llm=backend is not None)
        ph.empty()
        st.rerun()

    res = ss.result
    risk = res.risk
    a = res.analyzer
    card, act = st.columns([3, 2])
    with card:
        st.subheader("4 · Risk card")
        summary = a.assessment.staff_summary if a.available and a.assessment else ""
        render_card(risk, lang, prelim=False, summary=summary)
        if not a.available:
            st.caption(f"LLM unavailable ({a.error or 'not loaded'}): rules and transaction signals only.")
        st.markdown("**What to say to the customer**")
        st.info(actions.customer_message(risk.scam_type, risk.level, lang))
    with act:
        st.markdown("**Recommended actions**")
        for i, item in enumerate(actions.recommended(risk.level, lang)):
            st.checkbox(item, key=f"act_{i}")
        options = actions.action_options()
        st.selectbox("Action taken (required)", options, index=None, key="action_taken",
                     placeholder="Choose what the officer decided")
        st.checkbox("Mark as suspected fraud (keeps payee details in the complaint)", key="suspected_fraud")
        st.text_input("Authorised officer", key="officer_name")
        can = bool(ss.get("action_taken")) and bool(ss.get("officer_name", "").strip())
        c1, c2 = st.columns(2)
        if c1.button("← Edit answers", width="stretch"):
            ss.step, ss.qidx = "interview", len(QUESTIONS) - 1
            st.rerun()
        if c2.button("Create report →", type="primary", disabled=not can, width="stretch"):
            note = report.build_note(res, ctx, answers, staff_name=ss.staff_name, officer_name=ss.officer_name,
                                     action_taken=ss.action_taken, suspected_fraud=ss.get("suspected_fraud", False),
                                     models={"llm": res.model_name or "not used",
                                             "speech": "faster-whisper small int8" if ss.asr_times else "not used"},
                                     cfg=CFG)
            ss.note = note
            ss.report_paths = report.save(note)
            audit.append(note)
            ss.step = "report"
            st.rerun()


# --- step 5: report ---------------------------------------------------------------------------------------

def step_report() -> None:
    note = ss.note
    st.subheader(f"5 · Incident report {note.id}")
    left, right = st.columns([3, 2])
    with left:
        with st.container(height=480):
            st.markdown(report.render_markdown(note))
    with right:
        st.download_button("Download Markdown", report.render_markdown(note), f"{note.id}.md",
                           mime="text/markdown", width="stretch")
        st.download_button("Download HTML", report.render_html(note), f"{note.id}.html", mime="text/html",
                           width="stretch")
        st.markdown("**Complaint summary** (paste into 1930 / cybercrime.gov.in)")
        st.code(report.complaint_summary(note), language=None, wrap_lines=True)
        st.caption(f"Saved to var/reports/ and logged in var/audit.jsonl (hash-chained).")
        st.button("New check", type="primary", on_click=reset, width="stretch")


init_state()
startup_cleanup()
sidebar()
{"intake": step_intake, "interview": step_interview, "risk": step_risk, "report": step_report}[ss.step]()
st.caption("Prototype · not certified · not legal advice · cannot confirm whether a document is genuine · "
           "the tool advises, a person decides.")
