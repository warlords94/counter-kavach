import io
from time import perf_counter

from kavach.config import load_config, resolve
from kavach.llm.backend import physical_cores
from kavach.schemas import Transcript


class ASR:
    """faster-whisper from a local directory (never a Hub name), CPU int8, VAD on. Audio stays in memory."""

    def __init__(self, cfg: dict | None = None):
        from faster_whisper import WhisperModel

        cfg = cfg or load_config()
        model_dir = resolve(cfg["models"]["whisper_dir"])
        if not (model_dir / "model.bin").exists():
            raise FileNotFoundError(f"Whisper model not found in {model_dir} (run: python tasks.py models)")
        self.name = f"faster-whisper {model_dir.name} ({cfg['asr']['compute_type']})"
        self.model = WhisperModel(str(model_dir), device="cpu", compute_type=cfg["asr"]["compute_type"],
                                  cpu_threads=physical_cores())

    def transcribe(self, audio: bytes, language: str) -> Transcript:
        t0 = perf_counter()
        segments, info = self.model.transcribe(io.BytesIO(audio), language=language, vad_filter=True, beam_size=1)
        segs = list(segments)
        text = " ".join(s.text.strip() for s in segs).strip()
        weight = sum(max(s.end - s.start, 1e-3) for s in segs)
        logprob = (sum(s.avg_logprob * max(s.end - s.start, 1e-3) for s in segs) / weight) if segs else -10.0
        return Transcript(text=text, language=info.language or language, avg_logprob=round(logprob, 3),
                          seconds=round(perf_counter() - t0, 2))


def needs_typing(t: Transcript, cfg: dict | None = None) -> bool:
    """Ask staff to type instead when transcription was slow, low-confidence or empty."""
    a = (cfg or load_config())["asr"]
    return t.seconds > a["max_clip_seconds"] or t.avg_logprob < a["min_avg_logprob"] or not t.text.strip()
