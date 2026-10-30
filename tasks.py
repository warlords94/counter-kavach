"""Cross-platform task runner: python tasks.py <setup|models|run|test|eval|bench|smoke> [extra args].

Extra arguments go to the task's command, e.g. python tasks.py run --server.port 8502
"""
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
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print(f"usage: python tasks.py <{'|'.join(TASKS)}> [extra args]")
        return 2
    task, extra = sys.argv[1], sys.argv[2:]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    if task in ("run", "eval", "bench"):
        env.setdefault("OFFLINE", "1")
    for cmd in TASKS[task]:
        code = subprocess.call(cmd + extra, cwd=ROOT, env=env)
        if code:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
