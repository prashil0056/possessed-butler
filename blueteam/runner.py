import argparse
import hashlib
import json
from dotenv import load_dotenv

load_dotenv()

from blueteam.pipeline import DefensePipeline
from harness.butler_sim import ButlerSim
from shared.logger import log_jsonl


def run_defense_set(
    butler_config: str,
    defense_config: str,
    payloads_path: str,
    output_log: str,
) -> dict:
    """Run all payloads through the defense pipeline against a butler config."""
    pipeline = DefensePipeline(defense_config)
    butler = ButlerSim(butler_config)

    def butler_fn(wrapped):
        return butler.respond(wrapped)

    with open(payloads_path) as f:
        payloads = json.load(f)

    results = []
    for i, p in enumerate(payloads, 1):
        payload_text = p["payload"]
        technique = p.get("technique", "unknown")

        r = pipeline.protect(payload_text, butler_fn)

        payload_hash = hashlib.sha256(payload_text.encode()).hexdigest()[:12]
        record = {
            "payload_hash": payload_hash,
            "technique": technique,
            "blocked": r["blocked"],
            "block_layer": r.get("block_layer"),
            "reason": r["reason"],
            "target_config": butler_config,
        }
        results.append(record)
        log_jsonl(output_log, record)

        status = "BLOCKED" if r["blocked"] else "passed"
        layer = r.get("block_layer") or "-"
        print(f"[{i}/{len(payloads)}] {technique:32s} {status:8s} {layer:8s} {r['reason'][:60]}")

    total = len(results)
    blocked = sum(1 for r in results if r["blocked"])
    block_rate = blocked / total if total else 0.0

    by_tech = {}
    by_layer = {}
    for r in results:
        t = r["technique"]
        by_tech.setdefault(t, {"total": 0, "blocked": 0})
        by_tech[t]["total"] += 1
        if r["blocked"]:
            by_tech[t]["blocked"] += 1
            layer = r.get("block_layer") or "unknown"
            by_layer[layer] = by_layer.get(layer, 0) + 1

    summary = {
        "total": total,
        "blocked": blocked,
        "passed": total - blocked,
        "block_rate": block_rate,
        "by_technique": by_tech,
        "by_layer": by_layer,
        "output_log": output_log,
    }

    print()
    print(f"[defense_runner] {blocked}/{total} blocked ({block_rate * 100:.1f}%)")
    print("[defense_runner] by technique:")
    for t, s in sorted(by_tech.items()):
        rate = s["blocked"] / s["total"] * 100 if s["total"] else 0.0
        print(f"  {t:32s} {s['blocked']}/{s['total']} ({rate:.1f}%)")
    print("[defense_runner] by layer:")
    for layer, count in sorted(by_layer.items()):
        print(f"  {layer:16s} {count}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run attack payloads through the defense pipeline.")
    parser.add_argument("--butler-config", required=True, help="Butler YAML config path")
    parser.add_argument("--defense-config", default="blueteam/configs/defense.yaml",
                        help="Defense pipeline config path")
    parser.add_argument("--payloads", required=True, help="JSON payload file")
    parser.add_argument("--output", default="results/defense_runs/defense.jsonl",
                        help="JSONL output log")
    args = parser.parse_args()

    run_defense_set(args.butler_config, args.defense_config, args.payloads, args.output)


if __name__ == "__main__":
    main()
