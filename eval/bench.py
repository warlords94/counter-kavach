"""CPU benchmark: fresh LLM calls (no cache) on the test split, with per-check energy. Writes eval/results/bench.md.

Run nothing else heavy while it runs; the numbers are only as clean as the machine is idle.
"""
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kavach import privacy  # noqa: E402

privacy.install_offline_guard()

from eval.run_eval import load_scenarios, percentile  # noqa: E402
from kavach.config import load_config, resolve  # noqa: E402
from kavach.llm.backend import get_backend  # noqa: E402
from kavach.metrics import system_info  # noqa: E402
from kavach.pipeline import run_check  # noqa: E402
from kavach.schemas import Answer, TransactionContext  # noqa: E402


def check(s: dict, backend, cfg: dict):
    ctx = TransactionContext(**s["transaction"])
    qa = {k: Answer(**v) for k, v in s["answers"].items()}
    return run_check(ctx, qa, s.get("notice_text", ""), backend=backend, cfg=cfg)


def main() -> int:
    cfg = load_config()
    info = system_info()
    t0 = perf_counter()
    backend = get_backend(cfg)
    load_s = perf_counter() - t0
    scenarios = load_scenarios("test")
    warm = check(load_scenarios("dev")[0], backend, cfg)  # first check fills the system-prompt KV cache
    print(f"warm-up {warm.total_seconds:.1f}s (excluded)", flush=True)

    rows = []
    for i, s in enumerate(scenarios, 1):
        r = check(s, backend, cfg)
        st = r.analyzer.stats
        rows.append({"id": s["id"], "total_s": r.total_seconds, "llm_s": r.timings["llm"],
                     "prompt_tokens": st.prompt_tokens, "prompt_eval_tokens": st.prompt_eval_tokens,
                     "prompt_s": st.prompt_seconds, "output_tokens": st.output_tokens, "gen_s": st.gen_seconds,
                     "attempts": r.analyzer.attempts, "joules": r.energy_joules, "energy_kind": r.energy_kind,
                     "level": r.risk.level})
        print(f"[{i}/{len(scenarios)}] {s['id']:7s} {r.total_seconds:5.1f}s  out {st.output_tokens:3d} tok  "
              f"{r.energy_joules:6.0f} J ({r.energy_kind})", flush=True)

    total = [r["total_s"] for r in rows]
    llm = [r["llm_s"] for r in rows]
    gen_rates = [r["output_tokens"] / r["gen_s"] for r in rows if r["gen_s"]]
    pp_rates = [r["prompt_eval_tokens"] / r["prompt_s"] for r in rows
                if r["prompt_s"] and r["prompt_eval_tokens"] and r["prompt_eval_tokens"] > 1]
    joules = [r["joules"] for r in rows if r["joules"] is not None]
    kinds = {r["energy_kind"] for r in rows}
    m = cfg["models"]
    model = Path(m["llm_fallback_path"] if m.get("use_fallback") else m["llm_path"]).name
    mean_j = statistics.mean(joules) if joules else float("nan")
    lines = [
        "# CPU benchmark", "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} · {len(rows)} test-split scenarios · fresh LLM calls (no cache) · "
        "model kept loaded and system prompt cached, as in the app.", "",
        "| Item | Value |", "|---|---|",
        f"| OS | {info['os']} |",
        f"| CPU | {info['cpu']} ({info['physical_cores']} cores / {info['logical_cores']} threads), no GPU |",
        f"| RAM | {info['ram_gb']} GB |",
        f"| Model | {model} |",
        f"| Runtime | llama.cpp via llama-cpp-python, {getattr(backend, 'n_threads', '?')} threads |",
        f"| Model load | {load_s:.1f} s (once per app start) |",
        f"| Latency per check, p50 / p95 | {percentile(total, .5):.1f} s / {percentile(total, .95):.1f} s |",
        f"| LLM step, p50 / p95 | {percentile(llm, .5):.1f} s / {percentile(llm, .95):.1f} s |",
        f"| Prompt processing | {statistics.median(pp_rates):.1f} tokens/s (median) |" if pp_rates else
        "| Prompt processing | n/a |",
        f"| Generation | {statistics.median(gen_rates):.1f} tokens/s (median) |" if gen_rates else "| Generation | n/a |",
        f"| Energy per check | {mean_j:.0f} J mean, {percentile(joules, .5):.0f} J p50 ({', '.join(sorted(kinds))}) |",
        f"| Energy per 1,000 checks | {mean_j * 1000 / 3600:.1f} Wh ({', '.join(sorted(kinds))}) |",
        "",
        "Energy is **estimated** (average CPU utilisation × configured TDP × time) unless the kind says measured "
        "(RAPL, Linux only).",
        "", "| id | total s | LLM s | output tokens | attempts | J | level |", "|---|---|---|---|---|---|---|",
    ]
    lines += [f"| {r['id']} | {r['total_s']:.1f} | {r['llm_s']:.1f} | {r['output_tokens']} | {r['attempts']} | "
              f"{r['joules']:.0f} | {r['level']} |" for r in rows]
    out = resolve(cfg["eval"]["results_dir"])
    out.mkdir(parents=True, exist_ok=True)
    (out / "bench.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "bench.json").write_text(json.dumps({"system": info, "model": model, "rows": rows}, indent=1),
                                    encoding="utf-8")
    print("\n".join(lines[4:17]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
