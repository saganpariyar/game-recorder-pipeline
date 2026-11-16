"""Master Pipeline Orchestrator coordinating Gameplay, Recording, and YouTube Upload."""

import os
import re
import time
import random
import datetime
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from src.config_loader import PipelineConfig
from src.controllers import (
    BaseGameController,
    PlaywrightGameController,
    PyAutoGUIController,
    ManualController,
    MockGameController,
)
from src.recorders import (
    BaseRecorder,
    OBSRecorder,
    PlaywrightRecorder,
    FFmpegRecorder,
    MockRecorder,
)
from src.uploader import (
    BaseUploader,
    YouTubeUploader,
    MockUploader,
)
from src.thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger("Pipeline.Orchestrator")


def sanitize_for_youtube(text: str) -> str:
    """Filter out gambling/betting trigger words to prevent automated age restriction."""
    if not text:
        return ""
    replacements = [
        (r"\bjackpot\s+sweep\b", "Grand Sweep"),
        (r"\bjackpot\b", "Grand Capture"),
        (r"\bpot\s+explosion\b", "Trick Stack Surge"),
        (r"\bpot-sweep\b", "Trick Sweep"),
        (r"\bpot sweep\b", "Trick Sweep"),
        (r"\bpots?\b", "Trick Stack"),
        (r"\bbaazi\b", "Khel"),
        (r"\bhigh-stakes\b", "Master Strategy"),
        (r"\bstakes\b", "points"),
        (r"\breal-money\b", "virtual"),
        (r"\bgambling\b", "board gaming"),
        (r"\bbetting\b", "strategy"),
        (r"\bpaisa\b", "points"),
        (r"\btash\b", "Board Game"),
    ]
    cleaned = text
    for pattern, repl in replacements:
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
    return cleaned


