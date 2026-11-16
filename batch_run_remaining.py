#!/usr/bin/env python3
"""Batch runner to record and schedule scenarios B02 through B06 for daily release."""

import sys
import logging
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_config
from src.pipeline import PipelineOrchestrator
from src.scenario_manager import ScenarioManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("BatchRunner")

SCENARIOS_QUEUE = [
    ("B02", "2026-11-18T12:30:00Z"), # Wednesday Nov 18 at 6:00 PM IST
    ("B03", "2026-11-19T12:30:00Z"), # Thursday Nov 19 at 6:00 PM IST
    ("B04", "2026-11-20T12:30:00Z"), # Friday Nov 20 at 6:00 PM IST
    ("B05", "2026-11-21T12:30:00Z"), # Saturday Nov 21 at 6:00 PM IST
    ("B06", "2026-11-22T12:30:00Z"), # Sunday Nov 22 at 6:00 PM IST
]

def main():
    config_path = PROJECT_ROOT / "config" / "bikkad_web.yaml"
    config = load_config(config_path)

    results = []
    for sc_id, schedule_ts in SCENARIOS_QUEUE:
        logger.info(f"\n========================================================")
        logger.info(f"PROCESSING SCENARIO: {sc_id} | Scheduled: {schedule_ts}")
        logger.info(f"========================================================")
        scenario = ScenarioManager.get_scenario(sc_id)
        if not scenario:
            logger.error(f"Scenario '{sc_id}' not found in tracker! Skipping.")
            continue

        orchestrator = PipelineOrchestrator(
            config=config,
            scenario=scenario,
            schedule_publish_at=schedule_ts
        )
        res = orchestrator.run()
        results.append({
            "scenario": sc_id,
            "scheduled": schedule_ts,
            "success": res.get("success"),
            "youtube_url": res.get("youtube_url"),
            "video_path": res.get("video_path")
        })

    logger.info("\n================ ALL BATCH RUNS COMPLETE ================")
    for r in results:
        status_str = "SUCCESS" if r["success"] else "FAILED"
        logger.info(f"Scenario {r['scenario']} [{status_str}]: {r.get('youtube_url')} (Scheduled: {r['scheduled']})")

if __name__ == "__main__":
    main()
