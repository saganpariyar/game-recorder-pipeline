"""Base Game Controller interface for Stage 1: Gameplay & Control."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseGameController(ABC):
    """Abstract base class representing an automated player or game session controller."""

    def __init__(self, name: str = "BaseController"):
        self.name = name
        self.running: bool = False

    @abstractmethod
    def start(self) -> None:
        """Initialize and launch game connection, browser, or window."""
        pass

    @abstractmethod
    def run_gameplay_loop(self, duration_seconds: int = 60) -> None:
        """Execute automated gameplay actions for the given duration."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Gracefully terminate gameplay session and release resources."""
        pass

    def is_running(self) -> bool:
        """Check whether controller session is currently active."""
        return self.running

