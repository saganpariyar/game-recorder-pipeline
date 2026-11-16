"""FFmpeg Subprocess Screen & Audio Recorder."""

import os
import time
import signal
import subprocess
import logging
from pathlib import Path
from typing import Optional

from src.recorders.base import BaseRecorder
from src.config_loader import FFmpegConfig

logger = logging.getLogger("Pipeline.FFmpegRecorder")


class FFmpegRecorder(BaseRecorder):
    """Captures desktop and audio using FFmpeg subprocess (gdigrab on Windows)."""

    def __init__(self, config: FFmpegConfig):
        super().__init__(name="FFmpegRecorder")
        self.config = config
        self.process: Optional[subprocess.Popen] = None

    def _find_ffmpeg(self) -> str:
        """Locate ffmpeg binary in config, PATH, or playwright cache."""
        # 1. Configured path
        if self.config.ffmpeg_path and shutil_which(self.config.ffmpeg_path):
            return self.config.ffmpeg_path

        # 2. Check standard PATH
        import shutil
        found = shutil.which("ffmpeg")
        if found:
            return found

        # 3. Check Playwright cache
        user_home = Path.home()
        playwright_ffmpeg = user_home / "AppData" / "Local" / "ms-playwright" / "ffmpeg-1013" / "ffmpeg-win64.exe"
        if playwright_ffmpeg.exists():
            return str(playwright_ffmpeg)

        return self.config.ffmpeg_path

    def start_recording(self, output_path: str) -> None:
        """Launch FFmpeg subprocess capturing desktop."""
        ffmpeg_bin = self._find_ffmpeg()
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_filepath = str(out_file)

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "gdigrab",
            "-framerate", str(self.config.framerate),
            "-i", self.config.video_device,
        ]

        # Optional audio capture if configured
        if self.config.audio_device:
            cmd.extend([
                "-f", "dshow",
                "-i", f"audio={self.config.audio_device}",
                "-c:a", "aac",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            str(out_file)
        ])

        logger.info(f"Launching FFmpeg: {' '.join(cmd)}")
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            )
            self.recording = True
            time.sleep(1.0)  # Brief wait to ensure capture initialized
            logger.info(f"[SUCCESS] FFmpeg screen recording active -> {self.output_filepath}")
        except Exception as e:
            logger.error(f"Failed to launch FFmpeg: {e}")
            raise

    def stop_recording(self) -> str:
        """Send 'q' to FFmpeg stdin to gracefully finalize MP4 container."""
        if not self.process or not self.recording:
            return self.output_filepath or "output.mp4"

        logger.info("Stopping FFmpeg recording...")
        try:
            if self.process.stdin:
                self.process.stdin.write(b"q")
                self.process.stdin.flush()
            self.process.wait(timeout=5)
        except Exception:
            logger.warning("FFmpeg did not quit cleanly on 'q', terminating process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()

        self.recording = False
        time.sleep(1.0)
        logger.info(f"FFmpeg recording finalized at: {self.output_filepath}")
        return self.output_filepath


def shutil_which(cmd: str) -> Optional[str]:
    import shutil
    return shutil.which(cmd)

