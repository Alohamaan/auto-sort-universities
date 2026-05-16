from __future__ import annotations

import argparse
import json

from admissions_agent.jobs.poller import PollMailboxJob


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run admissions email reconciliation once")
    parser.add_argument("--query", default=None, help="Custom Gmail search query")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed actions without writing to Google Sheets or Gmail",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job = PollMailboxJob(dry_run=args.dry_run)
    decisions = job.run_once(query=args.query)

    for item in decisions:
        print(json.dumps(item, sort_keys=True, default=str))

    if args.dry_run and not decisions:
        print("DRY-RUN: no candidate threads found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
