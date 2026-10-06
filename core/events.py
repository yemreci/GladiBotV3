from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Callable, Any

class BotState(Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    LOGGING_IN = "LOGGING_IN"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING_COOLDOWN = "WAITING_COOLDOWN"
    ERROR = "ERROR"

@dataclass
class LogMessage:
    timestamp: str
    level: str  # "INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG"
    text: str
    module_name: Optional[str] = None
