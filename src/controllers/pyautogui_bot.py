"""PyAutoGUI Controller for desktop games, native Windows apps, and Android Emulators."""

import time
import logging
from typing import Optional
from src.controllers.base import BaseGameController
from src.config_loader import AppConfig

logger = logging.getLogger("Pipeline.PyAutoGUIBot")


class PyAutoGUIController(BaseGameController):
    """Controls desktop windows or emulators using simulated mouse clicks, key presses, and window focusing."""

    def __init__(self, app_cfg: AppConfig):
        super().__init__(name="PyAutoGUIController")
        self.app_cfg = app_cfg

    def start(self) -> None:
        """Locate target game window and bring it into focus."""
        import pyautogui

        logger.info(f"Starting PyAutoGUI session for window: '{self.app_cfg.window_title}'...")
        pyautogui.FAILSAFE = True

        if self.app_cfg.window_title:
            try:
                import pygetwindow as gw
                windows = gw.getWindowsWithTitle(self.app_cfg.window_title)
                if windows:
                    win = windows[0]
                    logger.info(f"Activating target window: {win.title}")
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    time.sleep(1.0)
                else:
                    logger.warning(f"No window found matching '{self.app_cfg.window_title}'. Ensure game is running.")
            except Exception as e:
                logger.warning(f"Failed to focus window using pygetwindow: {e}")

        self.running = True

    def run_gameplay_loop(self, duration_seconds: int = 60) -> None:
        """Perform periodic gameplay clicks or keys to maintain activity."""
        import pyautogui

        logger.info(f"Running desktop gameplay interaction loop for {duration_seconds}s...")
        end_time = time.time() + duration_seconds
        step_delay = max(1.0, self.app_cfg.turn_delay_ms / 1000.0)

        # Get screen dimensions for center-based relative clicking
        screen_w, screen_h = pyautogui.size()
        center_x, center_y = screen_w // 2, screen_h // 2

        while time.time() < end_time and self.running:
            try:
                # Example: click bottom-center area where player cards normally reside
                card_zone_y = int(screen_h * 0.82)
                card_zone_x = center_x

                logger.debug(f"Simulating interaction click at ({card_zone_x}, {card_zone_y})")
                pyautogui.click(card_zone_x, card_zone_y)

                time.sleep(step_delay)
            except Exception as e:
                logger.warning(f"Error in PyAutoGUI loop: {e}")
                time.sleep(2.0)

        logger.info("PyAutoGUI loop finished.")

    def stop(self) -> None:
        """Terminate PyAutoGUI interaction."""
        logger.info("Stopping PyAutoGUI controller...")
        self.running = False

