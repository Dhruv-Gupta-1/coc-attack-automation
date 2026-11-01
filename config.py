import json
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "gemini_model": "gemini-3.1-flash-lite",
    "cycles": 5,
    "battle_wait_seconds": 75,
    "drag_duke_count": 1,
    "dragon_count": 16,
    "target_window": "Clash of Clans",
    "detection_threshold": 0.68,
    "troop_1_count": 1,
    "troop_2_count": 16,
    "auto_reload_on_disconnect": True
}

def _read_env_key() -> str:
    """Reads GEMINI_API_KEY from local .env or system environment if present."""
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY", "").strip()
    env_file = APP_DIR / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
        except Exception:
            pass
    return ""

def load_config() -> dict:
    """Loads configuration from config.json, creating it with defaults if not present."""
    env_key = _read_env_key()
    if not CONFIG_FILE.exists():
        cfg = DEFAULT_CONFIG.copy()
        if env_key:
            cfg["gemini_api_key"] = env_key
        save_config(cfg)
        return cfg
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            if not merged.get("gemini_api_key") and env_key:
                merged["gemini_api_key"] = env_key
            return merged
    except Exception:
        cfg = DEFAULT_CONFIG.copy()
        if env_key:
            cfg["gemini_api_key"] = env_key
        return cfg

def save_config(config_data: dict) -> bool:
    """Saves configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
