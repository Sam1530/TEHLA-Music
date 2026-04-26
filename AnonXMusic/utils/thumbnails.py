import os
import re
import math
import random
import traceback

import aiofiles
import aiohttp
from PIL import (
    Image, ImageDraw, ImageEnhance,
    ImageFilter, ImageFont, ImageOps
)
from ytSearch import VideosSearch

from config import YOUTUBE_IMG_URL
from AnonXMusic import app

# ================= CONSTANTS =================
CACHE_DIR = "cache"
CANVAS_SIZE = (1280, 720)

# ================= PREMIUM NEON PURPLE COLOR SCHEME =================
DARK_BG = (4, 1, 15)                      # Deeper dark for richer contrast
NEON_PURPLE = (147, 51, 234)              # #9333EA - Vibrant purple
NEON_PURPLE_LIGHT = (175, 90, 250)        # Brighter light purple
NEON_PURPLE_PINK = (192, 38, 211)         # #C026D3 - Purple-pink
NEON_MAGENTA = (220, 75, 242)             # #D946EF - Magenta
NEON_VIOLET = (139, 92, 246)              # #8B5CF6 - Violet
ACCENT_PURPLE = (186, 104, 200)           # Soft accent
DEEP_PURPLE = (30, 8, 55)                 # Rich deep purple
ROYAL_PURPLE = (60, 15, 100)              # Royal purple accent
WHITE = (255, 255, 255)
LIGHT_GRAY = (230, 225, 240)
DARK_GRAY = (120, 110, 130)
SOFT_WHITE = (245, 240, 250)
GLASS_WHITE = (255, 255, 255, 40)

# ================= SPOTIFY-STYLE BUTTON COLORS =================
SPOTIFY_GREEN = (30, 215, 96)             # Spotify green accent
BUTTON_BG = (40, 40, 50, 120)             # Semi-transparent button bg
BUTTON_HOVER = (60, 55, 70, 160)          # Button hover effect

# ================= LAYOUT POSITIONS =================
COVER_SIZE = 380
COVER_X = 60
COVER_Y = (CANVAS_SIZE[1] - COVER_SIZE) // 2

RIGHT_START_X = COVER_X + COVER_SIZE + 70
RIGHT_WIDTH = CANVAS_SIZE[0] - RIGHT_START_X - 60

# ================= TEXT & CONTROLS POSITIONS =================
NOW_PLAYING_Y = 115
TITLE_Y = 185
ARTIST_Y = TITLE_Y + 75
ALBUM_INFO_Y = ARTIST_Y + 50
PROGRESS_Y = ALBUM_INFO_Y + 70
TIME_Y = PROGRESS_Y + 50
CONTROLS_Y = TIME_Y + 65

# ================= HELPER FUNCTIONS =================

def ensure_cache_dir():
    """Ensure cache directory exists"""
    os.makedirs(CACHE_DIR, exist_ok=True)

def trim_text(text, font, max_width):
    """Trim text to fit within max_width with ellipsis"""
    try:
        if font.getlength(text) <= max_width:
            return text
        while font.getlength(text + "…") > max_width:
            text = text[:-1]
        return text + "…"
    except:
        return text[:30] + "..." if len(text) > 30 else text

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def blend_colors(color1, color2, ratio=0.5):
    """Blend two colors"""
    return tuple(
        max(0, min(255, int(c1 * (1 - ratio) + c2 * ratio)))
        for c1, c2 in zip(color1, color2)
    )

def draw_rounded_rect_with_border(draw, bbox, radius, fill, outline, outline_width):
    """Helper to draw rounded rectangle with border"""
    draw.rounded_rectangle(bbox, radius=radius, fill=fill)
    if outline_width > 0:
        for i in range(outline_width):
            draw.rounded_rectangle(
                (bbox[0] - i, bbox[1] - i, bbox[2] + i, bbox[3] + i),
                radius=radius + i,
                outline=outline
            )

# ================= ENHANCED BACKGROUND EFFECTS =================

def create_gradient_background(width, height, color1, color2):
    """Create rich multi-layer gradient background"""
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    for i in range(height):
        ratio = i / height
        # Dynamic curve for more depth
        curve = math.sin(ratio * math.pi * 0.6) ** 1.8
        r = int(color1[0] * (1 - curve) + color2[0] * curve)
        g = int(color1[1] * (1 - curve) + color2[1] * curve)
        b = int(color1[2] * (1 - curve) + color2[2] * curve)
        draw.line([(0, i), (width, i)], fill=(r, g, b, 255))
    
    return gradient

