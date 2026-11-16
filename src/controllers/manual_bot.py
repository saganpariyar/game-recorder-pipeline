"""Manual controller allowing the human user to play while the pipeline records and uploads."""

import time
import logging
from src.controllers.base import BaseGameController
from src.config_loader import AppConfig

logger = logging.getLogger("Pipeline.ManualController")


class ManualController(BaseGameController):
    """Pass-through controller that allows manual play for a designated duration or until stopped."""

    def __init__(self, app_cfg: AppConfig):
        super().__init__(name="ManualController")
        self.app_cfg = app_cfg

    def start(self) -> None:
        logger.info(f"Manual mode active for '{self.app_cfg.name}'. Please play the game directly!")
        self.running = True

    def run_gameplay_loop(self, duration_seconds: int = 60) -> None:
        logger.info(f"Recording user gameplay for {duration_seconds} seconds. Press Ctrl+C in terminal to stop early.")
        start_time = time.time()
        while time.time() - start_time < duration_seconds and self.running:
            time.sleep(1.0)

    def stop(self) -> None:
        logger.info("Ending manual gameplay session.")
        self.running = False

