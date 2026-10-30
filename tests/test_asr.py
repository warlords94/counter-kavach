import io
import wave

import pytest

from kavach.asr import needs_typing
from kavach.config import load_config, resolve
from kavach.schemas import Transcript

WHISPER = resolve(load_config()["models"]["whisper_dir"])


def t(text="नमस्ते", logprob=-0.4, seconds=2.0):
    return Transcript(text=text, language="hi", avg_logprob=logprob, seconds=seconds)


def test_good_transcript_is_accepted():
    assert not needs_typing(t())


def test_slow_low_confidence_or_empty_transcript_asks_staff_to_type():
    assert needs_typing(t(seconds=12))
    assert needs_typing(t(logprob=-1.4))
    assert needs_typing(t(text="  "))


def silent_wav(seconds=1.0, rate=16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


@pytest.mark.llm
@pytest.mark.skipif(not (WHISPER / "model.bin").exists(), reason="Whisper model not downloaded")
def test_silence_transcribes_to_nothing_and_asks_to_type():
    from kavach.asr import ASR
    tr = ASR().transcribe(silent_wav(), "hi")
    assert tr.text.strip() == "" and needs_typing(tr)
