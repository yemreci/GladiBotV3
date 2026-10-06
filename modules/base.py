from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, Any
from playwright.sync_api import Page

@dataclass
class ActionResult:
    success: bool
    message: str
    cooldown_seconds: float = 0.0
    retry_delay_seconds: float = 10.0

@dataclass
class BotTask:
    name: str
    module_name: str
    priority: int  # Lower number = higher priority (e.g. 1 = Healer, 2 = Auction, 3 = Expedition)
    execute_fn: Callable[[Page, Any, Callable[[], bool]], ActionResult]

    def __lt__(self, other):
        return self.priority < other.priority

class BaseModule(ABC):
    """Abstract base class for all bot automation modules."""

    def __init__(self, name: str, enabled: bool = True, priority: int = 5):
        self.name = name
        self.enabled = enabled
        self.priority = priority
        self.last_run_time: float = 0.0
        self.next_allowed_time: float = 0.0

    @abstractmethod
    def evaluate(self, page: Page, browser: Any) -> Optional[BotTask]:
        """
        Inspects the page/DOM to check if this module needs to act.
        Returns a BotTask if an action is ready, or None if on cooldown / conditions not met.
        """
        pass

    @abstractmethod
    def execute(self, page: Page, browser: Any, can_continue: Callable[[], bool]) -> ActionResult:
        """
        Executes the automation action.
        can_continue() should be checked before/during multi-step actions to support pausing.
        """
        pass
