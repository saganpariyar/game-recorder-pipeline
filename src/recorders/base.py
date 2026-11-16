"""Base Recorder interface for Stage 2: Screen & Audio Recording."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseRecorder(ABC):
    """Abstract base class representing a video and audio capture recorder."""

    def __init__(self, name: str = "BaseRecorder"):
        self.name = name
        self.recording: bool = False
        self.output_filepath: Optional[str] = None

    @abstractmethod
    def start_recording(self, output_path: str) -> None:
        """Begin video & audio capture to the specified output file."""
        pass

    @abstractmethod
    def stop_recording(self) -> str:
        """Stop capture and finalize the video file. Returns absolute path of recorded video."""
        pass

    def is_recording(self) -> bool:
        """Return True if recording is in progress."""
        return self.recording

