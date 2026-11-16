"""Scenario Manager for RECORDING_SCENARIOS.md automation and tracking."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("Pipeline.ScenarioManager")

PROJECT_ROOT = Path(__file__).parent.parent
TRACKER_JSON = PROJECT_ROOT / "SCENARIO_TRACKER.json"
PROGRESS_MD = PROJECT_ROOT / "SCENARIOS_PROGRESS.md"


class ScenarioManager:
    """Loads, queries, and updates scenario states in SCENARIO_TRACKER.json."""

    @staticmethod
    def load_tracker() -> Dict[str, Any]:
        """Load tracker data, or initialize if missing."""
        if not TRACKER_JSON.exists():
            from tools.parse_scenarios import parse
            parse()
        try:
            return json.loads(TRACKER_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to read {TRACKER_JSON}: {e}")
            return {"total_scenarios": 0, "completed_count": 0, "scenarios": []}

    @classmethod
    def get_scenario(cls, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve scenario by ID (e.g. 'B01', 'BC03', 'TK05')."""
        target = scenario_id.upper().strip()
        data = cls.load_tracker()
        for s in data.get("scenarios", []):
            if s["id"].upper() == target:
                return s
        return None

    @classmethod
    def get_next_pending_scenario(cls) -> Optional[Dict[str, Any]]:
        """Return the first uncompleted scenario in the queue."""
        data = cls.load_tracker()
        for s in data.get("scenarios", []):
            if s.get("status") != "COMPLETED":
                return s
        return None

    @classmethod
    def mark_completed(cls, scenario_id: str, youtube_url: str, video_path: str) -> bool:
        """Mark scenario as completed and regenerate SCENARIOS_PROGRESS.md."""
        target = scenario_id.upper().strip()
        data = cls.load_tracker()
        updated = False

        for s in data.get("scenarios", []):
            if s["id"].upper() == target:
                s["status"] = "COMPLETED"
                s["youtube_url"] = youtube_url
                s["video_file"] = str(Path(video_path).resolve())
                s["recorded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated = True
                break

        if updated:
            data["completed_count"] = sum(1 for s in data["scenarios"] if s.get("status") == "COMPLETED")
            TRACKER_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"[TRACKER] Scenario {target} marked as COMPLETED! ({data['completed_count']}/{data['total_scenarios']})")

            # Regenerate Markdown
            from tools.parse_scenarios import generate_progress_md
            generate_progress_md(data["scenarios"])
            return True

        return False

    @classmethod
    def list_scenarios(cls) -> List[Dict[str, Any]]:
        """Return full scenario list."""
        return cls.load_tracker().get("scenarios", [])

