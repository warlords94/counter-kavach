"""Download the GGUF LLMs and the Whisper model into models/. The only script allowed to use the network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from huggingface_hub import hf_hub_download, snapshot_download  # noqa: E402

from kavach.config import load_config, resolve  # noqa: E402


def fetch_gguf(spec: dict, target: Path) -> None:
    if target.exists():
        print(f"ok      {target} (already present)")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetch   {spec['repo']}/{spec['file']}")
    path = hf_hub_download(repo_id=spec["repo"], filename=spec["file"], local_dir=target.parent)
    Path(path).rename(target) if Path(path) != target else None
    print(f"ok      {target} ({target.stat().st_size / 1e9:.2f} GB)")


def main() -> int:
    cfg = load_config()["models"]
    dl = cfg["downloads"]
    only = set(sys.argv[1:])  # optional: llm llm_fallback whisper
    if not only or "llm" in only:
        fetch_gguf(dl["llm"], resolve(cfg["llm_path"]))
    if not only or "llm_fallback" in only:
        fetch_gguf(dl["llm_fallback"], resolve(cfg["llm_fallback_path"]))
    if not only or "whisper" in only:
        target = resolve(cfg["whisper_dir"])
        if (target / "model.bin").exists():
            print(f"ok      {target} (already present)")
        else:
            print(f"fetch   {dl['whisper']['repo']}")
            snapshot_download(repo_id=dl["whisper"]["repo"], local_dir=target)
            print(f"ok      {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
