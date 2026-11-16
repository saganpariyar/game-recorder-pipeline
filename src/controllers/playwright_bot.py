"""Playwright Game Controller for web-based games (Bikkad, Jhuthaniya, Tikdi, etc.)."""

import time
import logging
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from src.controllers.base import BaseGameController
from src.config_loader import AppConfig, RecorderConfig

logger = logging.getLogger("Pipeline.PlaywrightBot")


class PlaywrightGameController(BaseGameController):
    """Automates web games in a browser with realistic actions, card-playing logic, and video hooks."""

    def __init__(
        self,
        app_cfg: AppConfig,
        recorder_cfg: Optional[RecorderConfig] = None,
        video_output_dir: Optional[str] = None
    ):
        super().__init__(name="PlaywrightGameController")
        self.app_cfg = app_cfg
        self.recorder_cfg = recorder_cfg
        self.video_output_dir = video_output_dir

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.recorded_video_path: Optional[str] = None

    def start(self) -> None:
        """Launch browser, configure viewport & recording, and open the game page."""
        logger.info(f"Starting Playwright session for '{self.app_cfg.name}' at {self.app_cfg.url}...")
        self.playwright = sync_playwright().start()

        width = self.recorder_cfg.resolution_width if self.recorder_cfg else 1920
        height = self.recorder_cfg.resolution_height if self.recorder_cfg else 1080

        # Pre-flight check if URL is reachable
        if self.app_cfg.url:
            self._check_url_reachable(self.app_cfg.url)

        # Launch Chromium (headed so OBS can record or Playwright can capture)
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=[
                f"--window-size={width},{height}",
                "--start-maximized",
                "--autoplay-policy=no-user-gesture-required"
            ]
        )

        context_kwargs = {
            "viewport": {"width": width, "height": height},
            "no_viewport": False
        }

        # If recorder is playwright native, attach record_video_dir
        if self.video_output_dir:
            Path(self.video_output_dir).mkdir(parents=True, exist_ok=True)
            context_kwargs["record_video_dir"] = self.video_output_dir
            context_kwargs["record_video_size"] = {"width": width, "height": height}

        self.context = self.browser.new_context(**context_kwargs)
        self.page = self.context.new_page()

        # Navigate to game URL
        logger.info(f"Navigating to {self.app_cfg.url}...")
        self.page.goto(self.app_cfg.url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)  # Brief render grace period
        self.running = True

        # Unmute & initialize Web Audio API and Speech Synthesis
        try:
            self.page.evaluate("""() => {
                if (window.speechSynthesis) window.speechSynthesis.getVoices();
                if (window.sfx && typeof window.sfx.init === 'function') {
                    window.sfx.init();
                }
            }""")
        except Exception:
            pass

        if self.app_cfg.auto_start_match:
            self._setup_and_start_match()

    def _check_url_reachable(self, url: str) -> None:
        """Check if web app is responding before launching browser."""
        import urllib.request
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GamePipelineBot"})
            with urllib.request.urlopen(req, timeout=3):
                pass
        except Exception as e:
            logger.warning(
                f"\n{'='*70}\n"
                f"[WARNING] Could not reach '{url}': {e}\n"
                f"If you are recording Bikkad, make sure your game server is running!\n"
                f"You can launch it by running: c:\\Projects\\run_game.bat\n"
                f"{'='*70}\n"
            )

    def _setup_and_start_match(self) -> None:
        """Configure game selection and click Start Match."""
        if not self.page:
            return

        try:
            # 1. Switch to configured game tab if not already selected
            game_selector_id = f"#gsel-{self.app_cfg.game_type.lower()}"
            if self.page.is_visible(game_selector_id):
                logger.info(f"Selecting game mode: {self.app_cfg.game_type}")
                self.page.click(game_selector_id)
                time.sleep(0.5)

            # 2. Enter player name if input is present
            if self.page.is_visible("#input-your-name"):
                self.page.fill("#input-your-name", self.app_cfg.player_name)
                time.sleep(0.3)

            # 3. Select 1 Human Solo mode if buttons present
            if self.page.is_visible("#hcount-1"):
                self.page.click("#hcount-1")
                time.sleep(0.3)

            # 4. Click Record Mode or Start Match
            if self.page.is_visible("#btn-record-mode"):
                logger.info("Clicking '#btn-record-mode' to launch autonomous Record Mode match...")
                self.page.click("#btn-record-mode")
                time.sleep(2.0)
            elif self.page.is_visible("#btn-start-game"):
                logger.info("Clicking '#btn-start-game' to launch match...")
                self.page.click("#btn-start-game")
                time.sleep(2.0)
            else:
                logger.info("Start match button not found or game already in progress.")

        except Exception as e:
            logger.warning(f"Error during lobby setup: {e}. Attempting to continue...")

    def run_gameplay_loop(self, duration_seconds: int = 60) -> None:
        """Run gameplay loop for specified duration, picking cards and handling turns."""
        if not self.page:
            logger.error("Page is not initialized.")
            return

        logger.info(f"Starting gameplay loop for {duration_seconds}s...")
        end_time = time.time() + duration_seconds
        step_delay = self.app_cfg.turn_delay_ms / 1000.0

        while time.time() < end_time and self.running:
            if self.page.is_closed():
                logger.info("Browser page was closed by the game (Record mode completed). Stopping gameplay loop.")
                break

            try:
                # 0. Check if full match has completed
                if self.app_cfg.play_until_match_over:
                    is_complete = False
                    try:
                        is_complete = self.page.evaluate(
                            "() => window.recordingComplete === true || document.body.dataset.recordingComplete === 'true'"
                        )
                    except Exception:
                        pass

                    if is_complete or (self.page.is_visible("#modal-record-complete")):
                        logger.info("[VICTORY] Complete Match finished! Capturing final scoreboard...")
                        time.sleep(3.5)  # Capture victory screen on video
                        break

                # 1. Check for Trump selection dialog / modal (Bikkad / Bindi Coat)
                self._handle_trump_selection()

                # 2. Check for playable cards in the player's hand
                self._handle_card_play()

                # 3. Check for round end / Next Round / Play Again buttons
                self._handle_round_transitions()

                time.sleep(step_delay)

            except Exception as e:
                logger.debug(f"Gameplay loop iteration warning: {e}")
                time.sleep(1.0)

        logger.info("Gameplay loop duration completed.")

    def _handle_trump_selection(self) -> None:
        """Check if trump selection modal or prompt is active and make a choice."""
        if not self.page:
            return

        # Look for visible suit buttons or trump card selectors
        trump_selectors = [
            ".trump-suit-btn",
            "#btn-trump-spade",
            "#btn-trump-heart",
            "#btn-trump-diamond",
            "#btn-trump-club",
            ".suit-choice-card",
            "#btn-auto-trump"
        ]

        for selector in trump_selectors:
            if self.page.is_visible(selector):
                logger.info(f"Trump selection prompt detected. Clicking {selector}...")
                self.page.click(selector)
                time.sleep(0.5)
                return

    def _handle_card_play(self) -> None:
        """Inspect human hand and click an active or valid card to play."""
        if not self.page:
            return

        # Possible selectors for cards in human hand
        card_selectors = [
            "#hand-cards-container .card-item:not(.card-disabled)",
            "#hand-p1 .card:not(.card-disabled)",
            ".player-hand-bottom .card-item",
            "#my-hand .card",
            ".card-playable",
            ".hand-card"
        ]

        for selector in card_selectors:
            cards = self.page.query_selector_all(selector)
            if cards:
                # Click the first playable card
                try:
                    logger.info(f"Playing card using selector '{selector}' (found {len(cards)} cards)...")
                    cards[0].click()
                    time.sleep(0.5)
                    return
                except Exception as ex:
                    logger.debug(f"Failed to click card with {selector}: {ex}")

    def _handle_round_transitions(self) -> None:
        """Handle end-of-deal or round victory dialogs to keep game flowing."""
        if not self.page:
            return

        # Autonomous Record Mode handles deal transitions & match completion itself
        if self.app_cfg.url and "mode=record" in self.app_cfg.url:
            return

        continue_selectors = [
            "#btn-next-deal",
            "#btn-next-round",
            "#btn-play-again",
            ".btn-game-continue",
            "#modal-btn-confirm"
        ]

        for btn in continue_selectors:
            if self.page.is_visible(btn):
                logger.info(f"Round transition detected. Clicking {btn}...")
                self.page.click(btn)
                time.sleep(1.0)
                return

    def stop(self) -> None:
        """Close browser context and extract recorded video path if available."""
        logger.info("Stopping Playwright session...")
        self.running = False

        video = None
        if self.page:
            try:
                video = self.page.video
                self.page.close()
            except Exception as e:
                logger.warning(f"Error closing page: {e}")

        if self.context:
            try:
                self.context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")

        if video:
            try:
                self.recorded_video_path = video.path()
                logger.info(f"Playwright video recorded to: {self.recorded_video_path}")
            except Exception as e:
                logger.warning(f"Error getting video path: {e}")

        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")

        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping playwright: {e}")

        logger.info("Playwright session terminated.")

    def get_video_path(self) -> Optional[str]:
        """Return the path to the recorded video file if recorded via Playwright."""
        return self.recorded_video_path
