#!/usr/bin/env python3
"""Batch generates 9:16 vertical YouTube Shorts for Scenarios B01-B06 and schedules them on Sp Gaming Club."""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_config
from src.shorts_generator import ShortsGenerator
from src.uploader.youtube_uploader import YouTubeUploader
from src.scenario_manager import ScenarioManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("BatchShortsRunner")

# Video mapping for Scenarios B01 through B06
SHORTS_QUEUE = [
    {
        "id": "B01",
        "video": PROJECT_ROOT / "recordings" / "bikkad_Kabir Singh_20261116_220630.mp4",
        "player": "Kabir Singh",
        "schedule": "2026-11-17T06:30:00Z"  # Tuesday Nov 17 @ 12:00 PM IST noon
    },
    {
        "id": "B02",
        "video": PROJECT_ROOT / "recordings" / "bikkad_Mogambo_20261116_221155.mp4",
        "player": "Mogambo",
        "schedule": "2026-11-18T06:30:00Z"  # Wednesday Nov 18 @ 12:00 PM IST noon
    },
    {
        "id": "B03",
        "video": PROJECT_ROOT / "recordings" / "bikkad_Pushpa Raj_20261116_221539.mp4",
        "player": "Pushpa Raj",
        "schedule": "2026-11-19T06:30:00Z"  # Thursday Nov 19 @ 12:00 PM IST noon
    },
    {
        "id": "B04",
        "video": PROJECT_ROOT / "recordings" / "bikkad_Bajirao_20261116_221821.mp4",
        "player": "Bajirao",
        "schedule": "2026-11-20T06:30:00Z"  # Friday Nov 20 @ 12:00 PM IST noon
    },
    {
        "id": "B05",
        "video": PROJECT_ROOT / "recordings" / "bikkad_Mogambo_20261116_222137.mp4",
        "player": "Mogambo",
        "schedule": "2026-11-21T06:30:00Z"  # Saturday Nov 21 @ 12:00 PM IST noon
    },
    {
        "id": "B06",
        "video": PROJECT_ROOT / "recordings" / "bikkad_Chulbul Pandey_20261116_222351.mp4",
        "player": "Chulbul Pandey",
        "schedule": "2026-11-22T06:30:00Z"  # Sunday Nov 22 @ 12:00 PM IST noon
    },
]

def main():
    config_path = PROJECT_ROOT / "config" / "bikkad_web.yaml"
    config = load_config(config_path)

    shorts_gen = ShortsGenerator()
    uploader = YouTubeUploader(config.youtube)
    uploader.authenticate()

    results = []

    for item in SHORTS_QUEUE:
        sc_id = item["id"]
        v_path = Path(item["video"])
        player_name = item["player"]
        schedule_ts = item["schedule"]

        logger.info(f"\n========================================================")
        logger.info(f"PROCESSING YOUTUBE SHORT: {sc_id} | Scheduled: {schedule_ts}")
        logger.info(f"Source video: {v_path}")
        logger.info(f"========================================================")

        if not v_path.is_file():
            logger.error(f"Source video {v_path} does not exist! Skipping.")
            continue

        sc_data = ScenarioManager.get_scenario(sc_id) or {}
        sc_title = sc_data.get("title", f"Scenario {sc_id}")

        # 1. Generate 9:16 vertical Short
        logger.info(f"Converting to 9:16 vertical Short (1080x1920) with SP Gaming Club branding...")
        short_path = shorts_gen.convert_to_short(
            video_path=str(v_path),
            scenario_id=sc_id,
            scenario_title=sc_title,
            player_name=player_name,
            made_for_kids=config.youtube.made_for_kids
        )

        if not short_path or not Path(short_path).is_file():
            logger.error(f"Failed to generate Short for {sc_id}")
            continue

        file_size_mb = Path(short_path).stat().st_size / (1024 * 1024)
        logger.info(f"[SUCCESS] Short generated: {short_path} ({file_size_mb:.2f} MB)")

        # 2. Upload to YouTube Shorts
        short_title = f"🎮 {sc_id}: {player_name} {sc_title}! #Shorts | Sp Gaming Club"
        if len(short_title) > 95:
            short_title = f"🎮 {sc_id}: {sc_title}! #Shorts | Sp Gaming Club"
        if len(short_title) > 95:
            short_title = short_title[:90] + " #Shorts"

        description = (
            f"🎯 {sc_id}: {sc_title}\n"
            f"Player: {player_name} in Bikkad (Indian Court Piece / Double Sir)!\n\n"
            f"Full match video releases today at 6:00 PM IST on Sp Gaming Club.\n\n"
            f"✨ Family-Friendly Indian Card Game | Subscribe to @sptalks9129\n\n"
            f"#Shorts #Bikkad #SPGamingClub #CourtPiece #CardGame #DesiGaming #Gaming #ShortsFeed"
        )

        tags = [
            "Shorts", "YouTube Shorts", "Bikkad", "Court Piece", "Sp Gaming Club",
            "Desi Gaming", "Card Game", "Hokm", "Strategy Games", "Bollywood Gaming", "Family Fun"
        ]

        logger.info(f"Uploading Short to YouTube with schedule: {schedule_ts}...")
        try:
            yt_url = uploader.upload(
                video_path=short_path,
                title=short_title,
                description=description,
                tags=tags,
                privacy_status="private",
                category_id="20",
                made_for_kids=config.youtube.made_for_kids,
                thumbnail_path=None,
                publish_at=schedule_ts
            )
            logger.info(f"[SUCCESS] Short uploaded! URL: {yt_url}")
            results.append({
                "id": sc_id,
                "title": sc_title,
                "url": yt_url,
                "scheduled": schedule_ts,
                "status": "SUCCESS"
            })
        except Exception as e:
            logger.error(f"Failed to upload Short for {sc_id}: {e}")
            results.append({
                "id": sc_id,
                "title": sc_title,
                "url": None,
                "scheduled": schedule_ts,
                "status": f"FAILED: {e}"
            })

    logger.info("\n================ ALL SHORTS BATCH RUNS COMPLETE ================")
    for r in results:
        logger.info(f"Short {r['id']} [{r['status']}]: {r.get('url')} (Scheduled: {r['scheduled']})")

if __name__ == "__main__":
    main()
