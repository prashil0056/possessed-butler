import argparse
from dotenv import load_dotenv

load_dotenv()

from harness.runner import run_attack_set


def main():
    parser = argparse.ArgumentParser(description="Red-team attack tester. Wraps harness.runner.")
    parser.add_argument("--config", required=True, help="Butler YAML config path")
    parser.add_argument("--payloads", required=True, help="JSON payload file")
    parser.add_argument("--output", default="results/attack_runs/redteam.jsonl",
                        help="JSONL output log")
    args = parser.parse_args()
    run_attack_set(args.config, args.payloads, args.output)


if __name__ == "__main__":
    main()