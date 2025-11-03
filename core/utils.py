#!/usr/bin/env python3
# wifitool/core/utils.py

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Any, List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
CREDENTIAL_FILE = DATA_DIR / "credentials.jsonl"  # switched to plain JSON lines
CONFIG_FILE = ROOT / "config.json"

# -------------------- Directory / file helpers --------------------
def ensure_dirs() -> None:
    """Ensure necessary directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

def log_event(msg: str) -> None:
    """Append timestamped log to logs portal.log."""
    ensure_dirs()
    ts = datetime.utcnow().isoformat()
    with open(LOGS_DIR / "portal.log", "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[LOG {ts}] {msg}")

# -------------------- Config helpers --------------------
def load_config() -> dict[str, Any]:
    """Load portal config or fallback defaults."""
    defaults = {
        "portal_port": 8080,
        "victim_site": "/"
    }
    if CONFIG_FILE.exists():
        try:
            return {**defaults, **json.load(open(CONFIG_FILE, "r", encoding="utf-8"))}
        except Exception as e:
            log_event(f"[utils] Failed to load config.json: {e}")
    return defaults

def save_config(cfg: dict) -> None:
    """Save configuration dict to config.json (pretty-printed)."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        log_event(f"[utils] Failed to save config.json: {e}")

# -------------------- Plain JSON entry storage --------------------
def append_entry(entry_json: str) -> None:
    """
    Append an entry (JSON string) to CREDENTIAL_FILE in plain text.
    Each entry is stored as a single line (JSON object per line).
    """
    ensure_dirs()
    with open(CREDENTIAL_FILE, "a", encoding="utf-8") as f:
        f.write(entry_json + "\n")

def load_entries() -> List[str]:
    """
    Read CREDENTIAL_FILE and return list of JSON strings.
    """
    if not CREDENTIAL_FILE.exists():
        return []
    with open(CREDENTIAL_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines
