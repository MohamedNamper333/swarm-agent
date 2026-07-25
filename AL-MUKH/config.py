"""
AL-MUKH shared configuration — loads .env and exports Meilisearch credentials.
Import this module instead of hardcoding MEILI_URL / MEILI_KEY.
"""
import os
from pathlib import Path

def _load_env():
    """Load .env file from the AL-MUKH directory (best-effort, no python-dotenv)."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value

_load_env()

MEILI_URL = os.environ.get("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.environ.get("MEILI_MASTER_KEY", "mukh-dev-key-change-in-prod")
INDEX_NAME = "mukh-unified"
VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path.home() / "Documents" / "Obsidian Vault")))
SPOKE_ROOT = Path(os.environ.get("SPOKE_ROOT", str(VAULT_ROOT)))
