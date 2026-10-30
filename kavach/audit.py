"""Append-only audit log with a SHA-256 hash chain, plus retention cleanup of var/."""
import hashlib
import json
import time
from pathlib import Path

from kavach.config import resolve

GENESIS = "0" * 64
FIELDS = ("id", "timestamp", "branch", "staff_name", "officer_name", "customer_ref", "txn_type", "amount_inr",
          "level", "score", "scam_type", "overrides", "floors", "action_taken", "suspected_fraud", "llm_available")


def _digest(record: dict) -> str:
    body = {k: v for k, v in record.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append(note, path: Path | str | None = None) -> dict:
    """Store a summary of the (already masked) incident note; the Q&A stays only in the report files."""
    path = resolve(path or "var/audit.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _records(path)
    record = {k: getattr(note, k) for k in FIELDS}
    record["prev_hash"] = records[-1]["hash"] if records else GENESIS
    record["hash"] = _digest(record)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def verify_chain(path: Path | str) -> bool:
    prev = GENESIS
    for rec in _records(resolve(path)):
        if rec.get("prev_hash") != prev or rec.get("hash") != _digest(rec):
            return False
        prev = rec["hash"]
    return True


def purge_older_than(directory: Path | str, days: int) -> int:
    cutoff = time.time() - days * 86400
    removed = 0
    for f in resolve(directory).rglob("*"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    return removed
