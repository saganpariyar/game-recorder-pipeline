"""Parse all 106 scenarios from RECORDING_SCENARIOS.md into structured SCENARIO_TRACKER.json."""

import re
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCENARIOS_MD = ROOT.parent / "bikkad" / "RECORDING_SCENARIOS.md"
TRACKER_JSON = ROOT / "SCENARIO_TRACKER.json"
PROGRESS_MD = ROOT / "SCENARIOS_PROGRESS.md"

def parse():
    if not SCENARIOS_MD.exists():
        print(f"Error: {SCENARIOS_MD} not found.")
        return

    text = SCENARIOS_MD.read_text(encoding="utf-8")
    
    # Split by Scenario blocks
    lines = text.splitlines()
    scenarios = []
    
    current_cat = "General"
    current_game = "Bikkad"
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Category headers
        if line.startswith("### 🔹 Category"):
            current_cat = line.replace("### 🔹 ", "").strip()
        elif line.startswith("# 👑 PART 1: BIKKAD"):
            current_game = "bikkad"
        elif line.startswith("# 🪙 PART 2: BINDI COAT"):
            current_game = "bindicoat"
        elif line.startswith("# 🎯 PART 3: TIKDI"):
            current_game = "tikdi"
        elif line.startswith("# 🃏 PART 4: JHUTHANIYA"):
            current_game = "jhuthaniya"
            
        # Match Scenario line: - **Scenario B01: The 4-Card Opening Double Sir**
        scen_match = re.match(r"^-\s*\*\*Scenario\s+([A-Z0-9]+):\s*(.*?)\*\*", line)
        if scen_match:
            s_id = scen_match.group(1).strip()
            s_title = scen_match.group(2).strip()
            
            action = ""
            audio_visual = ""
            url = ""
            
            # Read indented bullet points
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("-"):
                sub = lines[j].strip()
                if "*Action:*" in sub:
                    action = re.sub(r"^-\s*\*Action:\*\s*", "", sub).strip()
                elif "*Audio/Visual:*" in sub:
                    audio_visual = re.sub(r"^-\s*\*Audio/Visual:\*\s*", "", sub).strip()
                elif "*URL:*" in sub:
                    url_m = re.search(r"`([^`]+)`", sub)
                    if url_m:
                        url = url_m.group(1).strip()
                j += 1
            
            scenarios.append({
                "id": s_id,
                "game": current_game,
                "title": s_title,
                "category": current_cat,
                "action": action,
                "audio_visual": audio_visual,
                "url": url,
                "status": "PENDING", # PENDING, IN_PROGRESS, COMPLETED
                "youtube_url": None,
                "video_file": None,
                "recorded_at": None,
                "notes": None
            })
            i = j - 1
        i += 1
        
    print(f"Successfully parsed {len(scenarios)} scenarios from {SCENARIOS_MD.name}!")
    
    # Preserve existing progress if tracker already exists
    if TRACKER_JSON.exists():
        try:
            old_data = json.loads(TRACKER_JSON.read_text(encoding="utf-8"))
            old_map = {item["id"]: item for item in old_data.get("scenarios", [])}
            for s in scenarios:
                if s["id"] in old_map and old_map[s["id"]].get("status") == "COMPLETED":
                    s["status"] = "COMPLETED"
                    s["youtube_url"] = old_map[s["id"]].get("youtube_url")
                    s["video_file"] = old_map[s["id"]].get("video_file")
                    s["recorded_at"] = old_map[s["id"]].get("recorded_at")
        except Exception as e:
            print(f"Warning: could not merge previous tracker: {e}")
            
    tracker_obj = {
        "total_scenarios": len(scenarios),
        "completed_count": sum(1 for s in scenarios if s["status"] == "COMPLETED"),
        "scenarios": scenarios
    }
    
    TRACKER_JSON.write_text(json.dumps(tracker_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved tracker to {TRACKER_JSON}")
    
    # Generate Progress Markdown
    generate_progress_md(scenarios)

def generate_progress_md(scenarios):
    completed = [s for s in scenarios if s["status"] == "COMPLETED"]
    pending = [s for s in scenarios if s["status"] != "COMPLETED"]
    
    md_lines = [
        "# 🎬 Master Scenario Recording & YouTube Upload Tracker",
        f"**Total Scenarios:** {len(scenarios)} | **Completed:** {len(completed)} | **Remaining:** {len(pending)}\n",
        "## 📊 Progress Summary by Game",
    ]
    
    games = ["bikkad", "bindicoat", "tikdi", "jhuthaniya"]
    for g in games:
        g_scens = [s for s in scenarios if s["game"] == g]
        g_done = [s for s in g_scens if s["status"] == "COMPLETED"]
        md_lines.append(f"- **{g.upper()}:** {len(g_done)} / {len(g_scens)} Completed")
        
    md_lines.append("\n---\n")
    md_lines.append("## 🏆 Completed Scenarios (Uploaded to Sp Gaming Club)\n")
    if not completed:
        md_lines.append("_No scenarios completed yet._\n")
    else:
        md_lines.append("| ID | Game | Title | YouTube Video | Date |")
        md_lines.append("|:---|:---|:---|:---|:---|")
        for s in completed:
            yt = f"[{s['youtube_url']}]({s['youtube_url']})" if s['youtube_url'] else "N/A"
            md_lines.append(f"| **{s['id']}** | `{s['game']}` | {s['title']} | {yt} | {s.get('recorded_at') or 'Done'} |")
            
    md_lines.append("\n---\n")
    md_lines.append("## ⏳ Next Pending Scenarios (1-by-1 Queue)\n")
    md_lines.append("| ID | Game | Category | Title | Target URL |")
    md_lines.append("|:---|:---|:---|:---|:---|")
    for s in pending[:15]:  # Show next 15
        md_lines.append(f"| **{s['id']}** | `{s['game']}` | {s['category']} | {s['title']} | `{s['url']}` |")
        
    if len(pending) > 15:
        md_lines.append(f"\n_...and {len(pending) - 15} more queued scenarios._")
        
    PROGRESS_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Generated {PROGRESS_MD.name}")

if __name__ == "__main__":
    parse()

