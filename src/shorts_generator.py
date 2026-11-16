"""YouTube Shorts (9:16 Vertical 1080x1920) Generator for SP Gaming Club."""

import subprocess
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class ShortsGenerator:
    """Converts 16:9 widescreen gameplay recordings into broadcast-grade 9:16 vertical YouTube Shorts."""

    def __init__(self, output_dir: Optional[str] = None):
        self.width = 1080
        self.height = 1920
        self.output_dir = Path(output_dir or (PROJECT_ROOT / "recordings" / "shorts"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.ImageFont:
        font_dir = Path("C:/Windows/Fonts")
        candidates = ["arialbd.ttf" if bold else "arial.ttf", "segoeuib.ttf", "calibrib.ttf"]
        for f in candidates:
            fp = font_dir / f
            if fp.exists():
                try:
                    return ImageFont.truetype(str(fp), size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def generate_overlay(
        self,
        scenario_id: str,
        scenario_title: str,
        player_name: Optional[str] = None,
        made_for_kids: bool = True
    ) -> Path:
        """Create a transparent 1080x1920 PNG overlay with SP Gaming Club branding."""
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        gold = (245, 197, 24, 255)
        navy_dark = (12, 16, 34, 240)

        # 1. Top Section Banner (y: 0 - 620)
        draw.rectangle([0, 0, self.width, 620], fill=navy_dark)
        draw.rectangle([0, 614, self.width, 620], fill=gold)

        # 2. Bottom Section Banner (y: 1296 - 1920)
        draw.rectangle([0, 1296, self.width, self.height], fill=navy_dark)
        draw.rectangle([0, 1296, self.width, 1302], fill=gold)

        font_brand = self._get_font(52, bold=True)
        font_title = self._get_font(40, bold=True)
        font_sub = self._get_font(32, bold=True)
        font_tag = self._get_font(26, bold=True)

        # SP Shield Emblem
        draw.rounded_rectangle(
            [self.width // 2 - 95, 70, self.width // 2 + 95, 175],
            radius=18,
            fill=(20, 26, 56, 255),
            outline=gold,
            width=3
        )
        draw.text((self.width // 2, 122), "SP", fill=(255, 215, 0, 255), font=font_brand, anchor="mm")

        # Channel Name
        draw.text((self.width // 2, 230), "SP GAMING CLUB", fill=(255, 255, 255, 255), font=font_brand, anchor="mm")

        # Scenario Title Pill
        sc_text = f"{scenario_id}: {scenario_title.upper()}"
        bbox = draw.textbbox((0, 0), sc_text, font=font_title)
        pill_w = min(1000, (bbox[2] - bbox[0]) + 50)
        draw.rounded_rectangle(
            [self.width // 2 - pill_w // 2, 305, self.width // 2 + pill_w // 2, 385],
            radius=14,
            fill=(18, 30, 65, 255),
            outline=gold,
            width=2
        )
        draw.text((self.width // 2, 345), sc_text, fill=(255, 225, 90, 255), font=font_title, anchor="mm")

        # Audience Gaming Pill (ALL AGES / 18+ ONLY)
        badge_text = "ALL AGES" if made_for_kids else "18+ ONLY"
        badge_fill = (20, 130, 60, 255) if made_for_kids else (180, 20, 20, 255)
        draw.rounded_rectangle(
            [self.width // 2 - 120, 420, self.width // 2 + 120, 480],
            radius=12,
            fill=badge_fill,
            outline=gold,
            width=2
        )
        draw.text((self.width // 2, 450), badge_text, fill=(255, 255, 255, 255), font=font_tag, anchor="mm")

        # Starring Hero
        hero_text = f"STARRING: {player_name.upper()}" if player_name else "DESI STRATEGY BATTLE"
        draw.text((self.width // 2, 540), hero_text, fill=(200, 220, 255, 255), font=font_tag, anchor="mm")

        # Bottom Callouts
        draw.text((self.width // 2, 1390), "TRADITIONAL INDIAN CARD GAME", fill=(255, 220, 80, 255), font=font_title, anchor="mm")
        draw.text((self.width // 2, 1475), "BIKKAD / COURT PIECE STRATEGY", fill=(230, 235, 250, 255), font=font_sub, anchor="mm")

        # Subscribe CTA Button
        draw.rounded_rectangle(
            [self.width // 2 - 320, 1600, self.width // 2 + 320, 1710],
            radius=24,
            fill=(220, 30, 30, 255),
            outline=gold,
            width=3
        )
        draw.text((self.width // 2, 1655), "SUBSCRIBE @sptalks9129", fill=(255, 255, 255, 255), font=font_title, anchor="mm")

        overlay_path = self.output_dir / f"overlay_{scenario_id}.png"
        img.save(overlay_path)
        return overlay_path

    def convert_to_short(
        self,
        video_path: str,
        scenario_id: str,
        scenario_title: str,
        player_name: Optional[str] = None,
        made_for_kids: bool = True
    ) -> Optional[str]:
        """Convert 16:9 video into 9:16 vertical Short using FFmpeg composite filter."""
        in_p = Path(video_path)
        if not in_p.is_file():
            return None

        out_name = f"short_{scenario_id}_{in_p.stem}.mp4"
        out_p = self.output_dir / out_name

        overlay_p = self.generate_overlay(scenario_id, scenario_title, player_name, made_for_kids=made_for_kids)

        # FFmpeg filter:
        # [0:v] split into background & foreground
        # [bg] downscaled to 135x240, blurred, upscaled to 1080x1920 (fast & buttery smooth)
        # [fg] scaled to 1080x608
        # Overlay [fg] at y=646 on [bg], then overlay the PNG banner on top
        filter_complex = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=135:240:force_original_aspect_ratio=increase,crop=135:240,boxblur=4:1,scale=1080:1920:flags=bicubic[blurred];"
            "[fg]scale=1080:608:force_original_aspect_ratio=decrease[center_game];"
            "[blurred][center_game]overlay=0:646[base];"
            "[base][1:v]overlay=0:0[outv]"
        )

        cmd = [
            self.ffmpeg_exe, "-y",
            "-loglevel", "error",
            "-i", str(in_p.resolve()),
            "-i", str(overlay_p.resolve()),
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_p.resolve())
        ]

        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and out_p.exists():
            try:
                overlay_p.unlink(missing_ok=True)
            except Exception:
                pass
            return str(out_p.resolve())
        else:
            return None
