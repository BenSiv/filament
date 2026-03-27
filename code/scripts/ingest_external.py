import argparse
import os
import sys

scripts_dir = os.path.dirname(os.path.abspath(__file__))
code_dir = os.path.dirname(scripts_dir)
if code_dir not in sys.path:
    sys.path.insert(0, code_dir)

from core.ingestion import REGISTRY


def list_sources():
    for source_cls in REGISTRY.list():
        status = "enabled" if source_cls.default_enabled else "stub"
        print(f"{source_cls.name:15} | {status:7} | {source_cls.description}")


def run_sources(names, limit, output_dir):
    results = []
    for name in names:
        source_cls = REGISTRY.get(name)
        source = source_cls()
        count = source.run(output_dir=output_dir, limit=limit)
        results.append((name, count))
    return results


def main():
    parser = argparse.ArgumentParser(description="Run external ingestion sources")
    parser.add_argument("--list", action="store_true", help="List available sources")
    parser.add_argument("--source", action="append", default=[], help="Source name to run (repeatable)")
    parser.add_argument("--all", action="store_true", help="Run all registered sources")
    parser.add_argument("--limit", type=int, default=0, help="Optional record limit")
    parser.add_argument(
        "--output-dir",
        default="data/raw/ingestion",
        help="Directory for output JSONL files",
    )
    args = parser.parse_args()

    if args.list:
        list_sources()
        return

    if args.all:
        names = [source.name for source in REGISTRY.list()]
    else:
        names = args.source

    if not names:
        print("No sources selected. Use --list to see available sources.")
        return

    limit = args.limit if args.limit > 0 else None
    os.makedirs(args.output_dir, exist_ok=True)
    results = run_sources(names, limit, args.output_dir)

    for name, count in results:
        print(f"{name}: wrote {count} records")


if __name__ == "__main__":
    main()
