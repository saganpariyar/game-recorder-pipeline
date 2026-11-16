#!/usr/bin/env python3
"""Execute Scenario B07: Record gameplay, normalize audio, generate thumbnail, create 9:16 Short, and schedule both."""

import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_config
from src.pipeline import PipelineOrchestrator
from src.scenario_manager import ScenarioManager
from src.shorts_generator import ShortsGenerator
from src.uploader.youtube_uploader import YouTubeUploader

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("ScenarioB07Runner")

def main():
    config_path = PROJECT_ROOT / "config" / "bikkad_web.yaml"
    config = load_config(config_path)

    scenario = ScenarioManager.get_scenario("B07")
    if not scenario:
        logger.error("Scenario B07 not found in tracker!")
        sys.exit(1)

    logger.info("======================================================================")
    logger.info("STARTING EXECUTION FOR SCENARIO B07: The Denied Double Sir")
    logger.info(f"Target Channel: {config.youtube.target_channel_name}")
    logger.info(f"Made for Kids:  {config.youtube.made_for_kids}")
    logger.info("======================================================================")

    # Monday, Nov 23 @ 6:00 PM IST (12:30 UTC)
    video_schedule = "2026-11-23T12:30:00Z"
    # Monday, Nov 23 @ 12:00 PM IST noon (06:30 UTC)
    short_schedule = "2026-11-23T06:30:00Z"

    # Step 1: Run Recording Pipeline for Full-Length Match
    orchestrator = PipelineOrchestrator(
        config=config,
        scenario=scenario,
        schedule_publish_at=video_schedule
    )
    res = orchestrator.run()

    video_path = res.get("video_path")
    youtube_url = res.get("youtube_url")
    player_name = orchestrator.context_vars.get("player_name", "Kabir Singh")

    logger.info(f"\n[STAGE 1 RESULT] Full Video Path: {video_path}")
    logger.info(f"[STAGE 1 RESULT] YouTube URL:       {youtube_url or 'Queued on disk (quota)'}")

    if not video_path or not Path(video_path).is_file():
        logger.error("Video recording file was not created. Aborting Shorts generation.")
        sys.exit(1)

    # Step 2: Generate 9:16 Vertical Short
    logger.info("\n>>> STAGE 4: Generating 9:16 Vertical YouTube Short (1080x1920)...")
    shorts_gen = ShortsGenerator()
    short_path = shorts_gen.convert_to_short(
        video_path=video_path,
        scenario_id="B07",
        scenario_title=scenario["title"],
        player_name=player_name,
        made_for_kids=config.youtube.made_for_kids
    )

    short_youtube_url = None
    if short_path and Path(short_path).is_file():
        file_size_mb = Path(short_path).stat().st_size / (1024 * 1024)
        logger.info(f"[SUCCESS] Short generated at: {short_path} ({file_size_mb:.2f} MB)")

        # Step 3: Upload Short to YouTube
        uploader = YouTubeUploader(config.youtube)
        short_title = f"🎮 B07: {player_name} The Denied Double Sir! #Shorts | Sp Gaming Club"
        if len(short_title) > 95:
            short_title = "🎮 B07: The Denied Double Sir! #Shorts | Sp Gaming Club"

        description = (
            f"🎯 B07: The Denied Double Sir (Interception)\n"
            f"Player: {player_name} in Bikkad (Indian Court Piece / Double Sir)!\n\n"
            f"Full match video releases Monday, Nov 23 at 6:00 PM IST on Sp Gaming Club.\n\n"
            f"✨ Family-Friendly Indian Card Game (All Ages) | Subscribe to @sptalks9129\n\n"
            f"#Shorts #Bikkad #SPGamingClub #CourtPiece #CardGame #DesiGaming #Gaming #ShortsFeed"
        )

        tags = [
            "Shorts", "YouTube Shorts", "Bikkad", "Court Piece", "Sp Gaming Club",
            "Desi Gaming", "Card Game", "Hokm", "Strategy Games", "Bollywood Gaming", "All Ages", "Family Fun"
        ]

        logger.info(f"Uploading Short to YouTube with schedule: {short_schedule}...")
        try:
            short_youtube_url = uploader.upload(
                video_path=short_path,
                title=short_title,
                description=description,
                tags=tags,
                privacy_status="private",
                category_id="20",
                made_for_kids=config.youtube.made_for_kids,
                thumbnail_path=None,
                publish_at=short_schedule
            )
            logger.info(f"[SUCCESS] Short uploaded: {short_youtube_url}")
        except Exception as e:
            logger.error(f"YouTube upload for Short encountered an error: {e}")

    logger.info("\n" + "=" * 70)
    logger.info("SCENARIO B07 EXECUTION SUMMARY")
    logger.info(f"Full Video File:  {video_path}")
    logger.info(f"Full Video URL:   {youtube_url or 'Saved on disk / Pending quota reset'}")
    logger.info(f"Short Video File: {short_path}")
    logger.info(f"Short Video URL:  {short_youtube_url or 'Saved on disk / Pending quota reset'}")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
