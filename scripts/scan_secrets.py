#!/usr/bin/env python3
"""Fail-closed repository secret scanner used by CI and release gates."""
from swarm.enterprise.core.governance.production_gate import ProductionGate


if __name__ == "__main__":
    passed, message = ProductionGate()._check_secrets()
    print(message)
    raise SystemExit(0 if passed else 1)
