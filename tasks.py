"""Cross-platform task runner: python tasks.py <setup|models|run|test|eval|bench|smoke>."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = [sys.executable, "-X", "utf8"]

TASKS = {
    "setup": [PY + ["-m", "pip", "install", "-r", "requirements.txt"]],
    "models": [PY + ["scripts/download_models.py"]],
    "run": [PY + ["-m", "streamlit", "run", "app/main.py"]],
    "test": [PY + ["-m", "pytest", "-q"]],
    "eval": [PY + ["eval/run_eval.py"]],
    "bench": [PY + ["eval/bench.py"]],
    "smoke": [PY + ["scripts/smoke_llm.py"]],
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in TASKS:
        print(f"usage: python tasks.py <{'|'.join(TASKS)}>")
        return 2
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    if sys.argv[1] in ("run", "eval", "bench"):
        env.setdefault("OFFLINE", "1")
    for cmd in TASKS[sys.argv[1]]:
        code = subprocess.call(cmd, cwd=ROOT, env=env)
        if code:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
