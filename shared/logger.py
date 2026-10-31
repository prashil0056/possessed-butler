import json
import os
from datetime import datetime, timezone


def log_jsonl(path: str, record: dict) -> None:
    """Append a JSON line to a file, with a UTC timestamp added."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    enriched = {"timestamp": datetime.now(timezone.utc).isoformat(), **record}

    with open(path, "a") as f:
        f.write(json.dumps(enriched) + "\n")


def read_jsonl(path: str) -> list:
    """Read all JSON lines from a file. Returns list of dicts."""
    if not os.path.exists(path):
        return []

    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def count_breaches(records: list) -> dict:
    """Summarize breach counts from a list of attack result records."""
    total = len(records)
    successes = sum(1 for r in records if r.get("success"))
    by_technique = {}
    for r in records:
        tech = r.get("technique", "unknown")
        by_technique.setdefault(tech, {"total": 0, "success": 0})
        by_technique[tech]["total"] += 1
        if r.get("success"):
            by_technique[tech]["success"] += 1

    return {
        "total": total,
        "successes": successes,
        "asr": successes / total if total else 0.0,
        "by_technique": by_technique,
    }