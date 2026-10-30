import json

import pytest

from kavach.analyzer import ANALYZER_SCHEMA
from kavach.config import load_config, resolve
from kavach.llm.backend import get_backend
from kavach.llm.kompact_backend import KompactBackend
from kavach.schemas import LLMAssessment

MODEL = resolve(load_config()["models"]["llm_path"])


def test_kompact_backend_is_a_stub():
    with pytest.raises(NotImplementedError):
        KompactBackend().generate([{"role": "user", "content": "hi"}])


@pytest.mark.llm
@pytest.mark.skipif(not MODEL.exists(), reason="LLM model not downloaded (python tasks.py models)")
def test_llamacpp_backend_returns_schema_valid_json():
    backend = get_backend()
    msgs = [{"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": "Customer says: a CBI officer on video call told me to move money "
                                        "to a safe RBI account. Assess coercion."}]
    out = backend.generate(msgs, json_schema=ANALYZER_SCHEMA, max_tokens=256, temperature=0.1)
    LLMAssessment.model_validate(json.loads(out.text))
    assert out.stats.output_tokens > 0 and out.stats.seconds > 0
