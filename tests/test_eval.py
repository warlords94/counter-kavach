from eval.run_eval import CachingBackend, level_of, summarize
from kavach.llm.backend import GenerationResult, LLMBackend
from kavach.schemas import GenerationStats


class CountingBackend(LLMBackend):
    name = "count"
    model_name = "m.gguf"

    def __init__(self):
        self.calls = 0

    def generate(self, messages, json_schema=None, max_tokens=384, temperature=0.1):
        self.calls += 1
        return GenerationResult(text='{"x": 1}', stats=GenerationStats(output_tokens=3, seconds=2.0))


def test_cache_hit_skips_the_model(tmp_path):
    inner = CountingBackend()
    b = CachingBackend(lambda: inner, tmp_path, model_name="m.gguf")
    msgs = [{"role": "user", "content": "hi"}]
    first, second = b.generate(msgs), b.generate(msgs)
    assert inner.calls == 1 and first.text == second.text and second.stats.seconds == 2.0
    assert b.hits == 1 and b.misses == 1


def test_cache_key_depends_on_schema(tmp_path):
    inner = CountingBackend()
    b = CachingBackend(lambda: inner, tmp_path, model_name="m.gguf")
    msgs = [{"role": "user", "content": "hi"}]
    b.generate(msgs)
    b.generate(msgs, json_schema={"type": "object"})
    assert inner.calls == 2


def test_level_thresholds():
    assert [level_of(s) for s in (34.9, 35, 64.9, 65)] == ["LOW", "MEDIUM", "MEDIUM", "HIGH"]


def row(is_scam, level, coached=False, split="dev"):
    return {"id": "x", "split": split, "is_scam": is_scam, "coached": coached, "levels": {"fused": level}}


def test_summarize_counts_recall_and_false_alarms():
    rows = [row(True, "HIGH"), row(True, "MEDIUM", coached=True), row(True, "LOW"),
            row(False, "LOW"), row(False, "MEDIUM"), row(False, "HIGH")]
    s = summarize(rows, "fused")
    assert s["scam_medium_plus"] == (2, 3) and s["scam_high"] == (1, 3)
    assert s["coached_medium_plus"] == (1, 1)
    assert s["genuine_high"] == (1, 3) and s["genuine_medium_plus"] == (2, 3)
