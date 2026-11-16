"""Configuration loader and Pydantic schema validation for the recording and upload pipeline."""

import os
from pathlib import Path
from typing import List, Optional, Literal, Dict, Any
import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    name: str = Field(default="Bikkad Card Game", description="Human-readable name of the target application")
    mode: Literal["web", "desktop", "emulator", "manual"] = Field(
        default="web",
        description="Type of application interaction mode"
    )
    url: Optional[str] = Field(default="http://127.0.0.1:8000", description="Target web URL if mode is 'web'")
    window_title: Optional[str] = Field(default=None, description="Window title match pattern for desktop/emulator mode")
    launch_command: Optional[str] = Field(default=None, description="Optional command to launch app/server prior to recording")
    game_type: str = Field(default="bikkad", description="Card game variation: bikkad, jhuthaniya, bindicoat, tikdi, gadhabaji, sarkari")
    player_name: str = Field(default="Chulbul Pandey", description="Player name used in the lobby")
    player_names: Optional[List[str]] = Field(default=None, description="Pool of Bollywood character names to pick from")
    play_duration_seconds: int = Field(default=180, description="Max gameplay duration in seconds")
    deals_target: int = Field(default=2, description="Target complete deals for full match in record mode")
    play_until_match_over: bool = Field(default=True, description="Stop recording automatically when full match finishes")
    turn_delay_ms: int = Field(default=1200, description="Delay between automated card clicks (ms)")
    auto_start_match: bool = Field(default=True, description="Automatically click Start Match in lobby")


class OBSConfig(BaseModel):
    host: str = Field(default="localhost", description="OBS WebSocket server host")
    port: int = Field(default=4455, description="OBS WebSocket server port (v5 default: 4455)")
    password: str = Field(default="", description="OBS WebSocket server password")
    scene_name: Optional[str] = Field(default=None, description="Optional scene to activate during recording")


class FFmpegConfig(BaseModel):
    ffmpeg_path: str = Field(default="ffmpeg", description="Path or command for ffmpeg binary")
    video_device: str = Field(default="desktop", description="Screen grab device (e.g. desktop for gdigrab)")
    audio_device: Optional[str] = Field(default=None, description="DirectShow audio device name if audio recording is desired")
    framerate: int = Field(default=30, description="FFmpeg recording framerate")


class RecorderConfig(BaseModel):
    backend: Literal["playwright", "obs", "ffmpeg", "mock"] = Field(
        default="playwright",
        description="Screen recording backend"
    )
    resolution_width: int = Field(default=1920, description="Target video width")
    resolution_height: int = Field(default=1080, description="Target video height")
    fps: int = Field(default=60, description="Target video framerate")
    output_dir: str = Field(default="recordings", description="Directory to store recorded video files")
    filename_template: str = Field(
        default="{app_slug}_{timestamp}.mp4",
        description="Pattern for output video files"
    )
    obs: OBSConfig = Field(default_factory=OBSConfig)
    ffmpeg: FFmpegConfig = Field(default_factory=FFmpegConfig)


class YouTubeConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable automated YouTube upload")
    client_secrets_file: str = Field(
        default="credentials/client_secret.json",
        description="Path to OAuth 2.0 client secrets JSON downloaded from Google Cloud Console"
    )
    token_cache_file: str = Field(
        default="credentials/token.json",
        description="Path where OAuth tokens are cached for automated silent refresh"
    )
    privacy_status: Literal["private", "unlisted", "public"] = Field(
        default="unlisted",
        description="Video privacy setting on YouTube"
    )
    title_template: str = Field(
        default="🔥 {player_name} Ka Asli {app_name} Challenge! Royal Trump Showdown | {date}",
        description="Template for YouTube video title"
    )
    title_templates: Optional[List[str]] = Field(
        default=None,
        description="Optional list of catchy Hinglish title templates (randomly selected each run)"
    )
    description_template: str = Field(
        default=(
            "Automated gameplay recording of {app_name} ({game_type}).\n\n"
            "Captured and uploaded automatically via Game Recorder & YouTube Pipeline.\n"
            "Game: {app_name}\n"
            "Session Date: {date}\n\n"
            "#gaming #gameplay #desicardgames #bikkad"
        ),
        description="Template for YouTube video description"
    )
    tags: List[str] = Field(
        default=["Bikkad", "Card Game", "Desi Card Games", "Gameplay", "Bots", "AI"],
        description="List of YouTube tags"
    )
    category_id: str = Field(default="20", description="YouTube Category ID (20 = Gaming)")
    made_for_kids: bool = Field(default=False, description="COPPA Self-declared made for kids flag")
    thumbnail_path: Optional[str] = Field(default=None, description="Optional custom thumbnail image path (.jpg/.png)")
    auto_generate_thumbnail: bool = Field(default=True, description="Automatically generate high-impact 1280x720 thumbnail for each video")
    target_channel_name: Optional[str] = Field(default="The MK Chapter", description="Expected channel name for sanity check")
    channel_url: Optional[str] = Field(default="https://www.youtube.com/@themkchapter", description="YouTube channel URL")


class PipelineConfig(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    recorder: RecorderConfig = Field(default_factory=RecorderConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)


def load_config(config_path: str | Path) -> PipelineConfig:
    """Load and validate pipeline configuration from a YAML file."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    return PipelineConfig(**raw_data)


def save_config(config: PipelineConfig, output_path: str | Path) -> None:
    """Save a PipelineConfig instance to a YAML file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)

