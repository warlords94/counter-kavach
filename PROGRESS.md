# Progress

**Deadline:** Sun 1 Nov 2026, 6 PM IST (target submit 3 PM) · **Current milestone:** M3 (interview, actions, report, audit, metrics) · **Last updated:** 2026-10-30

**Next action:** `kavach/interview.py`, then actions/report/audit/metrics, then the Streamlit UI (M4).

## Milestones

| Milestone | Status | Notes |
|---|---|---|
| M0 Plan | Done | `PLAN.md` v2; CLAUDE.md, TODO.md, PROGRESS.md |
| M1 Environment and scaffold | Done | conda env `kavach` (3.11.18), llama-cpp-python 0.3.36 prebuilt CPU wheel, models downloaded; 4B kept (see DECISIONS.md) |
| M2 Core logic and rules | Done | anomaly, textnorm, rules engine + YAML, privacy + offline guard |
| M5a Scenarios (pulled forward) | Done, needs hand review | 40 scenarios committed in 8b6f179 before any eval/tuning; drafted by Claude, **Avinash to review** |
| M3 Interview, analyzer, fusion, report | In progress | analyzer + evidence guard + fusion done with tests; interview, actions, report, audit, metrics left |
| M4 UI and voice | Not started | Voice time-boxed to 2 h |
| M5b Eval and benchmark | Not started | |
| M6 Stretch | Not started | Only if M1–M5 pass |
| M7 README and submission | Not started | |

Tests: **107 passed** (`python tasks.py test`, includes one real-LLM test).

## Environment check (2026-10-30)

| Item | Found | Action |
|---|---|---|
| OS | Windows 11 Home Single Language | Keep code cross-platform |
| CPU | AMD Ryzen 7 250, 8 cores / 16 threads | `n_threads` = 8 |
| RAM | 15.2 GB | 4B Q4_K_M fits |
| System Python | 3.14.5 | Not used |
| Conda env | `kavach`, Python 3.11.18 | Done |
| llama-cpp-python | 0.3.36, prebuilt CPU wheel, AVX2 (no AVX-512) | Done, no compiler needed |
| Models | Qwen3-4B-Instruct-2507 Q4_K_M (2.5 GB), Qwen2.5-1.5B-Instruct Q4_K_M, faster-whisper small | Downloaded to `models/` |
| make | Not installed | Use `tasks.py` |
| Tesseract | Not installed | Only needed for P1 notice check |
| Energy counters | No RAPL on Windows | Energy is labelled "estimated" |
| Power | Plugged in; Windows power mode not checked | Try "Best performance" before benchmarking |

## Measurements

Real runs on the reference laptop, 8 threads, plugged in, Qwen3-4B-Instruct-2507 Q4_K_M unless noted.

| Metric | Value | Model / setting | Date |
|---|---|---|---|
| Model load | 4.4 s | 4B | 2026-10-30 |
| Prompt processing | ~39 tok/s (1,079 tokens in 27.5 s) | 4B, cold | 2026-10-30 |
| Decoding | ~7.3 tok/s | 4B | 2026-10-30 |
| Grammar overhead | ~13 s per 160 output tokens (~0.08 s/token) | 4B, JSON-schema grammar | 2026-10-30 |
| KV prefix reuse | repeat prompt re-evaluates 1 token instead of 1,079 | 4B | 2026-10-30 |
| LLM step, genuine/coached (wedding, builder) | 14–15 s warm, 32 s cold (first check) | 4B, unconstrained first attempt | 2026-10-30 |
| LLM step, English/Hinglish scam (inv_01, da_09) | 35–39 s | 4B | 2026-10-30 |
| LLM step, Hindi scam (da_01, demo 1) | 74–92 s (~370 output tokens, long Devanagari quotes) | 4B | 2026-10-30 |
| LLM quality probe | da_01, inv_01, da_09 → high, correct scam type, all quotes pass the guard; gen_01, da_03 → low | 4B | 2026-10-30 |
| LLM quality probe, fallback | da_01 → **low** (wrong), invented facts | Qwen2.5-1.5B | 2026-10-30 |
| ASR per clip (s) | — | | |
| Total machine time per check (s) | — | | |
| Energy per check (J, estimated) | — | | |

## Eval results (latest)

| Metric | Target | Dev | Test | All 40 |
|---|---|---|---|---|
| Scams flagged MEDIUM or HIGH | ≥ 90% (≥ 22/24 overall) | — | — | — |
| Scams flagged HIGH | report | — | — | — |
| Coached scams flagged MEDIUM or HIGH | report | — | — | — |
| Genuine flagged HIGH | ≤ 10% (≤ 1/16 overall) | — | — | — |
| Genuine flagged MEDIUM or HIGH | ≤ 30% (≤ 4/16 overall) | — | — | — |
| JSON validity | report | — | — | — |
| Evidence-guard drops | report | — | — | — |

## Blockers

None. Risk: the LLM step on Hindi-heavy scam cases (35–90 s) is far over the 20 s target on this laptop. Mitigations in place: instant rules card, cached system prompt, unconstrained first attempt. Kompact (Phase 2) is the planned speed-up.

## Session log

### 2026-10-30 (Fri), morning: planning

- Reviewed the PDF build plan and found spec bugs (passport hard negative forced HIGH; negated answers matched the authority regex; a coached victim on a live call scored LOW; "always MEDIUM" met both eval targets; the guided check fired on tiny payments).
- Wrote `PLAN.md` v2 with the fixes; created `CLAUDE.md`, `TODO.md`, `PROGRESS.md`. Working on branch `build`.

### 2026-10-30 (Fri), M1 + M2 + M5a

- Created the conda env and installed requirements (llama-cpp-python wheel, no compiler needed); downloaded all three models.
- M2 test-first: anomaly, textnorm (NFC, nukta, abbreviation dots, clause-aware negation), rules engine (answer + text rules, each id once, Unsure at half weight), privacy masking + offline guard.
- Analyzer + evidence guard + fusion (re-normalised weights, floors, overrides); worked examples A–D pass as tests.
- 40 scenarios generated by `scripts/make_scenarios.py` and committed before any eval.
- Smoke test found output truncation (Devanagari quotes hit the 384-token cap) and ~90 s per attempt. Measured where the time goes, bounded the schema, put the JSON shape and question list in the cached system prompt, and switched the first attempt to unconstrained. Kept the 4B because the 1.5B misjudged demo 1. Details in DECISIONS.md.