class PipelineOrchestrator:
    """Manages the full end-to-end lifecycle: App/Game -> Screen/Audio Recording -> YouTube Upload."""

    def __init__(
        self,
        config: PipelineConfig,
        dry_run: bool = False,
        record_only: bool = False,
        no_upload: bool = False,
        scenario: Optional[Dict[str, Any]] = None,
        schedule_publish_at: Optional[str] = None
    ):
        self.config = config
        self.dry_run = dry_run
        self.record_only = record_only or no_upload
        self.scenario = scenario
        self.schedule_publish_at = schedule_publish_at
        self.now = datetime.datetime.now()

        # If scenario provided, configure scenario parameters
        if self.scenario:
            if self.scenario.get("url"):
                self.config.app.url = self.scenario["url"]
            if self.scenario.get("game"):
                self.config.app.game_type = self.scenario["game"]

        # Pick random Bollywood player name if list configured
        if self.config.app.player_names:
            import random
            self.config.app.player_name = random.choice(self.config.app.player_names)

        # Build template replacement variables
        app_slug = re.sub(r"[^\w\s-]", "", self.config.app.name.lower()).strip().replace(" ", "_")
        self.context_vars = {
            "app_name": self.config.app.name,
            "app_slug": app_slug,
            "game_type": self.config.app.game_type,
            "game_title": self.config.app.game_type.title(),
            "game_upper": self.config.app.game_type.upper(),
            "player_name": self.config.app.player_name,
            "scenario_id": self.scenario["id"] if self.scenario else "LIVE",
            "scenario_title": self.scenario["title"] if self.scenario else "",
            "scenario_action": self.scenario.get("action", "") if self.scenario else "",
            "date": self.now.strftime("%Y-%m-%d"),
            "time": self.now.strftime("%H:%M:%S"),
            "timestamp": self.now.strftime("%Y%m%d_%H%M%S"),
        }

        # Format URL with player name if placeholders or parameters needed
        if self.config.app.url:
            formatted_url = self.config.app.url.format(**self.context_vars)
            if "name=" not in formatted_url:
                import urllib.parse
                sep = "&" if "?" in formatted_url else "?"
                formatted_url += f"{sep}name={urllib.parse.quote(self.config.app.player_name)}"
            self.config.app.url = formatted_url

        # Resolve paths
        self.output_dir = Path(self.config.recorder.output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = (Path(__file__).parent.parent / self.output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        filename = self.config.recorder.filename_template.format(**self.context_vars)
        self.output_video_file = str((self.output_dir / filename).resolve())

        # Sub-modules
        self.controller: Optional[BaseGameController] = None
        self.recorder: Optional[BaseRecorder] = None
        self.uploader: Optional[BaseUploader] = None

    def _init_components(self) -> None:
        """Instantiate controller, recorder, and uploader based on config."""
        logger.info("Initializing pipeline components...")

        # 1. Recorder Selection
        backend = "mock" if self.dry_run else self.config.recorder.backend.lower()
        if backend == "obs":
            self.recorder = OBSRecorder(self.config.recorder.obs)
        elif backend == "ffmpeg":
            self.recorder = FFmpegRecorder(self.config.recorder.ffmpeg)
        elif backend == "playwright":
            self.recorder = PlaywrightRecorder(self.config.recorder)
        else:
            self.recorder = MockRecorder()

        # 2. Controller Selection
        if self.dry_run:
            self.controller = MockGameController(self.config.app)
        else:
            mode = self.config.app.mode.lower()
            if mode == "web":
                # If recorder is playwright native, feed video_output_dir directly into browser context
                playwright_video_dir = str(self.output_dir) if backend == "playwright" else None
                self.controller = PlaywrightGameController(
                    app_cfg=self.config.app,
                    recorder_cfg=self.config.recorder,
                    video_output_dir=playwright_video_dir
                )
            elif mode in ["desktop", "emulator"]:
                self.controller = PyAutoGUIController(self.config.app)
            else:
                self.controller = ManualController(self.config.app)

        # 3. Uploader Selection
        if self.dry_run or not self.config.youtube.enabled:
            self.uploader = MockUploader()
        else:
            self.uploader = YouTubeUploader(self.config.youtube)

    def run(self) -> Dict[str, Any]:
        """Execute the complete automation pipeline."""
        self._init_components()

        result = {
            "success": False,
            "video_path": None,
            "youtube_url": None,
            "error": None
        }

        try:
            logger.info("=" * 70)
            logger.info(f"STARTING RECORDING PIPELINE: {self.config.app.name.upper()}")
            logger.info(f"Target Mode: {self.config.app.mode} | Game: {self.config.app.game_type}")
            logger.info(f"Recording Backend: {self.recorder.name}")
            logger.info(f"Target Output: {self.output_video_file}")
            logger.info("=" * 70)

            # Stage 2: Start Recording First
            logger.info(">>> STAGE 2: Starting Screen/Audio Recorder...")
            self.recorder.start_recording(self.output_video_file)

            # Stage 1: Launch App and Start Gameplay
            logger.info(">>> STAGE 1: Launching Game & Player Controller...")
            self.controller.start()

            # Gameplay Activity Loop
            duration = self.config.app.play_duration_seconds
            logger.info(f">>> STAGE 1: Executing Gameplay Loop ({duration}s)...")
            self.controller.run_gameplay_loop(duration_seconds=duration)

            # Stage 1: Stop Controller
            logger.info(">>> STAGE 1: Concluding Gameplay Session...")
            self.controller.stop()

            # For Playwright recorder, propagate output video file
            if isinstance(self.controller, PlaywrightGameController) and isinstance(self.recorder, PlaywrightRecorder):
                pw_video = self.controller.get_video_path()
                if pw_video:
                    self.recorder.notify_video_ready(pw_video)

            # Stage 2: Stop Recording & Finalize Video
            logger.info(">>> STAGE 2: Finalizing Video Recording...")
            saved_video_path = self.recorder.stop_recording()
            result["video_path"] = saved_video_path
            logger.info(f"[SUCCESS] Video saved at: {saved_video_path}")

            # Stage 3: YouTube Upload
            if not self.record_only and self.config.youtube.enabled:
                logger.info(">>> STAGE 3: Initiating YouTube Upload...")
                if self.scenario:
                    clean_title = sanitize_for_youtube(self.scenario['title'])
                    clean_action = sanitize_for_youtube(self.scenario.get('action', ''))
                    ch_name = self.config.youtube.target_channel_name or "The MK Chapter"
                    title = f"🎮 {self.scenario['id']}: {self.context_vars['player_name']} Plays {clean_title}! {self.context_vars['app_name']} | {ch_name}"
                    description = (
                        f"🎬 Scenario {self.scenario['id']}: {clean_title}\n"
                        f"📌 Round Highlight: {clean_action}\n"
                        f"🌟 Starring: {self.context_vars['player_name']} & Bollywood AI Bot Legends\n\n"
                        f"{self.config.youtube.description_template.format(**self.context_vars)}"
                    )
                else:
                    if self.config.youtube.title_templates:
                        selected_tmpl = random.choice(self.config.youtube.title_templates)
                    else:
                        selected_tmpl = self.config.youtube.title_template
                    title = selected_tmpl.format(**self.context_vars)
                    description = self.config.youtube.description_template.format(**self.context_vars)

                title = sanitize_for_youtube(title)
                description = sanitize_for_youtube(description)

                # Thumbnail handling (create automatically if enabled)
                thumbnail_file = self.config.youtube.thumbnail_path
                if not thumbnail_file and self.config.youtube.auto_generate_thumbnail:
                    try:
                        logger.info(">>> Generating custom 1280x720 YouTube Thumbnail...")
                        tg = ThumbnailGenerator(output_dir=str(self.output_dir / "thumbnails"))
                        tagline = (
                            f"{self.scenario['id']}: {sanitize_for_youtube(self.scenario['title']).upper()}"
                            if self.scenario else None
                        )
                        prefix = f"thumb_{self.scenario['id']}" if self.scenario else f"thumb_{self.context_vars['app_slug']}"
                        thumbnail_file = tg.generate(
                            game_title=self.config.app.game_type.upper(),
                            player_name=self.context_vars.get("player_name"),
                            tagline=tagline,
                            video_path=saved_video_path,
                            filename_prefix=prefix,
                            made_for_kids=self.config.youtube.made_for_kids
                        )
                        logger.info(f"[SUCCESS] Custom thumbnail created at: {thumbnail_file}")
                    except Exception as ex:
                        logger.warning(f"Could not generate custom thumbnail: {ex}")

                try:
                    youtube_url = self.uploader.upload(
                        video_path=saved_video_path,
                        title=title,
                        description=description,
                        tags=self.config.youtube.tags,
                        privacy_status=self.config.youtube.privacy_status,
                        category_id=self.config.youtube.category_id,
                        made_for_kids=self.config.youtube.made_for_kids,
                        thumbnail_path=thumbnail_file,
                        publish_at=self.schedule_publish_at
                    )
                    result["youtube_url"] = youtube_url

                    # Update Scenario Tracker if scenario was active
                    if self.scenario and youtube_url:
                        try:
                            from src.scenario_manager import ScenarioManager
                            ScenarioManager.mark_completed(
                                scenario_id=self.scenario["id"],
                                youtube_url=youtube_url,
                                video_path=saved_video_path
                            )
                        except Exception as trk_err:
                            logger.warning(f"Failed to update scenario tracker: {trk_err}")
                except Exception as upload_err:
                    logger.error(f"[ERROR] YouTube upload encountered an error: {upload_err}")
                    result["upload_error"] = str(upload_err)
            else:
                logger.info(">>> STAGE 3: YouTube upload skipped (--record-only or disabled).")

            result["success"] = True

        except Exception as e:
            logger.error(f"[ERROR] Pipeline execution failed: {e}", exc_info=True)
            result["error"] = str(e)
            # Cleanup active resources
            try:
                if self.controller and self.controller.is_running():
                    self.controller.stop()
            except Exception:
                pass
            try:
                if self.recorder and self.recorder.is_recording():
                    self.recorder.stop_recording()
            except Exception:
                pass
            raise

        finally:
            logger.info("=" * 70)
            logger.info("PIPELINE EXECUTION SUMMARY")
            logger.info(f"Status:      {'SUCCESS' if result['success'] else 'FAILED'}")
            logger.info(f"Video File:  {result.get('video_path')}")
            logger.info(f"YouTube URL: {result.get('youtube_url') or 'N/A'}")
            logger.info("=" * 70)

        return result
