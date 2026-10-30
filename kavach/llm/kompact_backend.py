from kavach.llm.backend import GenerationResult, LLMBackend


class KompactBackend(LLMBackend):
    """Phase 2: Kompact AI Runtime. Stub until finalists receive runtime access."""
    name = "kompact"

    def __init__(self, *args, **kwargs):
        self.model_name = kwargs.get("model_name", "")

    def generate(self, messages: list[dict], json_schema: dict | None = None,
                 max_tokens: int = 384, temperature: float = 0.1) -> GenerationResult:
        raise NotImplementedError("Kompact AI Runtime backend is Phase 2")
