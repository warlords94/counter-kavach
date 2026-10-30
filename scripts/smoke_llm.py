"""M1 smoke test: run the real analyzer prompt on demo scenario 1 and apply the model choice rule."""
import json
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kavach import privacy  # noqa: E402

privacy.install_offline_guard()

from kavach.analyzer import analyze  # noqa: E402
from kavach.config import ROOT, load_config, resolve  # noqa: E402
from kavach.llm.backend import get_backend  # noqa: E402
from kavach.schemas import Answer, TransactionContext  # noqa: E402


def rate(tokens: int, seconds: float | None) -> str:
    return f"{tokens / seconds:.1f} tok/s" if seconds else "n/a"


def main() -> int:
    cfg = load_config()
    s = json.loads((ROOT / "data" / "scenarios" / "da_01.json").read_text(encoding="utf-8"))
    ctx = TransactionContext(**s["transaction"])
    qa = {k: Answer(**v) for k, v in s["answers"].items()}

    t0 = perf_counter()
    backend = get_backend(cfg)
    print(f"model {backend.model_name} | threads {backend.n_threads} | load {perf_counter() - t0:.1f}s")

    runs = []
    for label in ("cold (first check after load)", "warm (same prompt, KV cache reused)"):
        r = analyze(backend, ctx, qa, cfg=cfg)
        st = r.stats
        runs.append({"label": label, "available": r.available, "attempts": r.attempts, **st.model_dump()})
        print(f"{label}: {st.seconds:.1f}s total | prompt {st.prompt_tokens} tok, "
              f"{rate(st.prompt_tokens, st.prompt_seconds)} | output {st.output_tokens} tok, "
              f"{rate(st.output_tokens, st.gen_seconds)} | attempts {r.attempts}")
    if not r.available:
        print(f"LLM unavailable: {r.error}")
        return 1
    print(json.dumps(r.assessment.model_dump(), ensure_ascii=False, indent=2))
    print(f"evidence kept {len(r.kept_flags)}, dropped {r.dropped_flags}, llm_score {r.llm_score}")

    limit = cfg["llm"]["smoke_max_seconds"]
    cold = runs[0]["seconds"]
    verdict = "keep" if cold <= limit else "switch to fallback (models.use_fallback: true)"
    print(f"model choice rule: cold LLM step {cold:.1f}s vs limit {limit}s -> {verdict}")

    out = resolve("var/smoke_result.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"model": backend.model_name, "threads": backend.n_threads, "runs": runs,
                               "verdict": verdict}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
