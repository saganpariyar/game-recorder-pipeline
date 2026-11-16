"""Mock recorder for unit testing and dry runs."""

import time
import logging
from pathlib import Path
from src.recorders.base import BaseRecorder

logger = logging.getLogger("Pipeline.MockRecorder")


class MockRecorder(BaseRecorder):
    """Simulates recording by generating a placeholder video file."""

    def __init__(self):
        super().__init__(name="MockRecorder")

    def start_recording(self, output_path: str) -> None:
        self.output_filepath = output_path
        self.recording = True
        logger.info(f"[MOCK] Recording started -> {output_path}")

    def stop_recording(self) -> str:
        self.recording = False
        target = Path(self.output_filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Create a lightweight dummy file if it doesn't exist
        if not target.exists():
            target.write_bytes(b"DUMMY_VIDEO_STREAM_DATA_MOCK")
        logger.info(f"[MOCK] Recording stopped -> {target.resolve()}")
        return str(target.resolve())

