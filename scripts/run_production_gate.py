#!/usr/bin/env python3
"""CLI entry point for the fail-closed production release gate."""
from __future__ import annotations

import argparse
import json

from swarm.enterprise.core.governance.production_gate import get_production_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the institutional production release gate")
    parser.add_argument("--report", default="artifacts/production-gate.json")
    args = parser.parse_args()

    gate = get_production_gate()
    summary = gate.run_all()
    gate.write_report(args.report)
    print(json.dumps(summary, indent=2))
    return 0 if summary["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
