"""Mock Game Controller for testing and dry runs."""

import time
import logging
from src.controllers.base import BaseGameController
from src.config_loader import AppConfig

logger = logging.getLogger("Pipeline.MockBot")


class MockGameController(BaseGameController):
    """Simulates game actions without requiring an active browser or desktop window."""

    def __init__(self, app_cfg: AppConfig):
        super().__init__(name="MockGameController")
        self.app_cfg = app_cfg

    def start(self) -> None:
        logger.info(f"[MOCK] Simulated launch of game '{self.app_cfg.name}' (mode: {self.app_cfg.mode}).")
        self.running = True

    def run_gameplay_loop(self, duration_seconds: int = 5) -> None:
        logger.info(f"[MOCK] Simulating gameplay for {duration_seconds}s...")
        time.sleep(min(2, duration_seconds))
        logger.info("[MOCK] Simulated playing 3 card rounds with AI bots.")

    def stop(self) -> None:
        logger.info("[MOCK] Simulated game shutdown.")
        self.running = False

