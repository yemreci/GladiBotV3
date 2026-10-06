import json
import os
from dataclasses import dataclass, asdict

CONFIG_FILE = "bot_config.json"

@dataclass
class BotConfig:
    lobby_url: str = "https://lobby.gladiatus.gameforge.com/en_GB/hub"
    poll_interval_seconds: float = 6.0
    
    # Modules
    expedition_enabled: bool = True
    expedition_mob_index: int = 1
    
    dungeon_enabled: bool = False
    
    healer_enabled: bool = False
    min_hp_percent: int = 40
    
    auction_enabled: bool = False
    max_bid_gold: int = 5000
    
    # Hotkeys
    hotkey_start_resume: str = "f6"
    hotkey_pause: str = "f7"
    hotkey_stop: str = "f8"

    @classmethod
    def load(cls, path: str = CONFIG_FILE) -> "BotConfig":
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return cls(**data)
            except Exception:
                pass
        return cls()

    def save(self, path: str = CONFIG_FILE):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception:
            pass
