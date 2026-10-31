from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import hashlib
import yaml
from harness.butler_sim import ButlerSim
from harness.judge import Judge
from shared.logger import log_jsonl


def load_payloads(path: str) -> list:
    """Load a JSON payload file. Expects [{"technique": str, "payload": str}, ...]."""
    with open(path) as f:
        return json.load(f)


def run_attack_set(config_path: str, payloads_path: str, output_log: str) -> dict:
    """Run all payloads from payloads_path against the butler in config_path.
    Logs each result. Returns summary dict."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    butler = ButlerSim(config_path)
    judge = Judge(
        canary_tokens=cfg.get("canary_tokens", []),
        forbidden_tools=cfg.get("forbidden_tools", []),
        secret_phrases=cfg.get("secret_phrases", []),
    )

    payloads = load_payloads(payloads_path)
    results = []

    for i, p in enumerate(payloads, start=1):
        payload_text = p["payload"]
        technique = p.get("technique", "unknown")

        try:
            out = butler.respond(payload_text)
        except Exception as e:
            print(f"[runner] [{i}/{len(payloads)}] ERROR on {technique}: {e}")
            continue

        breached, breach_type = judge.is_breached(out)
        payload_hash = hashlib.sha256(payload_text.encode()).hexdigest()[:12]

        record = {
            "payload_hash": payload_hash,
            "technique": technique,
            "target_config": config_path,
            "success": breached,
            "breach_type": breach_type,
            "response_snippet": out["response"][:200],
        }
        results.append(record)
        log_jsonl(output_log, record)

        status = "HIT" if breached else "miss"
        print(f"[runner] [{i}/{len(payloads)}] {technique}: {status} ({breach_type})")

    total = len(results)
    hits = sum(1 for r in results if r["success"])
    asr = hits / total if total else 0.0

    by_technique = {}
    for r in results:
        t = r["technique"]
        by_technique.setdefault(t, {"total": 0, "hits": 0})
        by_technique[t]["total"] += 1
        if r["success"]:
            by_technique[t]["hits"] += 1

    summary = {
        "total": total,
        "hits": hits,
        "asr": asr,
        "by_technique": by_technique,
        "output_log": output_log,
    }

    print()
    print(f"[runner] {hits}/{total} breached ({asr * 100:.1f}% ASR)")
    print("[runner] by technique:")
    for t, s in by_technique.items():
        rate = s["hits"] / s["total"] if s["total"] else 0.0
        print(f"  {t:32s} {s['hits']}/{s['total']} ({rate * 100:.1f}%)")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run attack payloads against a butler config.")
    parser.add_argument("--config", required=True, help="Path to butler YAML config")
    parser.add_argument("--payloads", required=True, help="Path to JSON payload file")
    parser.add_argument("--output", default="results/attack_runs/run.jsonl",
                        help="Path to JSONL output log")
    args = parser.parse_args()

    run_attack_set(args.config, args.payloads, args.output)


if __name__ == "__main__":
    main()