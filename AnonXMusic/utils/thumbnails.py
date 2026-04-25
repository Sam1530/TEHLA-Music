import os
import re
import math

import aiofiles
import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from ytSearch import VideosSearch

from AnonXMusic import app
from config import YOUTUBE_IMG_URL


# ── Neon Color Palette ────────────────────────────────────────────────────────
NEON_COLORS = {
    "cyber_purple": (157, 78, 221),
    "electric_blue": (0, 195, 255),
    "neon_pink": (255, 20, 147),
    "acid_green": (57, 255, 20),
    "toxic_yellow": (255, 255, 0),
    "plasma_orange": (255, 103, 0),
    "cyber_cyan": (0, 255, 255),
    "hot_magenta": (255, 0, 128),
    "laser_red": (255, 30, 50),
    "ultra_violet": (138, 43, 226),
}


# ── helper functions ──────────────────────────────────────────────────────────

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight), Image.LANCZOS)


def circle(img):
    img = img.convert("RGBA")
    h, w = img.size
    mask = Image.new("L", (h, w), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (h, w)], fill=255)
    result = Image.new("RGBA", (h, w), (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result


def clear(text, limit=38):
    """Trim text to fit within character limit while keeping whole words."""
    words = text.split(" ")
    title = ""
    for w in words:
        if len(title) + len(w) < limit:
            title += " " + w
    return title.strip()


def get_vibrant_palette(img: Image.Image):
    """Extract the most vibrant colors from the cover art for dynamic theming."""
    small = img.convert("RGB").resize((150, 150))
    arr = np.array(small).reshape(-1, 3).astype(float)

    # Enhanced K-means for better color extraction
    np.random.seed(42)
    n_clusters = 8
    centers = arr[np.random.choice(len(arr), n_clusters, replace=False)]

    for _ in range(20):
        dists = np.linalg.norm(arr[:, None] - centers[None], axis=2)
        labels = np.argmin(dists, axis=1)
        for k in range(n_clusters):
            pts = arr[labels == k]
            if len(pts):
                centers[k] = pts.mean(axis=0)

    # Score colors by vibrancy (saturation × luminance balance)
    scored = []
    for c in centers:
        r, g, b = c / 255.0
        mx, mn = max(r, g, b), min(r, g, b)
        saturation = (mx - mn) / (mx + 1e-9)
        luminance = (mx + mn) / 2
        # Prefer high saturation + mid-high luminance for neon effect
        score = saturation * 2.0 + (1 - abs(luminance - 0.6)) * 1.5
        scored.append((score, c))

    scored.sort(reverse=True)

    # Return top 5 vibrant colors
    return [tuple(int(x) for x in c) for _, c in scored[:5]]


def create_neon_glow(size, bbox, color, radius=30, width=4, intensity=15):
    """Create a stunning multi-layered neon glow effect."""
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = bbox

    r, g, b = color

    # Outer glow layers (wide and faint)
    for i in range(intensity, 0, -1):
        expand = i * 3
        alpha = int(3 + (intensity - i) * 4)
        glow_color = (min(255, r), min(255, g), min(255, b), alpha)

        draw.rounded_rectangle(
            (x0 - expand, y0 - expand, x1 + expand, y1 + expand),
            radius=radius + expand,
            outline=glow_color,
            width=width + i
        )

    # Medium glow layer
    for i in range(6, 0, -1):
        expand = i
        alpha = int(30 + i * 20)
        glow_color = (min(255, r + 50), min(255, g + 50), min(255, b + 50), alpha)

        draw.rounded_rectangle(
            (x0 - expand, y0 - expand, x1 + expand, y1 + expand),
            radius=radius,
            outline=glow_color,
            width=width + 2
        )

    # Inner bright core
    inner_color = (min(255, r + 100), min(255, g + 100), min(255, b + 100), 255)
    draw.rounded_rectangle(
        bbox, radius=radius, outline=inner_color, width=width
    )

    # White hot highlight
    draw.rounded_rectangle(
        bbox, radius=radius, outline=(255, 255, 255, 120), width=max(1, width // 2)
    )

    return overlay


def draw_particle_background(size, palette):
    """Create a dynamic particle/dot background for extra depth."""
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    np.random.seed(42)

    for _ in range(120):
        x = np.random.randint(0, size[0])
        y = np.random.randint(0, size[1])
        r = np.random.randint(2, 8)
        color = palette[np.random.randint(0, len(palette))]
        alpha = np.random.randint(15, 50)
        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=(*color, alpha)
        )

    return overlay


def draw_glowing_progress(draw, canvas_size, x0, y0, x1, bar_height, progress, palette):
    """Draw an animated-looking glowing progress bar."""
    # Track background
    draw.rounded_rectangle(
        [(x0, y0), (x1, y0 + bar_height)],
        radius=bar_height // 2,
        fill=(20, 15, 35, 180)
    )

    # Track outline glow
    track_glow = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    tg_draw = ImageDraw.Draw(track_glow)
    for i in range(4, 0, -1):
        alpha = 20 + i * 15
        tg_draw.rounded_rectangle(
            (x0 - i, y0 - i, x1 + i, y0 + bar_height + i),
            radius=bar_height // 2 + i,
            outline=(palette[0][0], palette[0][1], palette[0][2], alpha),
            width=2
        )

    progress_x = int(x0 + (x1 - x0) * progress)

    # Filled progress glow layers
    for i in range(8, 0, -1):
        alpha = 8 + i * 8
        spread = i * 2
        color = palette[i % len(palette)]
        progress_glow = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        pg_draw = ImageDraw.Draw(progress_glow)
        pg_draw.rounded_rectangle(
            (x0 - spread // 2, y0 - spread // 2, progress_x + spread // 2, y0 + bar_height + spread // 2),
            radius=bar_height // 2 + spread // 2,
            fill=(*color, alpha)
        )
        # Paste manually (simplified composite)

    # Filled portion
    filled_color = palette[0]
    draw.rounded_rectangle(
        [(x0, y0), (progress_x, y0 + bar_height)],
        radius=bar_height // 2,
        fill=(min(255, filled_color[0] + 60), min(255, filled_color[1] + 60), min(255, filled_color[2] + 60), 230)
    )

    # Highlight on filled portion
    draw.rounded_rectangle(
        [(x0, y0), (progress_x, y0 + bar_height // 3)],
        radius=bar_height // 2,
        fill=(255, 255, 255, 60)
    )

    # Glowing thumb dot
    thumb_radius = 12
    thumb_y = y0 + bar_height // 2
    for i in range(5, 0, -1):
        glow_r = thumb_radius + i * 3
        alpha = 25 + i * 20
        draw.ellipse(
            (progress_x - glow_r, thumb_y - glow_r, progress_x + glow_r, thumb_y + glow_r),
            fill=(*palette[2], alpha)
        )

    # Thumb core
    draw.ellipse(
        (progress_x - thumb_radius, thumb_y - thumb_radius, progress_x + thumb_radius, thumb_y + thumb_radius),
        fill=(255, 255, 255, 250)
    )
    draw.ellipse(
        (progress_x - thumb_radius + 3, thumb_y - thumb_radius + 3, progress_x + thumb_radius - 3, thumb_y + thumb_radius - 3),
        fill=(*palette[2], 220)
    )


def draw_gradient_overlay(size, top_color, bottom_color):
    """Create a smooth gradient overlay."""
    gradient = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    h = size[1]

    for y in range(h):
        t = y / h
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        a = int(30 + t * 180)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b, a))

    return gradient


# ── Main Thumbnail Generator ──────────────────────────────────────────────────

async def get_thumb(videoid, user_id, title=None, duration=None, thumbnail=None,
                    views=None, channel=None):
    """
    Generate a premium neon-styled now-playing thumbnail.

    The design features:
    - Dynamic color extraction from cover art
    - Multi-layered neon glow borders
    - Glassmorphism effects
    - Particle backgrounds
    - Professional typography layout
    """
    if os.path.isfile(f"cache/{videoid}_{user_id}.png"):
        return f"cache/{videoid}_{user_id}.png"

    try:
        # ── Fetch song details if not provided ──────────────────────────
        if not title or not thumbnail:
            url = f"https://www.youtube.com/watch?v={videoid}"
            results = VideosSearch(url, limit=1)
            for result in (await results.next())["result"]:
                try:
                    title = result["title"]
                    title = re.sub(r"\W+", " ", title).title()
                except:
                    title = "Untitled Track"
                try:
                    duration = result["duration"]
                except:
                    duration = "??:??"
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                try:
                    views = result["viewCount"]["short"]
                except:
                    views = "Unknown"
                try:
                    channel = result["channel"]["name"]
                except:
                    channel = "Unknown Channel"
        else:
            title = re.sub(r"\W+", " ", str(title)).title()
            duration = duration or "??:??"
            views = views or "Unknown"
            channel = channel or "Unknown Channel"

        # ── Download cover art ──────────────────────────────────────────
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        # ═════════════════════════════════════════════════════════════════
        # CANVAS SETUP (2X resolution for sharp output)
        # ═════════════════════════════════════════════════════════════════
        SCALE = 2
        W, H = 2560, 1440  # 1280x720 × 2

        # Canvas background (dark base)
        canvas = Image.new("RGBA", (W, H), (8, 5, 18, 255))

        # ── Load and process cover art ──────────────────────────────────
        cover_raw = Image.open(f"cache/thumb{videoid}.png").convert("RGBA")
        cover_raw = ImageEnhance.Sharpness(cover_raw).enhance(1.5)
        cover_raw = ImageEnhance.Color(cover_raw).enhance(1.4)
        cover_raw = ImageEnhance.Contrast(cover_raw).enhance(1.2)

        # Extract vibrant palette
        palette = get_vibrant_palette(cover_raw)
        dominant = palette[0]

        # ── Background layer (blurred cover) ────────────────────────────
        bg_layer = cover_raw.copy()
        bg_layer = bg_layer.resize((W, H), Image.LANCZOS)
        bg_layer = bg_layer.filter(ImageFilter.GaussianBlur(radius=40))
        bg_darken = Image.new("RGBA", (W, H), (0, 0, 0, 160))
        bg_layer = Image.alpha_composite(bg_layer, bg_darken)
        canvas.paste(bg_layer, (0, 0))

        # ── Particle effect ─────────────────────────────────────────────
        particles = draw_particle_background((W, H), palette)
        canvas = Image.alpha_composite(canvas, particles)

        # ── Gradient overlay ────────────────────────────────────────────
        gradient = draw_gradient_overlay(
            (W, H),
            (dominant[0], dominant[1], dominant[2]),
            (0, 0, 0)
        )
        canvas = Image.alpha_composite(canvas, gradient)

        # ── Center Album Art (with glassmorphism effect) ─────────────────
        ART_SIZE = 480 * SCALE // 2  # 480px at final resolution
        art_x = (W - ART_SIZE) // 2
        art_y = (H - ART_SIZE) // 2 - 40 * SCALE // 2

        # Glass backdrop behind album art
        glass_pad = 20 * SCALE // 2
        glass_bg = Image.new("RGBA", (ART_SIZE + glass_pad * 2, ART_SIZE + glass_pad * 2), (0, 0, 0, 0))
        gb_draw = ImageDraw.Draw(glass_bg)
        gb_draw.rounded_rectangle(
            [(0, 0), (ART_SIZE + glass_pad * 2, ART_SIZE + glass_pad * 2)],
            radius=28 * SCALE // 2,
            fill=(255, 255, 255, 25)
        )
        canvas.alpha_composite(
            glass_bg,
            (art_x - glass_pad, art_y - glass_pad)
        )

        # Album art shadow
        shadow = Image.new("RGBA", (ART_SIZE + 40, ART_SIZE + 40), (0, 0, 0, 0))
        sd_draw = ImageDraw.Draw(shadow)
        sd_draw.rounded_rectangle(
            [(20, 20), (ART_SIZE + 20, ART_SIZE + 20)],
            radius=24 * SCALE // 2,
            fill=(dominant[0] // 3, dominant[1] // 3, dominant[2] // 3, 180)
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(20))
        canvas.alpha_composite(shadow, (art_x - 20, art_y - 20))

        # Album art itself
        art_img = cover_raw.resize((ART_SIZE, ART_SIZE), Image.LANCZOS)
        art_img = ImageEnhance.Sharpness(art_img).enhance(1.8)
        art_img = ImageEnhance.Contrast(art_img).enhance(1.3)
        art_mask = Image.new("L", (ART_SIZE, ART_SIZE), 0)
        ImageDraw.Draw(art_mask).rounded_rectangle(
            [(0, 0), (ART_SIZE, ART_SIZE)],
            radius=22 * SCALE // 2,
            fill=255
        )
        art_img.putalpha(art_mask)
        canvas.alpha_composite(art_img, (art_x, art_y))

        # ── Neon border around album art ─────────────────────────────────
        neon_border = create_neon_glow(
            (W, H),
            (art_x - 8, art_y - 8, art_x + ART_SIZE + 8, art_y + ART_SIZE + 8),
            palette[1],  # Second color for contrast
            radius=26 * SCALE // 2,
            width=5 * SCALE // 2,
            intensity=12
        )
        canvas = Image.alpha_composite(canvas, neon_border)

        # ── Outer card neon border ──────────────────────────────────────
        outer_border = create_neon_glow(
            (W, H),
            (10, 10, W - 10, H - 10),
            dominant,
            radius=40,
            width=4 * SCALE // 2,
            intensity=10
        )
        canvas = Image.alpha_composite(canvas, outer_border)

        # ── Now Playing Badge (Top Left) ────────────────────────────────
        badge_w = 280 * SCALE // 2
        badge_h = 56 * SCALE // 2
        badge_x = 40 * SCALE // 2
        badge_y = 30 * SCALE // 2

        badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        bd_draw = ImageDraw.Draw(badge)

        # Glass badge background
        bd_draw.rounded_rectangle(
            [(0, 0), (badge_w, badge_h)],
            radius=badge_h // 2,
            fill=(10, 8, 25, 200)
        )

        # Badge neon outline
        for i in range(3, 0, -1):
            alpha = 30 + i * 25
            bd_draw.rounded_rectangle(
                (i, i, badge_w - i, badge_h - i),
                radius=badge_h // 2,
                outline=(*palette[0], alpha),
                width=2
            )

        canvas.alpha_composite(badge, (badge_x, badge_y))

        # ── Bot Name Badge (Top Right) ──────────────────────────────────
        bot_name = unidecode(app.name)[:20]
        try:
            bot_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 20 * SCALE // 2)
            bot_w = int(bot_font.getlength(bot_name)) + 40 * SCALE // 2
        except:
            bot_font = ImageFont.load_default()
            bot_w = len(bot_name) * 12 + 40

        bot_badge = Image.new("RGBA", (bot_w, badge_h), (0, 0, 0, 0))
        bb_draw = ImageDraw.Draw(bot_badge)
        bb_draw.rounded_rectangle(
            [(0, 0), (bot_w, badge_h)],
            radius=badge_h // 2,
            fill=(10, 8, 25, 200)
        )
        for i in range(3, 0, -1):
            alpha = 30 + i * 25
            bb_draw.rounded_rectangle(
                (i, i, bot_w - i, badge_h - i),
                radius=badge_h // 2,
                outline=(*palette[2], alpha),
                width=2
            )

        bot_x = W - bot_w - 40 * SCALE // 2
        bot_y = 30 * SCALE // 2
        canvas.alpha_composite(bot_badge, (bot_x, bot_y))

        # ── Typography ──────────────────────────────────────────────────
        try:
            font_title = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 44 * SCALE // 2)
            font_info = ImageFont.truetype("AnonXMusic/assets/font.ttf", 26 * SCALE // 2)
            font_badge_text = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 22 * SCALE // 2)
            font_time = ImageFont.truetype("AnonXMusic/assets/font.ttf", 24 * SCALE // 2)
        except:
            font_title = font_info = font_badge_text = font_time = ImageFont.load_default()

        draw = ImageDraw.Draw(canvas)

        # Badge text - Now Playing
        draw.text(
            (badge_x + 50 * SCALE // 2, badge_y + 12 * SCALE // 2),
            "🎵 NOW PLAYING",
            fill=(255, 255, 255, 250),
            font=font_badge_text
        )

        # Badge text - Bot name
        draw.text(
            (bot_x + 20 * SCALE // 2, bot_y + 14 * SCALE // 2),
            bot_name,
            fill=(255, 255, 255, 250),
            font=font_badge_text
        )

        # ── Song Info Layout (Bottom Section) ───────────────────────────
        # Position below album art
        info_y = art_y + ART_SIZE + 30 * SCALE // 2
        info_x = art_x

        # Title with glow
        title_text = clear(title, 45)
        # Title shadow/glow
        for ox, oy in [(2, 2), (-1, -1), (1, -1), (-1, 1)]:
            draw.text(
                (info_x + ox, info_y + oy),
                title_text,
                fill=(*palette[0], 100),
                font=font_title
            )
        # Title main
        draw.text(
            (info_x, info_y),
            title_text,
            fill=(255, 255, 255, 255),
            font=font_title
        )

        # Artist/Channel info
        info_y2 = info_y + 60 * SCALE // 2
        channel_text = f"🎙️ {channel}"
        draw.text(
            (info_x, info_y2),
            channel_text,
            fill=(200, 200, 230, 230),
            font=font_info
        )

        # Views
        views_text = f"👁️ {views} views"
        try:
            views_w = int(font_info.getlength(views_text))
        except:
            views_w = len(views_text) * 14
        draw.text(
            (info_x + 300 * SCALE // 2, info_y2),
            views_text,
            fill=(200, 200, 230, 230),
            font=font_info
        )

        # ── Progress Bar ────────────────────────────────────────────────
        prog_y = info_y2 + 50 * SCALE // 2
        prog_x0 = info_x
        prog_x1 = info_x + 600 * SCALE // 2
        prog_h = 10 * SCALE // 2

        draw_glowing_progress(
            draw, (W, H),
            prog_x0, prog_y, prog_x1, prog_h,
            0.55,  # Progress percentage
            palette
        )

        # ── Duration timestamps ─────────────────────────────────────────
        time_y = prog_y + prog_h + 15 * SCALE // 2
        start_time = "0:00"
        draw.text(
            (prog_x0, time_y),
            start_time,
            fill=(180, 185, 210, 220),
            font=font_time
        )

        duration_text = duration if duration else "0:00"
        try:
            dur_w = int(font_time.getlength(duration_text))
        except:
            dur_w = len(duration_text) * 12
        draw.text(
            (prog_x1 - dur_w, time_y),
            duration_text,
            fill=(180, 185, 210, 220),
            font=font_time
        )

        # ── Small album art thumbnail in bottom-left info ───────────────
        mini_size = 90 * SCALE // 2
        mini_x = prog_x0
        mini_y = time_y + 40 * SCALE // 2
        mini_art = cover_raw.resize((mini_size, mini_size), Image.LANCZOS)
        mini_mask = Image.new("L", (mini_size, mini_size), 0)
        ImageDraw.Draw(mini_mask).rounded_rectangle(
            [(0, 0), (mini_size, mini_size)],
            radius=12 * SCALE // 2,
            fill=255
        )
        mini_art.putalpha(mini_mask)

        # Mini art neon border
        mini_border = create_neon_glow(
            (W, H),
            (mini_x - 4, mini_y - 4, mini_x + mini_size + 4, mini_y + mini_size + 4),
            palette[3],
            radius=14 * SCALE // 2,
            width=3 * SCALE // 2,
            intensity=6
        )
        canvas = Image.alpha_composite(canvas, mini_border)
        canvas.alpha_composite(mini_art, (mini_x, mini_y))

        # ── Bot watermark next to mini art ───────────────────────────────
        watermark_text = f"Powered by {unidecode(app.name)}"
        try:
            water_y = mini_y + mini_size // 2 - 12 * SCALE // 2
            draw.text(
                (mini_x + mini_size + 16 * SCALE // 2, water_y),
                watermark_text,
                fill=(150, 155, 180, 200),
                font=font_info
            )
        except:
            pass

        # ═════════════════════════════════════════════════════════════════
        # FINAL OUTPUT
        # ═════════════════════════════════════════════════════════════════
        final = canvas.convert("RGB").resize((1280, 720), Image.LANCZOS)

        # Clean up temp file
        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass

        # Save with high quality
        final.save(f"cache/{videoid}_{user_id}.png", quality=100, optimize=True)
        return f"cache/{videoid}_{user_id}.png"

    except Exception as e:
        print(f"Thumbnail generation error: {e}")
        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass
        return YOUTUBE_IMG_URL