def create_radial_glow(size, color, center=None, intensity=0.1):
    """Create elegant radial glow with better visibility"""
    if center is None:
        center = (size[0] // 2, size[1] // 2)
    
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    max_radius = int(math.sqrt(size[0]**2 + size[1]**2)) // 2
    
    for radius in range(max_radius, 0, -60):
        alpha = min(12, int(255 * intensity * (radius / max_radius) * 0.4))
        draw.ellipse(
            (center[0] - radius, center[1] - radius,
             center[0] + radius, center[1] + radius),
            outline=(*color, alpha),
            width=5
        )
    
    return glow.filter(ImageFilter.GaussianBlur(45))

def create_particle_field(size, color, count=80):
    """Create subtle floating particles"""
    particles = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(particles)
    random.seed(42)
    
    for _ in range(count):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        radius = random.randint(1, 3)
        alpha = random.randint(10, 50)
        
        for r in range(radius, 0, -1):
            a = alpha * (r / radius)
            draw.ellipse(
                (x - r, y - r, x + r, y + r),
                fill=(*color, int(a))
            )
    
    return particles

def create_light_streaks(size, color, count=5):
    """Create diagonal light streaks for premium look"""
    streaks = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(streaks)
    
    for _ in range(count):
        x1 = random.randint(-100, size[0] + 100)
        y1 = random.randint(-100, size[1] + 100)
        length = random.randint(200, 500)
        angle = random.uniform(25, 45)
        
        x2 = x1 + int(length * math.cos(math.radians(angle)))
        y2 = y1 + int(length * math.sin(math.radians(angle)))
        
        alpha = random.randint(3, 10)
        width = random.randint(1, 3)
        draw.line([(x1, y1), (x2, y2)], fill=(*color, alpha), width=width)
    
    return streaks.filter(ImageFilter.GaussianBlur(8))

def create_cover_art_frame(size, border_width=15):
    """Create premium cover art frame with shadow"""
    frame = Image.new("RGBA", (size[0] + border_width * 2, size[1] + border_width * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    
    # Shadow layers
    for i in range(border_width, 0, -1):
        alpha = int(30 * (i / border_width))
        draw.rounded_rectangle(
            (i, i + 5, size[0] + border_width * 2 - i, size[1] + border_width * 2 - i + 5),
            radius=24,
            fill=(0, 0, 0, alpha)
        )
    
    # Glow border
    for i in range(3, 0, -1):
        alpha = int(40 * (i / 3))
        draw.rounded_rectangle(
            (border_width - i, border_width - i, 
             size[0] + border_width + i, size[1] + border_width + i),
            radius=22 + i,
            outline=(*NEON_PURPLE, alpha),
            width=2
        )
    
    # Inner highlight
    draw.rounded_rectangle(
        (border_width + 2, border_width + 2,
         size[0] + border_width - 2, size[1] + border_width - 2),
        radius=18,
        outline=(255, 255, 255, 30),
        width=1
    )
    
    return frame.filter(ImageFilter.GaussianBlur(5))

# ================= SPOTIFY-STYLE BUTTONS =================

def create_spotify_play_button(size=72):
    """Create Spotify-style play button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    for i in range(8, 0, -2):
        alpha = int(15 * (i / 8))
        draw.ellipse(
            (center - size//2 - i, center - size//2 - i,
             center + size//2 + i, center + size//2 + i),
            fill=(0, 0, 0, alpha)
        )
    
    draw.ellipse(
        (center - size//2 + 3, center - size//2 + 3,
         center + size//2 - 3, center + size//2 - 3),
        fill=SPOTIFY_GREEN
    )
    
    for i in range(size//2 - 3, size//4, -1):
        ratio = (i - size//4) / (size//2 - size//4)
        color = blend_colors(SPOTIFY_GREEN, (50, 230, 120), ratio)
        alpha = int(100 * ratio)
        draw.ellipse(
            (center - i, center - i, center + i, center + i),
            fill=(*color, alpha)
        )
    
    triangle_size = size // 5
    offset_x = 2
    points = [
        (center - triangle_size + offset_x, center - triangle_size),
        (center - triangle_size + offset_x, center + triangle_size),
        (center + triangle_size + offset_x, center)
    ]
    draw.polygon(points, fill=WHITE)
    
    draw.ellipse(
        (center - size//2 + 3, center - size//2 + 3,
         center + size//2 - 3, center + size//2 - 3),
        outline=(255, 255, 255, 30),
        width=1
    )
    
    return btn

def create_spotify_nav_button(size=44, direction="prev"):
    """Create Spotify-style navigation button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    draw.ellipse((2, 2, size - 2, size - 2), fill=(255, 255, 255, 12))
    draw.ellipse((2, 2, size - 2, size - 2), outline=(255, 255, 255, 25), width=2)
    
    if direction == "prev":
        bar_x = size // 4 + 2
        tri_w = size // 6
        tri_h = size // 4
        
        draw.rectangle(
            (bar_x - 1, center - tri_h, bar_x + 1, center + tri_h),
            fill=(255, 255, 255, 200)
        )
        
        for offset in [0, size // 5]:
            points = [
                (bar_x + 4 + offset, center - tri_h),
                (bar_x + 4 + offset, center + tri_h),
                (bar_x + 4 - tri_w + offset, center)
            ]
            draw.polygon(points, fill=(255, 255, 255, 200))
    
    elif direction == "next":
        bar_x = size - size // 4 - 2
        tri_w = size // 6
        tri_h = size // 4
        
        draw.rectangle(
            (bar_x - 1, center - tri_h, bar_x + 1, center + tri_h),
            fill=(255, 255, 255, 200)
        )
        
        for offset in [0, -size // 5]:
            points = [
                (bar_x - 4 + offset, center - tri_h),
                (bar_x - 4 + offset, center + tri_h),
                (bar_x - 4 + tri_w + offset, center)
            ]
            draw.polygon(points, fill=(255, 255, 255, 200))
    
    return btn

def create_shuffle_button(size=40):
    """Create shuffle button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    
    arrow_color = (255, 255, 255, 180)
    offset = size // 4
    
    points1 = [
        (offset, size - offset),
        (size - offset, offset),
        (size - offset - 5, offset + 5),
        (offset + 3, size - offset - 3)
    ]
    draw.line([points1[0], points1[1]], fill=arrow_color, width=2)
    draw.line([points1[2], points1[3]], fill=arrow_color, width=2)
    
    points2 = [
        (offset, offset),
        (size - offset, size - offset),
        (size - offset - 5, size - offset - 5),
        (offset + 3, offset + 3)
    ]
    draw.line([points2[0], points2[1]], fill=arrow_color, width=2)
    draw.line([points2[2], points2[3]], fill=arrow_color, width=2)
    
    draw.polygon([
        (size - offset, offset),
        (size - offset - 8, offset + 3),
        (size - offset - 3, offset + 8)
    ], fill=arrow_color)
    
    draw.polygon([
        (size - offset, size - offset),
        (size - offset - 8, size - offset - 3),
        (size - offset - 3, size - offset - 8)
    ], fill=arrow_color)
    
    return btn

def create_repeat_button(size=40):
    """Create repeat button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    bbox = (center - 10, center - 14, center + 10, center + 14)
    draw.arc(bbox, 45, 315, fill=(255, 255, 255, 180), width=2)
    
    arrow_x = bbox[2]
    arrow_y = bbox[1] + 8
    draw.polygon([
        (arrow_x + 5, arrow_y - 5),
        (arrow_x - 5, arrow_y),
        (arrow_x + 5, arrow_y + 5)
    ], fill=(255, 255, 255, 180))
    
    dot_size = 3
    draw.ellipse(
        (center - dot_size, center - dot_size - 8, 
         center + dot_size, center + dot_size - 8),
        fill=(255, 255, 255, 100)
    )
    
    return btn

def create_spotify_progress_bar(width, height, progress=0.3, current_time="1:15", total_time="3:56"):
    """Create attractive progress bar with neon purple theme"""
    bar_height = height
    bar_image = Image.new("RGBA", (width, bar_height + 45), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar_image)
    
    bar_y = 15
    bar_radius = bar_height // 2
    
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_height),
        radius=bar_radius,
        fill=(255, 255, 255, 15)
    )
    
    for i in range(2, 0, -1):
        alpha = int(20 * (i / 2))
        draw.rounded_rectangle(
            (0 - i, bar_y - i, width + i, bar_y + bar_height + i),
            radius=bar_radius + i,
            outline=(*NEON_PURPLE, alpha),
            width=1
        )
    
    fill_width = int(width * progress)
    if fill_width > 0:
        for i in range(5, 0, -1):
            alpha = int(15 * (i / 5))
            draw.rounded_rectangle(
                (0 - i, bar_y - i, fill_width + i, bar_y + bar_height + i),
                radius=bar_radius + i,
                fill=(*NEON_PURPLE, alpha)
            )
        
        for x in range(fill_width):
            ratio = x / max(fill_width, 1)
            color = blend_colors(NEON_PURPLE, NEON_PURPLE_LIGHT, ratio)
            draw.rectangle((x, bar_y, x + 1, bar_y + bar_height), fill=color)
        
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height),
            radius=bar_radius,
            fill=None
        )
        
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height // 2),
            radius=bar_radius,
            fill=(255, 255, 255, 25)
        )
        
        dot_radius = 9
        dot_x = fill_width
        dot_y = bar_y + bar_height // 2
        
        for i in range(4, 0, -1):
            alpha = int(40 * (i / 4))
            draw.ellipse(
                (dot_x - dot_radius - i*2, dot_y - dot_radius - i*2,
                 dot_x + dot_radius + i*2, dot_y + dot_radius + i*2),
                fill=(*NEON_PURPLE, alpha)
            )
        
        draw.ellipse(
            (dot_x - dot_radius, dot_y - dot_radius,
             dot_x + dot_radius, dot_y + dot_radius),
            fill=WHITE
        )
        
        draw.ellipse(
            (dot_x - dot_radius + 3, dot_y - dot_radius + 3,
             dot_x + dot_radius - 3, dot_y + dot_radius - 3),
            fill=NEON_PURPLE
        )
        
        draw.ellipse(
            (dot_x - dot_radius//2, dot_y - dot_radius//2,
             dot_x + dot_radius//2, dot_y + dot_radius//2),
            fill=(255, 255, 255, 40)
        )
    
    try:
        time_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 16)
    except:
        try:
            time_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 16)
        except:
            time_font = ImageFont.load_default()
    
    draw.text((0, bar_y + bar_height + 10), current_time, fill=WHITE, font=time_font)
    
    total_time_bbox = draw.textbbox((0, 0), total_time, font=time_font)
    total_time_width = total_time_bbox[2] - total_time_bbox[0]
    draw.text(
        (width - total_time_width, bar_y + bar_height + 10),
        total_time,
        fill=WHITE,
        font=time_font
    )
    
    return bar_image

