from pathlib import Path
from time import perf_counter

from kavach.llm.backend import GenerationResult, LLMBackend
from kavach.schemas import GenerationStats


class LlamaCppBackend(LLMBackend):
    name = "llama.cpp"

    def __init__(self, model_path: Path, n_ctx: int = 4096, n_threads: int | None = None,
                 chat_format: str = "chatml", seed: int = 42):
        from llama_cpp import Llama

        if not Path(model_path).exists():
            raise FileNotFoundError(f"LLM model not found: {model_path} (run: python tasks.py models)")
        self.model_name = Path(model_path).name
        self.n_threads = n_threads
        self.llm = Llama(model_path=str(model_path), n_ctx=n_ctx, n_threads=n_threads,
                         chat_format=chat_format, seed=seed, verbose=False)

    def _perf(self, reset: bool = False) -> tuple[float | None, float | None, int | None]:
        """Prompt-eval seconds, generation seconds and evaluated prompt tokens from llama.cpp (best effort)."""
        try:
            import llama_cpp
            ctx = self.llm._ctx.ctx
            if reset:
                llama_cpp.llama_perf_context_reset(ctx)
                return None, None, None
            d = llama_cpp.llama_perf_context(ctx)
            return d.t_p_eval_ms / 1000, d.t_eval_ms / 1000, d.n_p_eval
        except Exception:
            return None, None, None

    def generate(self, messages: list[dict], json_schema: dict | None = None,
                 max_tokens: int = 384, temperature: float = 0.1) -> GenerationResult:
        kwargs = {}
        if json_schema is not None:
            kwargs["response_format"] = {"type": "json_object", "schema": json_schema}
        self._perf(reset=True)
        t0 = perf_counter()
        out = self.llm.create_chat_completion(messages=messages, max_tokens=max_tokens,
                                              temperature=temperature, **kwargs)
        seconds = perf_counter() - t0
        prompt_s, gen_s, prompt_n = self._perf()
        usage = out.get("usage") or {}
        return GenerationResult(
            text=out["choices"][0]["message"]["content"] or "",
            stats=GenerationStats(prompt_tokens=usage.get("prompt_tokens", 0),
                                  output_tokens=usage.get("completion_tokens", 0),
                                  seconds=seconds, prompt_seconds=prompt_s, prompt_eval_tokens=prompt_n,
                                  gen_seconds=gen_s),
        )
