# Counter Kavach

Offline, CPU-only Streamlit copilot that helps bank counter staff spot coercion scams ("digital arrest", impersonation) before a large withdrawal or transfer, and records an SOP-ready incident note. Build Next submission deadline: **Sun 1 Nov 2026, 6 PM IST** (target 3 PM).

## Start of every session

1. Read `PROGRESS.md`: current milestone, measured numbers, blockers.
2. Read `TODO.md`: the first unchecked item is the next task, and TODO.md sets the order.
3. Read the section of `PLAN.md` for the module you are about to build. PLAN.md is the design source of truth. Do not reintroduce anything listed under "Changes from the PDF version".

## Hard constraints

- Python 3.11, CPU only, no GPU code, no cloud APIs.
- No network at runtime. Only `scripts/download_models.py` downloads. With `OFFLINE=1`, the offline guard in `kavach/privacy.py` is installed before any model library is imported. Load models from local paths only (never by Hub name).
- All LLM calls go through `LLMBackend` (`kavach/llm/backend.py`); exactly one LLM call per check.
- Every threshold, weight, floor, override and model path lives in `config.yaml`; no magic numbers in code.
- Synthetic data only: invented names, account numbers that fail checksum, no real agency logos or seals.
- The tool advises; it never blocks or approves a transaction. Age is the only personal attribute scored.
- Never commit `models/`, `var/`, downloaded datasets, or the plan PDF.

## Environment (reference laptop)

- Windows 11, AMD Ryzen 7 250 (8 cores / 16 threads), 15 GB RAM, no GPU.
- System Python is 3.14: do not use it. Use the conda env `kavach` (Python 3.11).
  - conda is not on PATH; it lives at `%USERPROFILE%\miniconda3\Scripts\conda.exe`.
  - Call the env's interpreter directly: `%USERPROFILE%\miniconda3\envs\kavach\python.exe`.
- No `make`: use `python tasks.py <target>`; the Makefile wraps `tasks.py` for Linux/macOS.
- No Tesseract (P1 only). No RAPL on Windows, so energy is always labelled "estimated".
- Encoding:
  - The console is cp1252, so printing Devanagari crashes. Run Python with `-X utf8`; `-I` ignores `PYTHONIOENCODING`.
  - Always pass `encoding="utf-8"` to `open()` / `read_text()` / `write_text()`; the Windows default would corrupt Hindi YAML and reports.

## Commands

| Task | Windows | Linux/macOS |
|---|---|---|
| Install deps | `python tasks.py setup` | `make setup` |
| Download models | `python tasks.py models` | `make models` |
| Run app | `python tasks.py run` | `make run` |
| Tests | `python tasks.py test` | `make test` |
| Eval (cached LLM) | `python tasks.py eval` (`NOCACHE=1` for fresh calls) | `make eval` |
| Benchmark | `python tasks.py bench` | `make bench` |
| One test | `python -X utf8 -m pytest tests/test_rules.py -k passport -q` | same |

## Code conventions

- All logic lives in the `kavach/` package. `app/` is UI only. Eval and bench call the same code path as the app.
- All module I/O uses Pydantic v2 models in `kavach/schemas.py`.
- Use `pathlib` everywhere, `yaml.safe_load`, and type hints on public functions; keep comments sparse.
- All text matching goes through `kavach/textnorm.py` (NFC, casefold, abbreviation dots, negation window).
- Never put `\b` around Devanagari: Python treats matras as non-word characters.
- Regexes in YAML go in single quotes; write `''` for a literal apostrophe.
- Every text rule gets a positive and a hard-negative test. The fusion worked examples in PLAN.md (cases A–D, with and without the LLM) are tests.

## Workflow

- Work through `TODO.md` top to bottom. Don't start M6 (stretch) until M1–M5 pass.
- After each milestone:
  - run the tests and show the output
  - tick `TODO.md`
  - update `PROGRESS.md` (status table, measurements, session log, next action)
  - record choices in `DECISIONS.md`
  - commit
- Commit locally after each milestone; push to `origin` only when asked.
- If PLAN.md is ambiguous, pick the simplest option, record it in `DECISIONS.md` (create it if missing), and continue.
- If an install or model download fails, stop and show the exact error. Don't work around it silently.
- Numbers in PROGRESS.md, README and `eval/results/` come from real runs only. Report misses; never hand-fill tables.
- Time is the main risk. If behind, cut in this order: notice OCR → PDF export → voice → shrink eval to 20. Never cut the README or the eval table.

## Files

- `PLAN.md`: design and specs (source of truth)
- `TODO.md`: ordered task checklist
- `PROGRESS.md`: status, measured numbers, blockers, session log
- `DECISIONS.md`: choices made where PLAN.md was ambiguous
