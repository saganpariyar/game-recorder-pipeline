"""Recorders package for Stage 2: Screen/Audio Recording."""

from src.recorders.base import BaseRecorder
from src.recorders.obs_recorder import OBSRecorder
from src.recorders.playwright_recorder import PlaywrightRecorder
from src.recorders.ffmpeg_recorder import FFmpegRecorder
from src.recorders.mock_recorder import MockRecorder

__all__ = [
    "BaseRecorder",
    "OBSRecorder",
    "PlaywrightRecorder",
    "FFmpegRecorder",
    "MockRecorder",
]

