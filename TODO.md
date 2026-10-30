# TODO

Deadline: **Sun 1 Nov 2026, 6 PM IST** (target submit 3 PM). Work top to bottom; tick items as they're done. Specs for every item are in `PLAN.md`. If something is cut, move it to "Cut / deferred" with a reason.

## Friday 30 Oct, evening (~4 h)

### M1 · Environment and scaffold
- [ ] Create conda env `kavach` with Python 3.11 (`%USERPROFILE%\miniconda3\Scripts\conda.exe create -n kavach python=3.11 -y`)
- [ ] Install `llama-cpp-python` from the prebuilt CPU wheel index; if no wheel, install VS 2022 Build Tools (C++) + CMake. On failure: stop, record the exact error in PROGRESS.md
- [ ] Scaffold the repo tree from PLAN.md (`kavach/`, `app/`, `data/`, `eval/`, `scripts/`, `tests/`, `docs/`)
- [x] `.gitignore`: plan PDF, `models/`, `var/`, Python caches
- [ ] `.gitignore`: add the downloaded-datasets folder once it's chosen
- [ ] `requirements.txt` with pinned versions (Streamlit ≥ 1.40)
- [ ] `config.yaml` from the PLAN.md sketch
- [ ] `.streamlit/config.toml` with `browser.gatherUsageStats = false`
- [ ] `tasks.py` (setup, models, run, test, eval, bench) + Makefile wrapper
- [ ] `scripts/download_models.py`: Qwen3-4B-Instruct-2507 Q4_K_M, Qwen2.5-1.5B-Instruct Q4_K_M, faster-whisper small → `models/`; record exact repos and files
- [ ] `kavach/llm/backend.py` (`LLMBackend`, `GenerationResult`), `llamacpp_backend.py`, `kompact_backend.py` stub
- [ ] Smoke test on demo scenario 1: valid JSON, prompt/output tokens, tokens/s, LLM seconds → PROGRESS.md
- [ ] Apply the model choice rule (LLM > 25 s → 1.5B fallback) and record it in DECISIONS.md
- [ ] Commit M1

### M2 · Core logic and rules
- [ ] `kavach/schemas.py` (all Pydantic models)
- [ ] `kavach/anomaly.py` + tests (₹50,000 amount gate, max-single-debit signal, cap 100)
- [ ] `kavach/textnorm.py` + tests (NFC, casefold, whitespace, abbreviation dots, negation window)
- [ ] `kavach/rules/red_flags.yaml`: all rules from PLAN.md (answer rules + text rules, EN / Hinglish / Devanagari)
- [ ] `kavach/rules/engine.py`:
  - text rules run only on Q1, staff notes, notice text and Yes/Unsure details
  - Unsure counts at half weight
  - each rule id counts once
  - `LIVE_CALL` comes from the transaction flag or Q6
- [ ] Rule tests: a positive and a hard negative per text rule, plus the 5 listed hard negatives
- [ ] `kavach/privacy.py`:
  - customer identifiers always masked; suspect identifiers kept in full only when the case is marked suspected fraud
  - offline guard wraps `create_connection`, `connect` and `getaddrinfo`; allows localhost, `127.0.0.1` and `::1`
- [ ] Test proving an outbound connection fails with `OFFLINE=1`
- [ ] Commit M2

### Non-code
- [ ] Resume ready as PDF

## Saturday 31 Oct (~10 h)

