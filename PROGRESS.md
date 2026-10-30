# Progress

**Deadline:** Sun 1 Nov 2026, 6 PM IST (target submit 3 PM) · **Current milestone:** M1, not started · **Last updated:** 2026-10-30

**Next action:** create conda env `kavach` (Python 3.11) and install `llama-cpp-python` (first item in TODO.md).

## Milestones

| Milestone | Status | Notes |
|---|---|---|
| M0 Plan | Done | `PLAN.md` v2 with review fixes; CLAUDE.md, TODO.md, PROGRESS.md created |
| M1 Environment and scaffold | Not started | |
| M2 Core logic and rules | Not started | |
| M5a Scenarios (pulled forward) | Not started | Must be committed before any tuning |
| M3 Interview, analyzer, fusion, report | Not started | |
| M4 UI and voice | Not started | Voice time-boxed to 2 h |
| M5b Eval and benchmark | Not started | |
| M6 Stretch | Not started | Only if M1–M5 pass |
| M7 README and submission | Not started | |

## Environment check (2026-10-30)

| Item | Found | Action |
|---|---|---|
| OS | Windows 11 Home Single Language | Keep code cross-platform |
| CPU | AMD Ryzen 7 250, 8 cores / 16 threads | `n_threads` = 8 |
| RAM | 15.2 GB | 4B Q4_K_M fits |
| GPU use | None (CPU only by design) | — |
| System Python | 3.14.5 | Don't use; wheels may be missing |
| Miniconda | `%USERPROFILE%\miniconda3` (base 3.13.12), not on PATH; existing env: `sahayak` | Create `kavach` (3.11) |
| make | Not installed | Use `tasks.py` |
| Tesseract | Not installed | Only needed for P1 notice check |
| llama-cpp-python | Not installed | First M1 task |
| Energy counters | No RAPL on Windows | Energy is labelled "estimated" |
| Git | `origin` = github.com/warlords94/counter-kavach, 1 commit ("Initial commit"); plan PDF untracked | Keep the PDF out of the repo |

## Measurements

Fill from real runs only.

| Metric | Value | Model / setting | Date |
|---|---|---|---|
| LLM step, demo scenario 1 (s) | — | | |
| Prompt tokens / output tokens | — | | |
| Prompt tokens/s / generation tokens/s | — | | |
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

None yet.

## Session log

### 2026-10-30 (Fri)

- Reviewed the PDF build plan. Found spec bugs:
  - "police verification for my passport" triggered the hard override to HIGH
  - negated answers matched the authority regex
  - a coached victim on a live call scored LOW
  - "always MEDIUM" met both eval targets
  - the guided check fired on tiny payments
- Wrote `PLAN.md` v2 with the fixes. Checked the rewritten regexes against 18 positive and hard-negative cases (English, Hinglish, Devanagari): all pass.
- Created `CLAUDE.md`, `TODO.md`, `PROGRESS.md`.
- Next: M1, starting with the conda env and the `llama-cpp-python` install.
