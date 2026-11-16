# 🎮 Game Recorder & YouTube Automation Pipeline

An automated 3-stage pipeline designed to play games, capture high-definition video & audio, and upload automatically to YouTube via the YouTube Data API v3. Built with modularity to support **Bikkad** and any other web, desktop, or emulator game via configuration.

---

## 🏛️ Architecture Overview

```
1. Gameplay & Control         2. Screen/Audio Recording         3. YouTube Upload
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ Playwright / Puppeteer│ ──> │ OBS Studio (WebSocket)│ ──> │ YouTube Data API v3  │
│  or Python PyAutoGUI │     │  or FFmpeg / Playwright│     │ (OAuth2 Automation)  │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

| Stage | Responsibility | Supported Engines |
| :--- | :--- | :--- |
| **1. Gameplay & Control** | Launches game, clicks lobby buttons, plays turns, handles AI bots | **Playwright** (Web), **PyAutoGUI** (Desktop/Android Emulator), **Manual** |
| **2. Screen/Audio Recording** | Records crisp 60fps video with desktop & game audio | **OBS Studio v5 WebSocket**, **Playwright Native Video**, **FFmpeg** |
| **3. YouTube Upload** | Automated metadata, chunked resumable upload, thumbnail, OAuth2 token caching | **YouTube Data API v3** (with token auto-refresh), **Mock Uploader** |

---

## 📁 Project Structure

```
game-recorder-pipeline/
├── config/
│   ├── bikkad_web.yaml        # Config for Bikkad Web Game (http://127.0.0.1:8000)
│   ├── bikkad_emulator.yaml   # Config for Bikkad Android App on Emulator
│   └── default.yaml           # Generic template for any app or game
├── credentials/
│   ├── client_secret.json     # Google Cloud OAuth 2.0 Client credentials (downloaded)
│   ├── token.json             # Cached token generated automatically on 1st login
│   └── README.md              # Step-by-step Google Cloud OAuth setup guide
├── recordings/                # Saved gameplay video files (.mp4 / .webm)
├── src/
│   ├── controllers/           # Stage 1: PlaywrightBot, PyAutoGUIBot, Manual
│   ├── recorders/             # Stage 2: OBSRecorder, PlaywrightRecorder, FFmpeg, Mock
│   ├── uploader/              # Stage 3: YouTubeUploader, MockUploader
│   ├── config_loader.py       # Pydantic schema validation & YAML loader
│   └── pipeline.py            # Master Pipeline Orchestrator
├── main.py                    # Feature-rich CLI runner with rich formatting
├── run_pipeline.bat           # 1-Click interactive Windows launcher
└── requirements.txt           # Python package dependencies
```

---

## 🚀 Quick Start

### 1. Run Pipeline in Dry-Run Mode (Test without real upload)
```cmd
.venv\Scripts\python.exe main.py --dry-run
```

### 2. Run Bikkad Web Gameplay & Record Video
Ensure the Bikkad server is running (`http://127.0.0.1:8000` via `run_game.bat`), then run:
```cmd
.venv\Scripts\python.exe main.py --config config/bikkad_web.yaml --record-only
```
This will launch Chromium, start Bikkad, play solo against bots, capture 1080p video, and save it in `recordings/`.

### 3. Run with OBS Studio WebSocket Recording
1. Open OBS Studio on your PC.
2. Go to **Tools** > **WebSocket Server Settings** and check **Enable WebSocket Server** (Port: `4455`).
3. Test your connection:
   ```cmd
   .venv\Scripts\python.exe main.py --test-obs
   ```
4. Run pipeline using OBS recording:
   ```cmd
   .venv\Scripts\python.exe main.py --config config/bikkad_emulator.yaml
   ```

### 4. Enable YouTube Auto-Upload
1. Follow the quick guide in [`credentials/README.md`](credentials/README.md) to obtain `client_secret.json`.
2. Test YouTube authentication:
   ```cmd
   .venv\Scripts\python.exe main.py --test-youtube
   ```
3. Run the full pipeline with automatic upload:
   ```cmd
   .venv\Scripts\python.exe main.py --config config/bikkad_web.yaml
   ```

---

## ⚙️ Configuration Guide

Each app or game is defined by a YAML file in `config/`:

```yaml
app:
  name: "Bikkad Card Game"
  mode: "web"                  # Options: 'web', 'desktop', 'emulator', 'manual'
  url: "http://127.0.0.1:8000"
  game_type: "bikkad"          # 'bikkad', 'jhuthaniya', 'bindicoat', 'tikdi'
  player_name: "Desi Pro Bot"
  play_duration_seconds: 45
  turn_delay_ms: 1200
  auto_start_match: true

recorder:
  backend: "playwright"        # Options: 'playwright', 'obs', 'ffmpeg', 'mock'
  resolution_width: 1920
  resolution_height: 1080
  fps: 60
  output_dir: "recordings"
  filename_template: "{app_slug}_{game_type}_{timestamp}.mp4"

  obs:
    host: "localhost"
    port: 4455
    password: ""
    scene_name: ""

youtube:
  enabled: true
  privacy_status: "unlisted"   # 'private', 'unlisted', 'public'
  title_template: "Desi Card Games - {app_name} Gameplay ({date})"
  description_template: |
    Automated gameplay session of {app_name}.
    Recorded on: {date} {time}
  tags:
    - "Bikkad"
    - "Card Game"
    - "Gaming"
  category_id: "20"            # 20 = Gaming
  made_for_kids: false
```

---

## 🛠️ CLI Reference

```cmd
# List all configured apps
python main.py --list-configs

# Run custom duration
python main.py --config config/bikkad_web.yaml --duration 120

# Record only (do not upload)
python main.py --record-only

# Upload an existing video directly
python main.py --upload-only recordings/my_clip.mp4

# Test OBS Studio connection
python main.py --test-obs

# Test YouTube authentication
python main.py --test-youtube
```

