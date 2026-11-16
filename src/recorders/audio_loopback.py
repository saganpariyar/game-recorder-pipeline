"""Windows WASAPI Loopback Audio Recorder & FFmpeg Video-Audio Muxer.

Captures system audio (game sound effects, card deals, trump reveals, and Marwari/Hindi speech)
directly from the default playback device via WASAPI loopback, and merges it with the recorded video.
"""

import os
import time
import logging
import threading
import subprocess
from pathlib import Path
from typing import Optional, List
import numpy as np

logger = logging.getLogger("Pipeline.AudioLoopback")


class AudioLoopbackRecorder:
    """Records Windows default speaker output using WASAPI Loopback (soundcard + soundfile)."""

    def __init__(self, samplerate: int = 44100):
        self.samplerate = samplerate
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frames: List[np.ndarray] = []
        self.output_wav_path: Optional[str] = None
        self.mic = None

    def start(self, output_wav_path: str) -> bool:
        """Start recording loopback audio in a background thread."""
        try:
            import soundcard as sc
            spk = sc.default_speaker()
            self.mic = sc.get_microphone(id=str(spk.name), include_loopback=True)
            logger.info(f"Loopback audio capture bound to speaker: '{spk.name}'")
        except Exception as e:
            logger.warning(f"Could not initialize WASAPI loopback audio capture: {e}")
            return False

        self.output_wav_path = output_wav_path
        self.frames = []
        self.running = True

        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()
        logger.info(f"Background audio recording thread started (target: {output_wav_path})")
        return True

    def _record_loop(self) -> None:
        """Background thread loop capturing PCM audio frames with auto-reconnect."""
        chunk_size = 4410  # 100ms chunks at 44.1kHz
        while self.running:
            try:
                with self.mic.recorder(samplerate=self.samplerate, channels=2) as recorder:
                    while self.running:
                        try:
                            data = recorder.record(numframes=chunk_size)
                            if data is not None and len(data) > 0:
                                self.frames.append(data)
                        except Exception as ex:
                            if self.running:
                                time.sleep(0.02)
                                break  # Break inner loop to re-enter recorder context
            except Exception as e:
                if self.running:
                    time.sleep(0.05)

    def stop(self) -> Optional[str]:
        """Stop audio recording and write collected PCM data to WAV file."""
        if not self.running:
            return None

        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)

        if not self.frames:
            logger.warning("No audio frames were captured during recording session.")
            return None

        try:
            import soundfile as sf
            full_audio = np.concatenate(self.frames, axis=0)
            duration_s = round(len(full_audio) / self.samplerate, 2)
            max_amp = float(np.max(np.abs(full_audio)))

            # Automatic Peak Normalization: ensure audio is studio-clear (-1dB peak)
            if max_amp > 0.001:
                target_peak = 0.90
                gain = min(30.0, target_peak / max_amp)
                full_audio = full_audio * gain
                max_amp = float(np.max(np.abs(full_audio)))
                logger.info(f"Audio normalized: amplified by {gain:.2f}x to peak amplitude {round(max_amp, 3)}")

            out_path = Path(self.output_wav_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(out_path), full_audio, self.samplerate)

            logger.info(
                f"[SUCCESS] Recorded {duration_s}s audio to '{out_path.name}' "
                f"(peak amplitude: {round(max_amp, 3)})"
            )
            return str(out_path.resolve())
        except Exception as e:
            logger.warning(f"Failed to write audio WAV file: {e}")
            return None

    @staticmethod
    def mux_video_audio(video_path: str, audio_path: str, output_path: str) -> bool:
        """Mux video track with audio track using bundled imageio-ffmpeg."""
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as e:
            logger.error(f"FFmpeg binary not found: {e}")
            return False

        logger.info(f"Muxing video ({Path(video_path).name}) + audio ({Path(audio_path).name}) -> {Path(output_path).name}...")

        # Temp destination if input and output video paths are identical
        final_dest = Path(output_path).resolve()
        is_same_file = Path(video_path).resolve() == final_dest
        temp_dest = final_dest.with_suffix(".muxed.mp4") if is_same_file else final_dest

        # Fast stream copy first (map video from input 0, audio from input 1)
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(Path(video_path).resolve()),
            "-i", str(Path(audio_path).resolve()),
            "-map", "0:v:0",
            "-map", "1:a:0?",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            str(temp_dest)
        ]

        res = subprocess.run(cmd, capture_output=True, text=True)

        # Fallback to re-encoding video if stream copy fails
        if res.returncode != 0:
            logger.warning(f"Fast stream copy mux failed ({res.stderr.strip()[:120]}). Falling back to x264 re-encode...")
            cmd = [
                ffmpeg_exe, "-y",
                "-i", str(Path(video_path).resolve()),
                "-i", str(Path(audio_path).resolve()),
                "-map", "0:v:0",
                "-map", "1:a:0?",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                str(temp_dest)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode == 0 and temp_dest.exists():
            if is_same_file:
                # Replace original file with muxed file
                temp_dest.replace(final_dest)
            logger.info(f"[SUCCESS] Audio + Video successfully merged into: {final_dest}")

            # Clean up temporary wav file
            try:
                Path(audio_path).unlink(missing_ok=True)
            except Exception:
                pass

            return True
        else:
            logger.error(f"FFmpeg muxing failed: {res.stderr}")
            return False

