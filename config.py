"""
config.py - 配置读写，存储于 %APPDATA%\AudioStream\config.json
"""

import json
import os
from dataclasses import dataclass, asdict


CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "AudioStream")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "mode": "server",
    "server_ip": "192.168.99.1",
    "port": 5000,
    "autostart": False,
    "first_run": True,
}


@dataclass
class AppConfig:
    mode: str
    server_ip: str
    port: int
    autostart: bool
    first_run: bool

    @classmethod
    def load(cls) -> "AppConfig":
        data = dict(DEFAULTS)
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                data.update(saved)  # 合并默认值，防止升级后 KeyError
            except (json.JSONDecodeError, OSError):
                pass
        return cls(**{k: data[k] for k in DEFAULTS})

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)
