"""High-Impact 1280x720 YouTube Thumbnail Generator for Desi Board & Strategy Games."""

import re
import random
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Preset family-friendly taglines (including Bollywood flair, avoiding restricted keywords)
FANCY_TAGLINES = [
    "BOLLYWOOD STRATEGY CLASH",
    "SHOLAY STYLE MAHA-MUQABLA",
    "DABANGG SHOWDOWN EDITION",
    "MOGAMBO KHUSH HUA ROUND",
    "RISHTEY MEIN BAAP EDITION",
    "DON KO PAKADNA MUSHKIL",
    "PUSHPA JHUKEGA NAHI SPECIAL",
    "ROYAL STRATEGY SHOWDOWN",
    "TRADITIONAL FAMILY MATCH",
    "MASTERCLASS GAMEPLAY",
    "EPIC 4-PLAYER BATTLE",
]


def _clean_thumbnail_text(text: str) -> str:
    """Ensure thumbnail text stays strictly family/board-game safe."""
    cleaned = re.sub(r"\bpot-sweep\b", "TRICK SWEEP", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpots?\b", "TRICK", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bjackpot\s+sweep\b", "GRAND SWEEP", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bjackpot\b", "GRAND SWEEP", cleaned, flags=re.IGNORECASE)
    return cleaned


class ThumbnailGenerator:
    """Generates 1280x720 high-contrast YouTube thumbnails from real gameplay frames."""

    def __init__(self, output_dir: Optional[str] = None):
        self.width = 1280
        self.height = 720
        self.output_dir = Path(output_dir or "recordings/thumbnails")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        game_title: str = "BIKKAD",
        player_name: Optional[str] = None,
        tagline: Optional[str] = None,
        background_image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        filename_prefix: str = "thumb",
        made_for_kids: bool = True
    ) -> str:
        """Create a 1280x720 JPEG thumbnail and return its file path."""
        tagline_options = list(FANCY_TAGLINES)
        if player_name:
            tagline_options.insert(0, f"{player_name.upper()} KA MAHA MUQABLA")
            tagline_options.append(f"{player_name.upper()} SPECIAL ROUND")

        tagline = _clean_thumbnail_text((tagline or random.choice(tagline_options)).strip())

        # 1. Base Canvas - Deep Royal Felt Emerald/Blue Gradient
        img = Image.new("RGB", (self.width, self.height), color=(10, 46, 36))
        draw = ImageDraw.Draw(img)

        for y in range(self.height):
            ratio = y / self.height
            r = int(10 + ratio * 8)
            g = int(42 + ratio * 24)
            b = int(34 + ratio * 28)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # 2. Extract authentic gameplay frame from the video itself (or fallback)
        extracted_frame = None
        if not background_image_path and video_path and Path(video_path).is_file():
            extracted_frame = self._extract_video_frame(video_path)

        bg_candidate = background_image_path or extracted_frame or self._find_game_screenshot()
        if bg_candidate and Path(bg_candidate).is_file():
            try:
                bg = Image.open(bg_candidate).convert("RGB")
                bg = bg.resize((self.width, self.height), Image.Resampling.LANCZOS)
                # Subtle blur & darkening so gameplay table shines behind crisp title
                bg = bg.filter(ImageFilter.GaussianBlur(radius=1.5))
                enhancer = ImageEnhance.Brightness(bg)
                bg = enhancer.enhance(0.55)
                img = Image.blend(img, bg, alpha=0.80)
                draw = ImageDraw.Draw(img)
            except Exception:
                pass

        if extracted_frame:
            try:
                Path(extracted_frame).unlink(missing_ok=True)
            except Exception:
                pass

        # 3. Royal Rajput Gold Border Frame
        gold_color = (245, 197, 24)
        border_width = 12
        for i in range(border_width):
            draw.rectangle(
                [i, i, self.width - 1 - i, self.height - 1 - i],
                outline=(245 - i * 5, 197 - i * 5, 24)
            )

        draw.rectangle(
            [22, 22, self.width - 23, self.height - 23],
            outline=(212, 175, 55),
            width=2
        )

        # 4. Fonts (pure ASCII-safe labels so Arial never draws missing glyph boxes)
        font_large = self._get_font(size=108, bold=True)
        font_small = self._get_font(size=26, bold=True)

        # 5. Brand Header & Emblems (SP Gaming Club + 18+ Gaming)
        # Top-Left SP Brand Emblem
        sp_x, sp_y, sp_w, sp_h = 40, 48, 110, 64
        draw.rounded_rectangle(
            [sp_x, sp_y, sp_x + sp_w, sp_y + sp_h],
            radius=14,
            fill=(14, 18, 36),
            outline=gold_color,
            width=3
        )
        font_sp = self._get_font(size=44, bold=True)
        draw.text(
            (sp_x + sp_w // 2, sp_y + sp_h // 2),
            "SP",
            fill=(255, 215, 0),
            font=font_sp,
            anchor="mm"
        )

        # Top-Right Audience Badge (ALL AGES / 18+ ONLY)
        badge_text = "ALL AGES" if made_for_kids else "18+ ONLY"
        badge_fill = (22, 120, 60) if made_for_kids else (180, 20, 20)
        ad_w, ad_h = 140, 52
        ad_x, ad_y = self.width - 40 - ad_w, 54
        draw.rounded_rectangle(
            [ad_x, ad_y, ad_x + ad_w, ad_y + ad_h],
            radius=12,
            fill=badge_fill,
            outline=gold_color,
            width=2
        )
        font_ad = self._get_font(size=24, bold=True)
        draw.text(
            (ad_x + ad_w // 2, ad_y + ad_h // 2),
            badge_text,
            fill=(255, 255, 255),
            font=font_ad,
            anchor="mm"
        )

        # Center Top Header Pill
        pill_text = "SP GAMING CLUB  |  CLASSIC STRATEGY CARD BATTLES"
        pill_bbox = draw.textbbox((0, 0), pill_text, font=font_small)
        pill_w = (pill_bbox[2] - pill_bbox[0]) + 60
        pill_h = 52
        pill_x = (self.width - pill_w) // 2
        pill_y = 54

        draw.rounded_rectangle(
            [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
            radius=14,
            fill=(16, 24, 48),
            outline=gold_color,
            width=2
        )
        draw.text(
            (self.width // 2, pill_y + pill_h // 2),
            pill_text,
            fill=(255, 220, 90),
            font=font_small,
            anchor="mm"
        )

        # 6. Main Big Title (e.g. "BIKKAD")
        main_text = game_title.upper()
        text_y = 285

        shadow_offset = 8
        for dx in range(-shadow_offset, shadow_offset + 1, 2):
            for dy in range(-shadow_offset, shadow_offset + 1, 2):
                draw.text(
                    (self.width // 2 + dx, text_y + dy),
                    main_text,
                    fill=(0, 0, 0),
                    font=font_large,
                    anchor="mm"
                )

        draw.text(
            (self.width // 2, text_y),
            main_text,
            fill=(255, 223, 80),
            font=font_large,
            anchor="mm"
        )

        # 7. Dynamically Fitted Sub-Headline Tagline Banner (never overflows box)
        sub_text = tagline
        sub_font_size = 42
        font_sub = self._get_font(size=sub_font_size, bold=True)
        while sub_font_size > 24:
            bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
            if (bbox[2] - bbox[0]) <= 1040:
                break
            sub_font_size -= 2
            font_sub = self._get_font(size=sub_font_size, bold=True)

        bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
        sub_pill_w = min(1160, (bbox[2] - bbox[0]) + 84)
        sub_pill_h = 74
        sub_pill_x = (self.width - sub_pill_w) // 2
        sub_pill_y = 435

        draw.rounded_rectangle(
            [sub_pill_x, sub_pill_y, sub_pill_x + sub_pill_w, sub_pill_y + sub_pill_h],
            radius=14,
            fill=(10, 15, 30),
            outline=gold_color,
            width=3
        )

        draw.text(
            (self.width // 2, sub_pill_y + sub_pill_h // 2),
            sub_text,
            fill=(255, 255, 255),
            font=font_sub,
            anchor="mm"
        )

        # 8. Clean Footer Banner (SP Gaming Club)
        footer_text = (
            f"SP GAMING CLUB  •  STARRING: {player_name.upper()}  •  CLASSIC STRATEGY AI MATCH"
            if player_name
            else "SP GAMING CLUB  •  CLASSIC STRATEGY CARD BATTLES"
        )
        footer_y = 610
        draw.text(
            (self.width // 2 + 2, footer_y + 2),
            footer_text,
            fill=(0, 0, 0),
            font=font_small,
            anchor="mm"
        )
        draw.text(
            (self.width // 2, footer_y),
            footer_text,
            fill=(248, 250, 252),
            font=font_small,
            anchor="mm"
        )

        # 9. Save final thumbnail image
        timestamp = self._timestamp()
        out_path = self.output_dir / f"{filename_prefix}_{timestamp}.jpg"
        img.save(out_path, format="JPEG", quality=95)
        return str(out_path.resolve())

    def _extract_video_frame(self, video_path: str) -> Optional[str]:
        """Extract an active mid-game frame (~22s) from the recorded video."""
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            tmp_file = Path(tempfile.gettempdir()) / f"thumb_frame_{Path(video_path).stem}.jpg"
            # Seek to 22s first; if video is shorter, fallback to 5s
            for ts in ["22", "5"]:
                subprocess.run(
                    [ffmpeg_exe, "-y", "-ss", ts, "-i", str(video_path), "-vframes", "1", str(tmp_file)],
                    capture_output=True,
                    timeout=15
                )
                if tmp_file.exists() and tmp_file.stat().st_size > 10000:
                    return str(tmp_file)
        except Exception:
            pass
        return None

    def _get_font(self, size: int, bold: bool = False):
        """Locate standard Windows fonts or fall back to PIL default."""
        font_names = [
            "arialbd.ttf" if bold else "arial.ttf",
            "segoeuib.ttf" if bold else "segoeui.ttf",
            "impact.ttf",
            "trebucbd.ttf",
        ]
        windows_font_dir = Path("C:/Windows/Fonts")

        for name in font_names:
            font_path = windows_font_dir / name
            if font_path.exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except Exception:
                    pass

        return ImageFont.load_default()

    def _find_game_screenshot(self) -> Optional[str]:
        """Fallback local verified game art (never broken error pages)."""
        candidates = [
            Path("C:/Projects/bikkad/lobby_full_screen.png"),
            Path("C:/Projects/bikkad/frontend/assets/avatar_candidate1.png"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    @staticmethod
    def _timestamp() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")
