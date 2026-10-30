"""Small display helpers. Anything user-typed is HTML-escaped before it goes into markup."""
import html

import streamlit as st

from kavach.report import SCAM_LABELS

LEVEL_COLORS = {"LOW": "#2e7d32", "MEDIUM": "#a35f00", "HIGH": "#c62828"}
SOURCE_COLORS = {"Transaction": "#455a64", "Answer": "#1565c0", "Rule": "#6a1b9a", "LLM": "#00695c",
                 "Notice": "#8d6e63"}
LEVEL_HI = {"LOW": "कम", "MEDIUM": "मध्यम", "HIGH": "उच्च"}


def chip(text: str, color: str) -> str:
    return (f"<span style='background:{color};color:#fff;padding:1px 8px;border-radius:10px;"
            f"font-size:0.75rem;font-weight:600;margin-right:6px'>{html.escape(text)}</span>")


def offline_badge(active: bool) -> None:
    color, label = ("#2e7d32", "● Offline: network blocked") if active else ("#a35f00", "● Network guard off")
    st.markdown(chip(label, color), unsafe_allow_html=True)


def risk_badge(level: str, score: float, scam_type: str, lang: str, preliminary: bool) -> None:
    sub = "preliminary · rules + transaction, LLM still running" if preliminary else SCAM_LABELS[scam_type]
    level_text = f"{level} · {LEVEL_HI[level]}" if lang == "hi" else level
    st.markdown(
        f"<div style='background:{LEVEL_COLORS[level]};color:#fff;padding:10px 16px;border-radius:10px'>"
        f"<span style='font-size:1.9rem;font-weight:800'>{level_text}</span>"
        f"<span style='font-size:1rem;margin-left:12px'>score {score:.0f} · {html.escape(sub)}</span></div>",
        unsafe_allow_html=True)


def evidence_list(items) -> None:
    for e in items:
        st.markdown(chip(e.source, SOURCE_COLORS.get(e.source, "#555")) + html.escape(e.text),
                    unsafe_allow_html=True)


def metrics_panel(result, asr_times: list[float]) -> None:
    t = result.timings
    a = result.analyzer
    rows = [f"| anomaly | {t.get('anomaly', 0) * 1000:.1f} ms |", f"| rules | {t.get('rules', 0) * 1000:.1f} ms |"]
    if asr_times:
        rows.append(f"| speech to text | {sum(asr_times):.1f} s ({len(asr_times)} clips) |")
    rows.append(f"| LLM | {t.get('llm', 0):.1f} s |")
    rows.append(f"| **total** | **{result.total_seconds + sum(asr_times):.1f} s** |")
    st.markdown("| stage | time |\n|---|---|\n" + "\n".join(rows))
    if a.available and a.stats.output_tokens:
        gen = a.stats.gen_seconds or a.stats.seconds
        st.caption(f"{a.stats.prompt_tokens} prompt + {a.stats.output_tokens} output tokens · "
                   f"{a.stats.output_tokens / gen:.1f} tokens/s generation")
    if result.energy_joules is not None:
        st.caption(f"Energy: {result.energy_joules:.0f} J per check ({result.energy_kind})")