### M5a · Scenarios first, before any tuning (pulled forward from M5)
- [ ] `scripts/make_scenarios.py` + 40 scenarios in `data/scenarios/`:
  - 10 digital arrest, 5 investment, 4 KYC, 3 relative in trouble, 2 lottery or refund, 16 genuine
  - at least 5 coached scams
  - genuine hard negatives (passport, land case, son's fees, elderly customer on a call with their son)
  - 20 dev / 20 test, stratified by group
  - answers in English, Hindi and Hinglish
- [ ] Hand-review and edit every scenario (no text copied from real complaints)
- [ ] Commit the scenarios **before** any rule or weight tuning

### M3 · Interview, analyzer, fusion, report
- [ ] `data/question_bank.yaml`: Q1–Q10 in EN + HI, with `type`, `risk_answer`, `probes` and `branch_to`
- [ ] `kavach/interview.py`: one question at a time, probes on risk answers, "Enough to escalate" check
- [ ] `kavach/llm/prompts/analyzer.md`: system prompt of about 350 tokens or fewer, with the required statements
- [ ] `kavach/analyzer.py`:
  - JSON schema, one retry, then the "LLM unavailable" fallback
  - likelihood → score mapping
  - evidence guard (`partial_ratio` ≥ 85), no-evidence cap of 30, log of dropped flags
- [ ] `kavach/fusion.py`: re-normalised weights, overrides, floors
- [ ] Fusion tests: worked examples A–D, with and without the LLM
- [ ] `kavach/actions.yaml` + `actions.py`: actions per level; EN/HI customer-message templates per scam type and level
- [ ] `kavach/report.py` + templates: Markdown, HTML and the 5-line complaint summary
- [ ] `kavach/audit.py`: append to `var/audit.jsonl`, delete files past retention
- [ ] `kavach/metrics.py`: per-stage timings, tokens/s, energy (RAPL or labelled estimate)
- [ ] Commit M3

### M4 · UI and voice
- [ ] `app/main.py` 5-step wizard:
  - Intake: form, demo dropdown, anomaly reasons, "Start guided check" / "Check anyway"
  - Guided check: EN/HI toggle, Yes/No/Unsure/Skip, detail box, probes, progress bar, "Enough to escalate"
  - Risk card: preliminary rules card, then the LLM result; evidence chips, customer message, actions checklist, required "Action taken" and "Suspected fraud"
  - Report: preview, downloads, complaint summary, "New check"
- [ ] `app/components.py` (risk badge, evidence list, metrics panel)
- [ ] Sidebar: Offline badge, models + quantisation, CPU, stage latency, tokens/s, energy, Reset
- [ ] 3 demo scenarios in the dropdown (digital arrest, investment scam, genuine wedding)
- [ ] Check that a full check fits 1366×768 without scrolling
- [ ] `kavach/asr.py` + a mic button per detail box. **Time-box to 2 h**; typing stays the fallback
- [ ] Commit M4

### M5b · Eval and benchmark
- [ ] `eval/run_eval.py` → `eval/results/summary.md`:
  - LLM cache in `var/llm_cache/` (`NOCACHE=1` bypasses it)
  - recall, false alarms and genuine MEDIUM or higher, as counts and percentages; coached scams separately
  - ablations (rules only, LLM only, fused) plus "always MEDIUM" and "anomaly only" baselines
  - overrides and floors fired; JSON validity; evidence-guard drops; p50/p95
  - each miss listed with a one-line reason
- [ ] `eval/bench.py`: test split, cache off; OS/CPU/RAM/model table with latency, tokens/s, J/check and Wh per 1,000 checks
- [ ] Tune weights on **dev only**; record every change in DECISIONS.md
- [ ] Copy the final eval and bench numbers into PROGRESS.md
- [ ] Commit M5

## Sunday 1 Nov (~8 h)

### M6 · Stretch (only if M1–M5 pass)
- [ ] `kavach/notice_check.py` (Tesseract eng+hin) + synthetic notice images marked SAMPLE
- [ ] PDF export (fpdf2 + Noto Sans Devanagari)
- [ ] SHA-256 hash chain in the audit log
- [ ] Commit M6

### M7 · README and submission
- [ ] `docs/architecture.png`
- [ ] README: all 12 sections from PLAN.md, eval and bench tables from real runs, models and licenses
- [ ] MIT `LICENSE`
- [ ] Fresh-clone test: setup → models → run works; with Wi-Fi off and `OFFLINE=1`, a full check works
- [ ] Record the 2-minute demo (Wi-Fi visibly off); upload unlisted; demo GIF; link at the top of the README
- [ ] Commit M7, push, make the repo public; check the URL opens while logged out
- [ ] Submit the form by 3 PM IST:
  - "Working Professional", team size 1
  - project description with unbuilt features removed
  - resume PDF
  - acknowledgement ticked
- [ ] Confirm the email copy of the form responses arrived

## Cut list (only if behind, in this order)

1. Notice OCR
2. PDF export
3. Voice (buttons + typing stay)
4. Shrink eval to 20 scenarios

Never cut the README or the eval table.

## Cut / deferred

_Nothing yet._
