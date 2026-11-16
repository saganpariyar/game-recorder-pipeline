"""Playwright Native Video Recorder with Automated Audio Loopback Capture & Muxing."""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

from src.recorders.base import BaseRecorder
from src.config_loader import RecorderConfig
from src.recorders.audio_loopback import AudioLoopbackRecorder

logger = logging.getLogger("Pipeline.PlaywrightRecorder")


class PlaywrightRecorder(BaseRecorder):
    """Integrates Playwright's viewport recording with automated WASAPI loopback audio capture and FFmpeg muxing."""

    def __init__(self, config: RecorderConfig):
        super().__init__(name="PlaywrightRecorder")
        self.config = config
        self.source_video_path: Optional[str] = None
        self.target_output_path: Optional[str] = None
        self.audio_recorder: Optional[AudioLoopbackRecorder] = None
        self.temp_audio_path: Optional[str] = None

    def start_recording(self, output_path: str) -> None:
        """Mark recording active, set target output path, and launch background loopback audio capture."""
        self.target_output_path = output_path
        self.recording = True
        logger.info(f"Playwright video capture initialized for destination: {output_path}")

        # Start synchronized audio loopback recording
        try:
            self.temp_audio_path = str(Path(output_path).with_suffix(".loopback.wav"))
            self.audio_recorder = AudioLoopbackRecorder()
            if self.audio_recorder.start(self.temp_audio_path):
                logger.info(f"Automatic Audio Capture active (WASAPI Loopback): {self.temp_audio_path}")
            else:
                self.audio_recorder = None
        except Exception as e:
            logger.warning(f"Could not start background audio capture: {e}")
            self.audio_recorder = None

    def notify_video_ready(self, source_path: str) -> None:
        """Called by the Playwright controller when browser session closes and writes the video file."""
        self.source_video_path = source_path

    def stop_recording(self) -> str:
        """Finalize video, stop audio loopback, merge them with FFmpeg, and return final output path."""
        self.recording = False

        # Stop audio capture
        audio_file = None
        if self.audio_recorder:
            try:
                audio_file = self.audio_recorder.stop()
            except Exception as e:
                logger.warning(f"Error stopping audio recorder: {e}")

        if not self.source_video_path or not Path(self.source_video_path).exists():
            logger.warning(f"Source video file not found at {self.source_video_path}")
            return self.target_output_path or "recording.webm"

        src = Path(self.source_video_path)
        dest = Path(self.target_output_path) if self.target_output_path else src
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Merge Audio & Video if audio file exists
        if audio_file and Path(audio_file).exists():
            logger.info("Merging captured audio track with gameplay video...")
            success = AudioLoopbackRecorder.mux_video_audio(
                video_path=str(src.resolve()),
                audio_path=audio_file,
                output_path=str(dest.resolve())
            )
            if success and dest.exists():
                logger.info(f"[SUCCESS] Final video with complete audio saved to: {dest.resolve()}")
                return str(dest.resolve())
            else:
                logger.warning("Audio muxing failed or produced no output. Falling back to video copy.")

        # Fallback: copy raw video if no audio or muxing failed
        try:
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
                logger.info(f"Final video moved to: {dest.resolve()}")
                return str(dest.resolve())
            return str(src.resolve())
        except Exception as e:
            logger.warning(f"Error copying video file: {e}")
            return str(src.resolve())
