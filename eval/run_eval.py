"""Run the synthetic scenarios through the app's own pipeline and write eval/results/summary.md.

python eval/run_eval.py [--split dev|test|all]     NOCACHE=1 forces fresh LLM calls.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kavach import privacy  # noqa: E402

if __name__ == "__main__":
    privacy.install_offline_guard()

from kavach.config import load_config, resolve  # noqa: E402
from kavach.fusion import fuse, rules_hold  # noqa: E402
from kavach.llm.backend import GenerationResult, LLMBackend, get_backend  # noqa: E402
from kavach.pipeline import run_check  # noqa: E402
from kavach.schemas import Answer, TransactionContext  # noqa: E402

CONFIGS = ["fused", "no_llm", "rules_only", "llm_only", "anomaly_only", "always_medium"]
CONFIG_LABELS = {
    "fused": "Fused (full system)", "no_llm": "Without LLM (rules + transaction, floors, overrides)",
    "rules_only": "Rules only (rule score + hard overrides)", "llm_only": "LLM only",
    "anomaly_only": "Transaction anomaly only", "always_medium": "Baseline: always MEDIUM",
}


class CachingBackend(LLMBackend):
    """Caches generations on disk, keyed by model, messages and generation settings. The model loads lazily."""
    name = "cache"

    def __init__(self, factory, cache_dir: Path | str, model_name: str, enabled: bool = True):
        self._factory, self._inner = factory, None
        self.cache_dir = Path(cache_dir)
        self.model_name = model_name
        self.enabled = enabled
        self.hits = self.misses = 0

    def _path(self, messages, json_schema, max_tokens, temperature) -> Path:
        payload = json.dumps({"model": self.model_name, "messages": messages, "schema": json_schema,
                              "max_tokens": max_tokens, "temperature": temperature},
                             sort_keys=True, ensure_ascii=False)
        return self.cache_dir / f"{hashlib.sha256(payload.encode('utf-8')).hexdigest()}.json"

    def generate(self, messages, json_schema=None, max_tokens=384, temperature=0.1) -> GenerationResult:
        path = self._path(messages, json_schema, max_tokens, temperature)
        if self.enabled and path.exists():
            self.hits += 1
            return GenerationResult.model_validate_json(path.read_text(encoding="utf-8"))
        if self._inner is None:
            self._inner = self._factory()
        out = self._inner.generate(messages, json_schema=json_schema, max_tokens=max_tokens, temperature=temperature)
        self.misses += 1
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out.model_dump_json(), encoding="utf-8")
        return out


def level_of(score: float | None, cfg: dict | None = None) -> str:
    lv = (cfg or load_config())["fusion"]["levels"]
    if score is None:
        return "LOW"
    return "HIGH" if score >= lv["high"] else "MEDIUM" if score >= lv["medium"] else "LOW"


def load_scenarios(split: str) -> list[dict]:
    out = []
    for f in sorted((ROOT / "data" / "scenarios").glob("*.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        if split == "all" or s["split"] == split:
            out.append(s)
    return out


def evaluate_scenario(s: dict, backend: LLMBackend, cfg: dict) -> dict:
    ctx = TransactionContext(**s["transaction"])
    qa = {k: Answer(**v) for k, v in s["answers"].items()}
    notice = s.get("notice_text", "")
    res = run_check(ctx, qa, notice, backend=backend, cfg=cfg)
    a = res.analyzer
    full = res.rules.full_ids()
    rules_level = "HIGH" if any(rules_hold(o, full) for o in cfg["fusion"]["overrides_high"]) \
        else level_of(res.rules.score, cfg)
    levels = {
        "fused": res.risk.level,
        "no_llm": fuse(res.anomaly, res.rules, None, ctx, cfg).level,
        "rules_only": rules_level,
        "llm_only": level_of(a.llm_score, cfg) if a.available else "LOW",
        "anomaly_only": level_of(res.anomaly.score, cfg),
        "always_medium": "MEDIUM",
    }
    t = res.timings
    llm_s = a.stats.seconds if a.attempts else 0.0
    return {
        "id": s["id"], "title": s["title"], "split": s["split"], "language": s["language"],
        "is_scam": s["label"]["is_scam"], "scam_type": s["label"]["scam_type"], "coached": s["label"]["coached"],
        "levels": levels, "score": res.risk.score, "predicted_type": res.risk.scam_type,
        "anomaly": res.anomaly.score, "rules": res.rules.score, "rule_ids": sorted(full),
        "llm_score": a.llm_score, "llm_available": a.available,
        "llm_likelihood": a.assessment.coercion_likelihood if a.assessment else None,
        "attempts": a.attempts, "first_attempt_valid": a.available and a.attempts == 1,
        "kept_flags": len(a.kept_flags), "dropped_flags": a.dropped_flags,
        "overrides": res.risk.overrides_applied, "floors": res.risk.floors_applied,
        "prompt_tokens": a.stats.prompt_tokens, "output_tokens": a.stats.output_tokens,
        "ms": {"anomaly": t["anomaly"] * 1000, "rules": t["rules"] * 1000, "fusion": t["fusion"] * 1000},
        "llm_seconds": llm_s,
        "total_seconds": llm_s + (t["anomaly"] + t["rules"] + t["fusion"]),
    }


def summarize(rows: list[dict], config: str) -> dict:
    scam = [r for r in rows if r["is_scam"]]
    coached = [r for r in scam if r["coached"]]
    genuine = [r for r in rows if not r["is_scam"]]

    def count(group, levels):
        return (sum(r["levels"][config] in levels for r in group), len(group))

    return {
        "scam_medium_plus": count(scam, ("MEDIUM", "HIGH")), "scam_high": count(scam, ("HIGH",)),
        "coached_medium_plus": count(coached, ("MEDIUM", "HIGH")),
        "genuine_high": count(genuine, ("HIGH",)), "genuine_medium_plus": count(genuine, ("MEDIUM", "HIGH")),
    }


def fmt(pair: tuple[int, int]) -> str:
    n, total = pair
    return f"{n}/{total} ({100 * n / total:.0f}%)" if total else "–"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    v = sorted(values)
    return v[max(0, math.ceil(p * len(v)) - 1)]


def why(r: dict) -> str:
    llm = f"LLM {r['llm_likelihood']}" if r["llm_available"] else "LLM unavailable"
    rules = ", ".join(r["rule_ids"]) or "no rule hits"
    extra = "; ".join(filter(None, [", ".join(r["overrides"]), ", ".join(r["floors"])]))
    return (f"score {r['score']:.1f} (anomaly {r['anomaly']}, rules {r['rules']:.0f} [{rules}], {llm})"
            + (f"; fired: {extra}" if extra else ""))


def write_summary(rows: list[dict], cache: CachingBackend, cfg: dict, out_dir: Path) -> Path:
    splits = {"Dev": [r for r in rows if r["split"] == "dev"], "Test": [r for r in rows if r["split"] == "test"],
              f"All {len(rows)}": rows}
    head = {k: summarize(v, "fused") for k, v in splits.items()}
    L = [
        "# Evaluation results",
        "",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} · model `{cache.model_name}` · {len(rows)} synthetic scenarios "
        f"(author-written, LLM-drafted, not real complaints) · LLM cache hits {cache.hits}, fresh calls {cache.misses}.",
        "",
        "## Headline (fused system)",
        "",
        "| Metric | Target | " + " | ".join(splits) + " |",
        "|---|---|" + "---|" * len(splits),
    ]
    targets = {"scam_medium_plus": "≥ 90%", "scam_high": "report", "coached_medium_plus": "report",
               "genuine_high": "≤ 10%", "genuine_medium_plus": "≤ 30%"}
    names = {"scam_medium_plus": "Scams flagged MEDIUM or HIGH (recall)", "scam_high": "Scams flagged HIGH",
             "coached_medium_plus": "Coached scams flagged MEDIUM or HIGH",
             "genuine_high": "Genuine flagged HIGH (false alarms)",
             "genuine_medium_plus": "Genuine flagged MEDIUM or HIGH"}
    for key, name in names.items():
        L.append(f"| {name} | {targets[key]} | " + " | ".join(fmt(head[s][key]) for s in splits) + " |")

    L += ["", f"## Ablation (all {len(rows)})", "",
          "| Configuration | Scam MEDIUM+ | Scam HIGH | Coached MEDIUM+ | Genuine HIGH | Genuine MEDIUM+ |",
          "|---|---|---|---|---|---|"]
    for c in CONFIGS:
        s = summarize(rows, c)
        L.append(f"| {CONFIG_LABELS[c]} | " + " | ".join(fmt(s[k]) for k in names) + " |")

    llm_rows = [r for r in rows if r["attempts"]]
    L += ["", "## LLM output", "",
          f"- Valid JSON on the first attempt: {fmt((sum(r['first_attempt_valid'] for r in rows), len(rows)))}",
          f"- LLM result available (after at most one retry): {fmt((sum(r['llm_available'] for r in rows), len(rows)))}",
          f"- Evidence-guard: {sum(r['kept_flags'] for r in rows)} quotes kept, "
          f"{sum(r['dropped_flags'] for r in rows)} dropped",
          "", "## Latency per check (machine time, excluding speech-to-text)", "",
          "| Stage | p50 | p95 |", "|---|---|---|"]
    for stage in ("anomaly", "rules", "fusion"):
        vals = [r["ms"][stage] for r in rows]
        L.append(f"| {stage} (ms) | {percentile(vals, .5):.2f} | {percentile(vals, .95):.2f} |")
    llm_s = [r["llm_seconds"] for r in llm_rows]
    L.append(f"| LLM (s, as generated) | {percentile(llm_s, .5):.1f} | {percentile(llm_s, .95):.1f} |")
    tot = [r["total_seconds"] for r in rows]
    L.append(f"| Total (s) | {percentile(tot, .5):.1f} | {percentile(tot, .95):.1f} |")
    L += ["", "LLM timings are from the run that generated each cached result; `python tasks.py bench` measures "
          "fresh calls with energy.", "", "## Misses", ""]
    misses = ([("Scam flagged LOW", r) for r in rows if r["is_scam"] and r["levels"]["fused"] == "LOW"]
              + [("Genuine flagged HIGH", r) for r in rows if not r["is_scam"] and r["levels"]["fused"] == "HIGH"]
              + [("Genuine flagged MEDIUM", r) for r in rows if not r["is_scam"] and r["levels"]["fused"] == "MEDIUM"])
    L += [f"- **{kind}** `{r['id']}` ({r['split']}, {r['title']}): {why(r)}" for kind, r in misses] or ["- None"]
    L += ["", "## Per scenario", "",
          "| id | split | label | coached | level | score | anomaly | rules | LLM | overrides / floors |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        label = r["scam_type"] or "genuine"
        llm = r["llm_likelihood"] or "n/a"
        fired = ", ".join(r["overrides"] + r["floors"]) or "–"
        L.append(f"| {r['id']} | {r['split']} | {label} | {'yes' if r['coached'] else ''} | {r['levels']['fused']} "
                 f"| {r['score']:.1f} | {r['anomaly']} | {r['rules']:.0f} | {llm} | {fired} |")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "summary.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="all", choices=["dev", "test", "all"])
    args = ap.parse_args()
    cfg = load_config()
    m = cfg["models"]
    model_name = Path(m["llm_fallback_path"] if m.get("use_fallback") else m["llm_path"]).name
    cache = CachingBackend(lambda: get_backend(cfg), resolve(cfg["eval"]["llm_cache_dir"]), model_name,
                           enabled=os.environ.get("NOCACHE", "0") != "1")
    rows = []
    scenarios = load_scenarios(args.split)
    for i, s in enumerate(scenarios, 1):
        r = evaluate_scenario(s, cache, cfg)
        rows.append(r)
        print(f"[{i}/{len(scenarios)}] {r['id']:7s} {'scam' if r['is_scam'] else 'gen ':4s} -> {r['levels']['fused']:6s} "
              f"score {r['score']:5.1f} llm {r['llm_likelihood'] or 'n/a':6s} {r['llm_seconds']:5.1f}s", flush=True)
    out_dir = resolve(cfg["eval"]["results_dir"])
    path = write_summary(rows, cache, cfg, out_dir)
    (out_dir / "results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {path}")
    head = summarize(rows, "fused")
    print("recall", fmt(head["scam_medium_plus"]), "| genuine HIGH", fmt(head["genuine_high"]),
          "| genuine MEDIUM+", fmt(head["genuine_medium_plus"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
