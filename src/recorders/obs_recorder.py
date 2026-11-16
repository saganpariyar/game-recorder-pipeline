"""OBS Studio Recorder using WebSocket v5 (obs-websocket-py)."""

import os
import time
import logging
from pathlib import Path
from typing import Optional
from obswebsocket import obsws, requests, exceptions

from src.recorders.base import BaseRecorder
from src.config_loader import OBSConfig

logger = logging.getLogger("Pipeline.OBSRecorder")


class OBSRecorder(BaseRecorder):
    """Controls OBS Studio recording, scene switching, and status querying via OBS WebSocket v5."""

    def __init__(self, config: OBSConfig):
        super().__init__(name="OBSRecorder")
        self.config = config
        self.ws: Optional[obsws] = None

    def _ensure_connected(self) -> None:
        """Connect to OBS WebSocket server if not connected."""
        if self.ws is not None:
            return

        logger.info(f"Connecting to OBS Studio WebSocket at ws://{self.config.host}:{self.config.port}...")
        try:
            self.ws = obsws(self.config.host, self.config.port, self.config.password)
            self.ws.connect()
            logger.info("[SUCCESS] Connected to OBS Studio WebSocket server!")
        except Exception as e:
            self.ws = None
            msg = (
                f"Failed to connect to OBS Studio at {self.config.host}:{self.config.port}: {e}\n"
                "Please make sure:\n"
                "  1. OBS Studio is currently open and running.\n"
                "  2. WebSocket Server is enabled in OBS: Tools -> WebSocket Server Settings -> Enable WebSocket Server\n"
                f"  3. Server Port matches config (default: {self.config.port})\n"
                "  4. Password in config matches OBS WebSocket settings (leave empty if no password set)."
            )
            logger.error(msg)
            raise ConnectionError(msg) from e

    def start_recording(self, output_path: str) -> None:
        """Switch scene (if configured) and start OBS recording."""
        self._ensure_connected()

        # Switch to custom scene if specified
        if self.config.scene_name:
            try:
                logger.info(f"Switching OBS scene to '{self.config.scene_name}'...")
                self.ws.call(requests.SetCurrentProgramScene(sceneName=self.config.scene_name))
            except Exception as e:
                logger.warning(f"Could not switch to scene '{self.config.scene_name}': {e}")

        logger.info("Sending StartRecord command to OBS Studio...")
        try:
            self.ws.call(requests.StartRecord())
            self.recording = True
            self.output_filepath = output_path
            logger.info("[SUCCESS] OBS recording started.")
        except Exception as e:
            # Check if already recording
            status = self.get_status()
            if status.get("outputActive"):
                logger.info("OBS was already recording.")
                self.recording = True
                self.output_filepath = output_path
            else:
                logger.error(f"Failed to start OBS recording: {e}")
                raise

    def stop_recording(self) -> str:
        """Send StopRecord to OBS Studio and retrieve output video path."""
        if not self.recording and self.ws is None:
            raise RuntimeError("OBS recording is not currently active.")

        self._ensure_connected()
        logger.info("Sending StopRecord command to OBS Studio...")

        saved_path = self.output_filepath
        try:
            res = self.ws.call(requests.StopRecord())
            self.recording = False

            # OBS v5 StopRecord returns outputPath in datain
            if hasattr(res, "datain") and "outputPath" in res.datain:
                saved_path = res.datain["outputPath"]
                logger.info(f"OBS finalized recording to: {saved_path}")
            elif hasattr(res, "getOutputPath"):
                saved_path = res.getOutputPath()
                logger.info(f"OBS finalized recording to: {saved_path}")

        except Exception as e:
            logger.warning(f"Error while stopping OBS recording: {e}")

        # Wait briefly for file to finalize on disk
        time.sleep(1.5)

        self.disconnect()
        return str(Path(saved_path).resolve()) if saved_path else "unknown_obs_output.mp4"

    def get_status(self) -> dict:
        """Query current OBS recording status."""
        self._ensure_connected()
        try:
            res = self.ws.call(requests.GetRecordStatus())
            data = getattr(res, "datain", {})
            return data
        except Exception as e:
            logger.warning(f"Could not retrieve OBS record status: {e}")
            return {}

    def disconnect(self) -> None:
        """Disconnect WebSocket connection gracefully."""
        if self.ws:
            try:
                self.ws.disconnect()
            except Exception:
                pass
            self.ws = None
            logger.info("Disconnected from OBS Studio WebSocket.")

