import os
from abc import ABC, abstractmethod

import psutil
from pydantic import BaseModel

from kavach.config import load_config, resolve
from kavach.schemas import GenerationStats


class GenerationResult(BaseModel):
    text: str
    stats: GenerationStats


class LLMBackend(ABC):
    """All inference goes through this interface, so the Phase 2 Kompact port changes one file."""
    name: str = "base"
    model_name: str = ""

    @abstractmethod
    def generate(self, messages: list[dict], json_schema: dict | None = None,
                 max_tokens: int = 384, temperature: float = 0.1) -> GenerationResult: ...


def physical_cores() -> int:
    return psutil.cpu_count(logical=False) or os.cpu_count() or 4


def get_backend(cfg: dict | None = None) -> LLMBackend:
    cfg = cfg or load_config()
    m, llm = cfg["models"], cfg["llm"]
    path = resolve(m["llm_fallback_path"] if m.get("use_fallback") else m["llm_path"])
    threads = physical_cores() if llm["n_threads"] == "auto" else int(llm["n_threads"])
    from kavach.llm.llamacpp_backend import LlamaCppBackend
    return LlamaCppBackend(path, n_ctx=llm["n_ctx"], n_threads=threads, chat_format=llm["chat_format"])