def create_spotify_controls():
    """Create complete Spotify-style control panel"""
    panel_width = 350
    panel_height = 120
    
    panel = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
    
    # Simple glass background
    glass = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glass)
    gdraw.rounded_rectangle((0, 0, panel_width, panel_height), radius=15, fill=(255, 255, 255, 8))
    gdraw.rounded_rectangle((0, 0, panel_width, panel_height), radius=15, outline=(255, 255, 255, 20), width=1)
    panel = Image.alpha_composite(panel, glass)
    
    center_x = panel_width // 2
    center_y = panel_height // 2
    
    shuffle_btn = create_shuffle_button(36)
    panel.alpha_composite(shuffle_btn, (center_x - 120, center_y - 18))
    
    prev_btn = create_spotify_nav_button(40, "prev")
    panel.alpha_composite(prev_btn, (center_x - 70, center_y - 20))
    
    play_btn = create_spotify_play_button(64)
    panel.alpha_composite(play_btn, (center_x - 32, center_y - 32))
    
    next_btn = create_spotify_nav_button(40, "next")
    panel.alpha_composite(next_btn, (center_x + 30, center_y - 20))
    
    repeat_btn = create_repeat_button(36)
    panel.alpha_composite(repeat_btn, (center_x + 85, center_y - 18))
    
    return panel

