#!/usr/bin/env python3
"""Game Recorder & YouTube Automation Pipeline CLI."""

import sys
import argparse
import logging
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_loader import load_config, PipelineConfig
from src.pipeline import PipelineOrchestrator
from src.recorders.obs_recorder import OBSRecorder
from src.uploader.youtube_uploader import YouTubeUploader

console = Console()


def setup_logging(verbose: bool = False):
    """Configure terminal logging format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def list_configs():
    """Display available configuration presets."""
    config_dir = PROJECT_ROOT / "config"
    table = Table(title="Available App Configurations", show_header=True, header_style="bold cyan")
    table.add_column("Filename", style="green")
    table.add_column("App Name", style="bold white")
    table.add_column("Mode", style="yellow")
    table.add_column("Recorder", style="magenta")

    for cfg_file in config_dir.glob("*.yaml"):
        try:
            cfg = load_config(cfg_file)
            table.add_row(cfg_file.name, cfg.app.name, cfg.app.mode, cfg.recorder.backend)
        except Exception:
            table.add_row(cfg_file.name, "Error reading config", "-", "-")

    console.print(table)


def test_obs_connection(config_path: Path):
    """Test connection to OBS Studio WebSocket server."""
    cfg = load_config(config_path)
    console.print(f"[bold cyan]Testing OBS Studio WebSocket connection...[/bold cyan]")
    console.print(f"Host: [yellow]{cfg.recorder.obs.host}:{cfg.recorder.obs.port}[/yellow]")

    try:
        recorder = OBSRecorder(cfg.recorder.obs)
        recorder._ensure_connected()
        status = recorder.get_status()
        console.print("[bold green]✔ Successfully connected to OBS Studio![/bold green]")
        console.print(f"Record Status: {status}")
        recorder.disconnect()
    except Exception as e:
        console.print(f"[bold red]✘ OBS Connection Failed:[/bold red] {e}")


def test_youtube_auth(config_path: Path):
    """Test YouTube OAuth2 authentication flow and display channel name."""
    cfg = load_config(config_path)
    console.print(f"[bold cyan]Testing YouTube Data API v3 Authentication...[/bold cyan]")

    try:
        uploader = YouTubeUploader(cfg.youtube)
        service = uploader.authenticate()
        channels_response = service.channels().list(mine=True, part="snippet,statistics").execute()
        items = channels_response.get("items", [])
        if items:
            channel = items[0]
            title = channel["snippet"]["title"]
            subs = channel["statistics"].get("subscriberCount", "0")
            console.print(f"[bold green]✔ Authenticated as YouTube Channel:[/bold green] [bold yellow]{title}[/bold yellow] ({subs} subscribers)")
            
            target = cfg.youtube.target_channel_name
            if target and target.lower() in title.lower():
                console.print(f"[bold green]🎯 Verified: Channel matches configured target '{target}'![/bold green]")
            elif target:
                console.print(f"[yellow]⚠️ Notice: Authenticated channel is '{title}', but config expects '{target}'.[/yellow]")
                console.print(f"[dim]If you intended to upload to '{target}', delete 'credentials/token.json' and select '{target}' on the Google login prompt.[/dim]")
        else:
            console.print("[bold green]✔ Authenticated with YouTube, but no public channel found on this Google account.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]✘ YouTube Authentication Failed:[/bold red] {e}")


def upload_single_video(config_path: Path, video_file: str):
    """Directly upload a video file to YouTube using configuration templates."""
    import random
    from src.thumbnail_generator import ThumbnailGenerator

    cfg = load_config(config_path)
    uploader = YouTubeUploader(cfg.youtube)

    now_str = datetime_str()
    context_vars = {
        "app_name": cfg.app.name,
        "app_slug": "manual_upload",
        "game_type": cfg.app.game_type,
        "game_title": cfg.app.game_type.title(),
        "game_upper": cfg.app.game_type.upper(),
        "player_name": cfg.app.player_name,
        "date": now_str[:10],
        "time": now_str[11:],
        "timestamp": now_str.replace("-", "").replace(":", "").replace(" ", "_"),
    }

    if cfg.youtube.title_templates:
        selected_tmpl = random.choice(cfg.youtube.title_templates)
    else:
        selected_tmpl = cfg.youtube.title_template
    title = selected_tmpl.format(**context_vars)
    description = cfg.youtube.description_template.format(**context_vars)

    thumbnail_path = cfg.youtube.thumbnail_path
    if not thumbnail_path and cfg.youtube.auto_generate_thumbnail:
        try:
            tg = ThumbnailGenerator(output_dir=str(PROJECT_ROOT / "recordings" / "thumbnails"))
            thumbnail_path = tg.generate(
                game_title=cfg.app.game_type.upper(),
                player_name=cfg.app.player_name,
                filename_prefix="thumb_reupload"
            )
            console.print(f"[bold cyan]Custom thumbnail generated:[/bold cyan] {thumbnail_path}")
        except Exception as e:
            console.print(f"[yellow]Could not generate thumbnail:[/yellow] {e}")

    console.print(f"[bold cyan]Uploading video directly to YouTube:[/bold cyan] {video_file}")
    url = uploader.upload(
        video_path=video_file,
        title=title,
        description=description,
        tags=cfg.youtube.tags,
        privacy_status=cfg.youtube.privacy_status,
        category_id=cfg.youtube.category_id,
        made_for_kids=cfg.youtube.made_for_kids,
        thumbnail_path=thumbnail_path
    )
    console.print(f"[bold green]✔ Upload Complete![/bold green] URL: [link={url}]{url}[/link]")


def datetime_str() -> str:
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    parser = argparse.ArgumentParser(
        description="🎮 Game Recorder & YouTube Automation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                      # Run with default config (config/bikkad_web.yaml)
  python main.py --config config/bikkad_web.yaml      # Run specific app config
  python main.py --dry-run                            # Test pipeline with mock recorder and mock uploader
  python main.py --record-only                        # Record gameplay session without uploading to YouTube
  python main.py --duration 120                       # Override play duration to 120 seconds
  python main.py --test-obs                           # Test OBS Studio WebSocket connection
  python main.py --test-youtube                       # Test YouTube OAuth authorization
  python main.py --upload-only recordings/game.mp4    # Upload an existing video to YouTube
        """
    )

    parser.add_argument(
        "-c", "--config",
        default="config/bikkad_web.yaml",
        help="Path to YAML configuration file (default: config/bikkad_web.yaml)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Override gameplay duration in seconds"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate recording and uploading without touching real services"
    )
    parser.add_argument(
        "--record-only",
        action="store_true",
        help="Record gameplay and save video locally without uploading to YouTube"
    )
    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="List all preset application configuration files"
    )
    parser.add_argument(
        "--test-obs",
        action="store_true",
        help="Test connection to OBS Studio WebSocket v5"
    )
    parser.add_argument(
        "--test-youtube",
        action="store_true",
        help="Verify YouTube Data API v3 OAuth credentials"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Execute a specific scenario from RECORDING_SCENARIOS.md (e.g. B01, BC03, TK01)"
    )
    parser.add_argument(
        "--next-scenario",
        action="store_true",
        help="Automatically record the next pending scenario in the queue"
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Display master progress table of completed and pending scenarios"
    )
    parser.add_argument(
        "--upload-only",
        type=str,
        default=None,
        help="Upload an existing video file to YouTube directly"
    )
    parser.add_argument(
        "--schedule",
        type=str,
        default=None,
        help="Schedule video release at RFC 3339 timestamp (e.g. 2026-11-16T12:30:00Z)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable detailed debug logs"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.list_configs:
        list_configs()
        return

    if args.list_scenarios:
        from src.scenario_manager import ScenarioManager
        scenarios = ScenarioManager.list_scenarios()
        completed = [s for s in scenarios if s.get("status") == "COMPLETED"]
        pending = [s for s in scenarios if s.get("status") != "COMPLETED"]

        table = Table(title=f"🎬 Master Scenarios Tracker ({len(completed)}/{len(scenarios)} Completed)")
        table.add_column("ID", style="bold cyan", width=6)
        table.add_column("Game", style="yellow", width=12)
        table.add_column("Title", style="white")
        table.add_column("Status", style="bold")
        table.add_column("YouTube Link", style="green")

        for s in scenarios:
            st = "[bold green]COMPLETED[/bold green]" if s.get("status") == "COMPLETED" else "[dim]PENDING[/dim]"
            yt = s.get("youtube_url") or "-"
            table.add_row(s["id"], s["game"], s["title"], st, yt)

        console.print(table)
        return

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (PROJECT_ROOT / config_path).resolve()

    if args.test_obs:
        test_obs_connection(config_path)
        return

    if args.test_youtube:
        test_youtube_auth(config_path)
        return

    if args.upload_only:
        upload_single_video(config_path, args.upload_only)
        return

    # Resolve target scenario if specified
    target_scenario = None
    from src.scenario_manager import ScenarioManager
    if args.scenario:
        target_scenario = ScenarioManager.get_scenario(args.scenario)
        if not target_scenario:
            console.print(f"[bold red]Scenario '{args.scenario}' not found in tracker![/bold red]")
            sys.exit(1)
    elif args.next_scenario:
        target_scenario = ScenarioManager.get_next_pending_scenario()
        if not target_scenario:
            console.print(f"[bold green]🎉 All master scenarios are already completed![/bold green]")
            return

    # Load configuration
    try:
        config = load_config(config_path)
    except Exception as e:
        console.print(f"[bold red]Failed to load configuration:[/bold red] {e}")
        sys.exit(1)

    if args.duration is not None:
        config.app.play_duration_seconds = args.duration

    # Welcome Banner
    scenario_info = ""
    if target_scenario:
        scenario_info = (
            f"\nScenario:   [bold green]{target_scenario['id']}: {target_scenario['title']}[/bold green]\n"
            f"Category:   [italic]{target_scenario.get('category', '')}[/italic]"
        )

    banner = (
        f"[bold cyan]Game Recorder & YouTube Automation Pipeline[/bold cyan]\n"
        f"Target App: [yellow]{config.app.name}[/yellow] ({config.app.mode})\n"
        f"Recorder:   [magenta]{config.recorder.backend.upper()}[/magenta] "
        f"({config.recorder.resolution_width}x{config.recorder.resolution_height} @ {config.recorder.fps}fps)\n"
        f"YouTube:    [green]{'ENABLED' if config.youtube.enabled and not args.record_only else 'DISABLED / RECORD-ONLY'}[/green] "
        f"(Privacy: {config.youtube.privacy_status})\n"
        f"Duration:   [white]{config.app.play_duration_seconds} seconds[/white]"
        f"{scenario_info}"
    )
    console.print(Panel(banner, title="🎮 Pipeline Launch", border_style="cyan"))

    orchestrator = PipelineOrchestrator(
        config=config,
        dry_run=args.dry_run,
        record_only=args.record_only,
        scenario=target_scenario,
        schedule_publish_at=args.schedule
    )

    result = orchestrator.run()

    if result["success"]:
        console.print(f"\n[bold green]✔ Pipeline Run Completed Successfully![/bold green]")
        if result.get("video_path"):
            console.print(f"🎬 Video Saved: [bold white]{result['video_path']}[/bold white]")
        if result.get("youtube_url"):
            console.print(f"🚀 YouTube Video: [bold yellow][link={result['youtube_url']}]{result['youtube_url']}[/link][/bold yellow]")
    else:
        console.print(f"\n[bold red]✘ Pipeline Failed:[/bold red] {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()

