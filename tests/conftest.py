"""Shared pytest fixtures for the swarm-agent test suite.

This conftest ensures that:
  - the project root is on sys.path so `vault_client`, `swarm.*`, and friends import
  - a tmp_path-based vault working dir is provided to tests that need it
  - a pytest-html-friendly summary plugin hook is registered
"""
import sys
import os
from pathlib import Path

import pytest

# Ensure project root is importable from any test (unit/live/e2e/stress/challenges).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also honor PYTHONPATH if set explicitly.
_env_pp = os.environ.get("PYTHONPATH", "")
if _env_pp:
    for p in _env_pp.split(os.pathsep):
        if p and p not in sys.path:
            sys.path.insert(0, p)

# Quiet down chatty third-party loggers during tests.
import logging
for _name in ("urllib3", "asyncio", "httpx"):
    logging.getLogger(_name).setLevel(logging.WARNING)


@pytest.fixture
def project_root() -> Path:
    """Return the absolute path to the swarm-agent project root."""
    return PROJECT_ROOT


@pytest.fixture
def vault_workdir(tmp_path) -> Path:
    """Per-test vault working directory under pytest's tmp_path."""
    wd = tmp_path / "vault"
    wd.mkdir(exist_ok=True)
    return wd