def create_now_playing_badge(width, height=30):
    """Create NOW PLAYING badge"""
    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    
    draw.rounded_rectangle(
        (0, 0, width, height),
        radius=height // 2,
        fill=(147, 51, 234, 30)
    )
    
    draw.rounded_rectangle(
        (0, 0, width, height),
        radius=height // 2,
        outline=(147, 51, 234, 80),
        width=1
    )
    
    return badge

# ================= MAIN FUNCTION =================

async def get_thumb(videoid, user_id=None):
    """Generate premium neon purple thumbnail for music bot."""
    
    ensure_cache_dir()
    
    cache_name = f"spotify_{videoid}_{user_id}.png" if user_id else f"spotify_{videoid}_thumb.png"
    cache_path = os.path.join(CACHE_DIR, cache_name)
    
    if os.path.exists(cache_path):
        return cache_path
    
    # ========== FETCH VIDEO DATA ==========
    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        vs = VideosSearch(url, limit=1)
        results = await vs.next()
        data = results["result"][0]
        
        title = re.sub(r"[^\w\s-]", "", data.get("title", "Unknown Title")).strip()
        title = re.sub(r"\s+", " ", title)
        
        artist = data.get("channel", {}).get("name", "Unknown Artist")
        duration = data.get("duration", "0:00")
        views = data.get("viewCount", {}).get("text", "0 views")
        
        thumb_url = data.get("thumbnails", [{}])[-1].get("url", "")
        if thumb_url:
            thumb_url = thumb_url.split("?")[0]
        
        if not thumb_url:
            return YOUTUBE_IMG_URL
            
    except Exception as e:
        print(f"[Thumbnail] Error fetching data: {e}")
        return YOUTUBE_IMG_URL
    
    # ========== DOWNLOAD COVER ART ==========
    thumb_file = os.path.join(CACHE_DIR, f"{videoid}_raw.jpg")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url, timeout=10) as resp:
                if resp.status != 200:
                    return YOUTUBE_IMG_URL
                    
                async with aiofiles.open(thumb_file, "wb") as f:
                    await f.write(await resp.read())
    except Exception as e:
        print(f"[Thumbnail] Error downloading cover: {e}")
        return YOUTUBE_IMG_URL
    
    # ========== CREATE PREMIUM CANVAS ==========
    try:
        cover_img = Image.open(thumb_file).convert("RGBA")
        
        # ===== ENHANCED BACKGROUND =====
        bg = create_gradient_background(CANVAS_SIZE[0], CANVAS_SIZE[1], ROYAL_PURPLE, DARK_BG)
        canvas = Image.new("RGBA", CANVAS_SIZE)
        canvas.paste(bg, (0, 0))
        
        # Multiple glow effects for richer background
        glow1 = create_radial_glow(
            CANVAS_SIZE, NEON_PURPLE,
            center=(CANVAS_SIZE[0] // 3, CANVAS_SIZE[1] // 2),
            intensity=0.08
        )
        canvas = Image.alpha_composite(canvas, glow1)
        
        glow2 = create_radial_glow(
            CANVAS_SIZE, NEON_MAGENTA,
            center=(CANVAS_SIZE[0] * 2 // 3, CANVAS_SIZE[1] // 3),
            intensity=0.06
        )
        canvas = Image.alpha_composite(canvas, glow2)
        
        # Third glow for depth
        glow3 = create_radial_glow(
            CANVAS_SIZE, NEON_VIOLET,
            center=(CANVAS_SIZE[0] // 2, CANVAS_SIZE[1] * 3 // 4),
            intensity=0.05
        )
        canvas = Image.alpha_composite(canvas, glow3)
        
        # Light streaks for premium look
        streaks = create_light_streaks(CANVAS_SIZE, NEON_PURPLE_LIGHT, 4)
        canvas = Image.alpha_composite(canvas, streaks)
        
        # Particles
        particles = create_particle_field(CANVAS_SIZE, NEON_PURPLE_LIGHT, 70)
        canvas = Image.alpha_composite(canvas, particles)
        
        # ===== PROCESS COVER ART =====
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        cover = ImageEnhance.Contrast(cover).enhance(1.15)
        cover = ImageEnhance.Color(cover).enhance(1.1)
        cover = ImageEnhance.Sharpness(cover).enhance(1.2)
        cover = ImageEnhance.Brightness(cover).enhance(1.05)
        
        frame = create_cover_art_frame((COVER_SIZE, COVER_SIZE), 20)
        
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle(
            (0, 0, COVER_SIZE, COVER_SIZE), radius=20, fill=255
        )
        cover.putalpha(cover_mask)
        
        frame_with_cover = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        frame_with_cover.paste(frame, (0, 0))
        frame_with_cover.paste(cover, (20, 20), cover)
        
        canvas.alpha_composite(frame_with_cover, (COVER_X - 20, COVER_Y - 20 - 5))
        
        # ===== LOAD FONTS =====
        font_paths = [
            "AnonXMusic/assets/font2.ttf",
            "AnonXMusic/assets/font.ttf",
        ]
        
        title_font = None
        artist_font = None
        subtitle_font = None
        small_font = None
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    title_font = ImageFont.truetype(font_path, 46)
                    artist_font = ImageFont.truetype(font_path, 26)
                    subtitle_font = ImageFont.truetype(font_path, 18)
                    small_font = ImageFont.truetype(font_path, 15)
                    break
            except:
                continue
        
        if title_font is None:
            title_font = ImageFont.load_default()
            artist_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(canvas)
        
        # ===== NOW PLAYING - GLOWING WHITE TEXT ✨ =====
        badge_width = 210
        badge = create_now_playing_badge(badge_width, 34)
        canvas.alpha_composite(badge, (RIGHT_START_X - 5, NOW_PLAYING_Y - 10))
        
        # Glow layers for NOW PLAYING
        for offset in range(4, 0, -1):
            alpha = 60 - offset * 12
            draw.text(
                (RIGHT_START_X + 15 - offset, NOW_PLAYING_Y - 3 - offset),
                "◆ NOW PLAYING",
                font=subtitle_font,
                fill=(*NEON_PURPLE_LIGHT, alpha)  # Purple glow
            )
        
        # Main text - Bright white with eye-catching visibility
        draw.text(
            (RIGHT_START_X + 15, NOW_PLAYING_Y - 3),
            "◆ NOW PLAYING",
            font=subtitle_font,
            fill=(255, 255, 255, 255)  # Full bright white
        )
        
        # ===== SONG TITLE =====
        title_text = trim_text(title, title_font, RIGHT_WIDTH)
        
        # Soft shadow
        draw.text(
            (RIGHT_START_X + 2, TITLE_Y + 2),
            title_text,
            font=title_font,
            fill=(0, 0, 0, 60)
        )
        
        # Main title
        draw.text(
            (RIGHT_START_X, TITLE_Y),
            title_text,
            font=title_font,
            fill=WHITE
        )
        
        # Title accent line
        title_bbox = draw.textbbox((RIGHT_START_X, TITLE_Y), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        accent_y = TITLE_Y + title_font.size + 8
        
        accent_width = min(title_width, 200)
        for i in range(3):
            alpha = 150 - i * 50
            draw.line(
                [(RIGHT_START_X, accent_y + i), (RIGHT_START_X + accent_width, accent_y + i)],
                fill=(*NEON_PURPLE, alpha),
                width=2
            )
        
        # ===== ARTIST NAME =====
        artist_text = trim_text(artist, artist_font, RIGHT_WIDTH - 40)
        draw.text((RIGHT_START_X, ARTIST_Y), artist_text, font=artist_font, fill=LIGHT_GRAY)
        
        # Verified badge
        badge_size = 20
        try:
            artist_text_width = draw.textlength(artist_text, font=artist_font)
        except:
            artist_bbox = draw.textbbox((0, 0), artist_text, font=artist_font)
            artist_text_width = artist_bbox[2] - artist_bbox[0]
        
        badge_x = RIGHT_START_X + int(artist_text_width) + 10
        badge_y = ARTIST_Y + 8
        
        draw.ellipse(
            (badge_x, badge_y, badge_x + badge_size, badge_y + badge_size),
            fill=SPOTIFY_GREEN
        )
        draw.text((badge_x + 4, badge_y + 2), "✓", font=small_font, fill=WHITE)
        
        # ===== ALBUM/YEAR INFO =====
        draw.text(
            (RIGHT_START_X, ALBUM_INFO_Y),
            f"Album • {views} • YouTube Music",
            font=subtitle_font,
            fill=DARK_GRAY
        )
        
        # ===== PROGRESS BAR =====
        current_time = "0:00"
        progress_value = 0.3
        if ":" in duration:
            time_parts = duration.split(":")
            if len(time_parts) == 2:
                try:
                    minutes, seconds = time_parts
                    current_duration = int(minutes) * 60 + int(seconds)
                    progress_value = min(0.3, current_duration / (current_duration + 180))
                    current_time = f"{int(current_duration * progress_value // 60)}:{int(current_duration * progress_value % 60):02d}"
                except:
                    current_time = "0:00"
        
        progress_bar = create_spotify_progress_bar(
            RIGHT_WIDTH, 6, progress_value, current_time, duration
        )
        canvas.alpha_composite(progress_bar, (RIGHT_START_X, PROGRESS_Y))
        
        # ===== CONTROLS =====
        try:
            controls = create_spotify_controls()
            controls_x = RIGHT_START_X + (RIGHT_WIDTH - 350) // 2
            controls_y = CONTROLS_Y
            canvas.alpha_composite(controls, (controls_x, controls_y))
        except Exception as e:
            print(f"[Thumbnail] Error creating controls: {e}")
            draw.text(
                (RIGHT_START_X + RIGHT_WIDTH // 4, CONTROLS_Y + 30),
                "⏮  ▶  ⏭",
                font=title_font,
                fill=WHITE
            )
        
        # ===== VOLUME BAR =====
        volume_y = CONTROLS_Y + 130
        volume_width = 120
        
        draw.text((RIGHT_START_X, volume_y), "🔊", font=small_font, fill=LIGHT_GRAY)
        
        volume_bar_x = RIGHT_START_X + 25
        volume_bar_y = volume_y + 8
        
        draw.rounded_rectangle(
            (volume_bar_x, volume_bar_y, volume_bar_x + volume_width, volume_bar_y + 4),
            radius=2,
            fill=(255, 255, 255, 15)
        )
        
        fill_width = int(volume_width * 0.7)
        draw.rounded_rectangle(
            (volume_bar_x, volume_bar_y, volume_bar_x + fill_width, volume_bar_y + 4),
            radius=2,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== BOTTOM DECORATIVE LINE =====
        line_y = CANVAS_SIZE[1] - 55
        for i in range(3):
            alpha = 60 - i * 20
            draw.line(
                [(30, line_y + i), (CANVAS_SIZE[0] - 30, line_y + i)],
                fill=(*NEON_PURPLE, alpha),
                width=1
            )
        
        # ===== SIGNATURE - GLOWING WHITE TEXT ✨ =====
        signature = "Made with ❤ by @DivineDemonn"
        
        # Glow layers for signature
        for offset in range(3, 0, -1):
            alpha = 50 - offset * 12
            draw.text(
                (35 - offset, CANVAS_SIZE[1] - 40 - offset),
                signature,
                font=small_font,
                fill=(*NEON_PURPLE_LIGHT, alpha)  # Purple glow
            )
        
        # Shadow for depth
        draw.text(
            (36, CANVAS_SIZE[1] - 39),
            signature,
            font=small_font,
            fill=(0, 0, 0, 80)
        )
        
        # Main text - Bright glowing white
        draw.text(
            (35, CANVAS_SIZE[1] - 40),
            signature,
            font=small_font,
            fill=(255, 255, 255, 255)  # Full bright white
        )
        
        # ===== VERSION BADGE =====
        badge_text = "PREMIUM HD"
        badge_bbox = draw.textbbox((0, 0), badge_text, font=small_font)
        badge_w = badge_bbox[2] - badge_bbox[0] + 20
        badge_h = 24
        
        badge_x = CANVAS_SIZE[0] - badge_w - 30
        badge_y = CANVAS_SIZE[1] - 45
        
        draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
            radius=12,
            fill=(147, 51, 234, 40),
            outline=(147, 51, 234, 80),
            width=1
        )
        
        draw.text(
            (badge_x + 10, badge_y + 4),
            badge_text,
            font=small_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SAVE =====
        final_canvas = canvas.convert("RGB")
        final_canvas.save(cache_path, "PNG", quality=100, optimize=True)
        
        cover_img.close()
        canvas.close()
        final_canvas.close()
        bg.close()
        
        try:
            os.remove(thumb_file)
        except:
            pass
        
        # Cache cleanup
        try:
            cache_files = sorted(
                [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f.endswith('.png')],
                key=os.path.getmtime,
                reverse=True
            )
            for old_file in cache_files[15:]:
                try:
                    os.remove(old_file)
                except:
                    pass
        except:
            pass
        
        return cache_path
        
    except Exception as e:
        print(f"[Thumbnail] Error generating thumbnail: {e}")
        traceback.print_exc()
        
        try:
            os.remove(thumb_file)
        except:
            pass
        
        return YOUTUBE_IMG_URL
