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
DARK_BG = (6, 2, 20)                      # Ultra deep purple-black
NEON_PURPLE = (147, 51, 234)              # #9333EA - Vibrant purple
NEON_PURPLE_LIGHT = (168, 85, 247)        # #A855F7 - Light purple
NEON_PURPLE_PINK = (192, 38, 211)         # #C026D3 - Purple-pink
NEON_MAGENTA = (217, 70, 239)             # #D946EF - Magenta
NEON_VIOLET = (139, 92, 246)              # #8B5CF6 - Violet
ACCENT_PURPLE = (186, 104, 200)           # Soft accent
DEEP_PURPLE = (48, 12, 72)                # Very dark purple
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

# ================= PROFESSIONAL VISUAL EFFECTS =================

def create_gradient_background(width, height, color1, color2, angle=0):
    """Create smooth gradient background with angle support"""
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    for i in range(height):
        ratio = i / height
        # Add subtle curve to gradient
        curve_ratio = math.sin(ratio * math.pi * 0.5)
        r = int(color1[0] * (1 - curve_ratio) + color2[0] * curve_ratio)
        g = int(color1[1] * (1 - curve_ratio) + color2[1] * curve_ratio)
        b = int(color1[2] * (1 - curve_ratio) + color2[2] * curve_ratio)
        draw.line([(0, i), (width, i)], fill=(r, g, b, 255))
    
    return gradient

def create_radial_glow(size, color, center=None, intensity=0.08):
    """Create elegant radial glow effect"""
    if center is None:
        center = (size[0] // 2, size[1] // 2)
    
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    max_radius = int(math.sqrt(size[0]**2 + size[1]**2)) // 2
    
    for radius in range(max_radius, 0, -80):
        alpha = int(255 * intensity * (radius / max_radius) * 0.3)
        draw.ellipse(
            (center[0] - radius, center[1] - radius,
             center[0] + radius, center[1] + radius),
            outline=(*color, min(alpha, 8)),
            width=3
        )
    
    return glow.filter(ImageFilter.GaussianBlur(40))

def create_noise_overlay(size, opacity=5):
    """Add subtle noise texture for premium feel"""
    noise = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = noise.load()
    
    for x in range(size[0]):
        for y in range(size[1]):
            if random.random() < 0.1:
                gray = random.randint(0, 255)
                pixels[x, y] = (gray, gray, gray, opacity)
    
    return noise

def create_glass_effect(size, corner_radius=20):
    """Create glass morphism effect panel"""
    glass = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glass)
    
    # Main glass panel
    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius=corner_radius,
        fill=(255, 255, 255, 8)
    )
    
    # Glass border
    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius=corner_radius,
        outline=(255, 255, 255, 20),
        width=1
    )
    
    # Top highlight
    draw.rounded_rectangle(
        (0, 0, size[0], size[1] // 2),
        radius=corner_radius,
        fill=(255, 255, 255, 5)
    )
    
    return glass

def create_particle_field(size, color, count=120):
    """Create elegant floating particles"""
    particles = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(particles)
    random.seed(42)
    
    for _ in range(count):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        radius = random.randint(1, 3)
        alpha = random.randint(10, 40)
        
        # Create tiny glowing dots
        for r in range(radius, 0, -1):
            a = alpha * (r / radius)
            draw.ellipse(
                (x - r, y - r, x + r, y + r),
                fill=(*color, int(a))
            )
    
    return particles

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
    """Create Spotify-style play button with circular design"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    # Outer shadow
    for i in range(8, 0, -2):
        alpha = int(15 * (i / 8))
        draw.ellipse(
            (center - size//2 - i, center - size//2 - i,
             center + size//2 + i, center + size//2 + i),
            fill=(0, 0, 0, alpha)
        )
    
    # Main circle background - Spotify green
    draw.ellipse(
        (center - size//2 + 3, center - size//2 + 3,
         center + size//2 - 3, center + size//2 - 3),
        fill=SPOTIFY_GREEN
    )
    
    # Inner gradient effect
    for i in range(size//2 - 3, size//4, -1):
        ratio = (i - size//4) / (size//2 - size//4)
        color = blend_colors(SPOTIFY_GREEN, (50, 230, 120), ratio)
        alpha = int(100 * ratio)
        draw.ellipse(
            (center - i, center - i, center + i, center + i),
            fill=(*color, alpha)
        )
    
    # White play triangle
    triangle_size = size // 5
    offset_x = 2  # Slight right offset for visual balance
    points = [
        (center - triangle_size + offset_x, center - triangle_size),
        (center - triangle_size + offset_x, center + triangle_size),
        (center + triangle_size + offset_x, center)
    ]
    draw.polygon(points, fill=WHITE)
    
    # Subtle border
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
    
    # Circular background with glass effect
    draw.ellipse(
        (2, 2, size - 2, size - 2),
        fill=(255, 255, 255, 12)
    )
    
    # Border
    draw.ellipse(
        (2, 2, size - 2, size - 2),
        outline=(255, 255, 255, 25),
        width=1.5
    )
    
    if direction == "prev":
        # Previous track icon (two triangles + bar)
        bar_x = size // 4 + 2
        tri_w = size // 6
        tri_h = size // 4
        
        # Vertical bar
        draw.rectangle(
            (bar_x - 1.5, center - tri_h, bar_x + 1.5, center + tri_h),
            fill=(255, 255, 255, 200)
        )
        
        # Two triangles pointing left
        for offset in [0, size // 5]:
            points = [
                (bar_x + 4 + offset, center - tri_h),
                (bar_x + 4 + offset, center + tri_h),
                (bar_x + 4 - tri_w + offset, center)
            ]
            draw.polygon(points, fill=(255, 255, 255, 200))
    
    elif direction == "next":
        # Next track icon (two triangles + bar)
        bar_x = size - size // 4 - 2
        tri_w = size // 6
        tri_h = size // 4
        
        # Vertical bar
        draw.rectangle(
            (bar_x - 1.5, center - tri_h, bar_x + 1.5, center + tri_h),
            fill=(255, 255, 255, 200)
        )
        
        # Two triangles pointing right
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
    
    # Two crossed arrows
    arrow_color = (255, 255, 255, 180)
    offset = size // 4
    
    # Arrow 1 (up-right)
    points1 = [
        (offset, size - offset),
        (size - offset, offset),
        (size - offset - 5, offset + 5),
        (offset + 3, size - offset - 3)
    ]
    draw.line(points1[:2], fill=arrow_color, width=2)
    
    # Arrow 2 (down-right)
    points2 = [
        (offset, offset),
        (size - offset, size - offset),
        (size - offset - 5, size - offset - 5),
        (offset + 3, offset + 3)
    ]
    draw.line(points2[:2], fill=arrow_color, width=2)
    
    return btn

def create_repeat_button(size=40):
    """Create repeat button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    # Circular arrows
    bbox = (center - 8, center - 12, center + 8, center + 12)
    draw.arc(bbox, 45, 315, fill=(255, 255, 255, 180), width=2)
    
    # Arrow head
    arrow_pos = (bbox[2], bbox[2] - 5)
    draw.polygon([
        (arrow_pos[0] + 3, arrow_pos[1] - 5),
        (arrow_pos[0] - 5, arrow_pos[1]),
        (arrow_pos[0] + 3, arrow_pos[1] + 5)
    ], fill=(255, 255, 255, 180))
    
    return btn

def create_spotify_progress_bar(width, height, progress=0.3, current_time="1:15", total_time="3:56"):
    """Create Spotify-style progress bar"""
    bar_height = height
    bar_image = Image.new("RGBA", (width, bar_height + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar_image)
    
    bar_y = 15
    bar_radius = bar_height // 2
    
    # Background track
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_height),
        radius=bar_radius,
        fill=(255, 255, 255, 15)
    )
    
    # Progress fill with gradient
    fill_width = int(width * progress)
    if fill_width > 0:
        # Glow under progress
        for i in range(4, 0, -1):
            alpha = int(8 * (i / 4))
            draw.rounded_rectangle(
                (0 - i, bar_y - i, fill_width + i, bar_y + bar_height + i),
                radius=bar_radius + i,
                fill=(*SPOTIFY_GREEN, alpha)
            )
        
        # Main progress
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height),
            radius=bar_radius,
            fill=SPOTIFY_GREEN
        )
        
        # Progress highlight
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height // 2),
            radius=bar_radius,
            fill=(255, 255, 255, 20)
        )
        
        # Thumb dot
        dot_radius = 7
        dot_x = fill_width
        dot_y = bar_y + bar_height // 2
        
        # Dot shadow
        for i in range(3, 0, -1):
            alpha = int(15 * (i / 3))
            draw.ellipse(
                (dot_x - dot_radius - i, dot_y - dot_radius - i,
                 dot_x + dot_radius + i, dot_y + dot_radius + i),
                fill=(0, 0, 0, alpha)
            )
        
        # Dot fill
        draw.ellipse(
            (dot_x - dot_radius, dot_y - dot_radius,
             dot_x + dot_radius, dot_y + dot_radius),
            fill=WHITE
        )
        
        # Dot border
        draw.ellipse(
            (dot_x - dot_radius, dot_y - dot_radius,
             dot_x + dot_radius, dot_y + dot_radius),
            outline=SPOTIFY_GREEN,
            width=2
        )
    
    # Time labels
    try:
        time_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 14)
    except:
        try:
            time_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 14)
        except:
            time_font = ImageFont.load_default()
    
    # Current time
    draw.text((0, bar_y + bar_height + 8), current_time, fill=(255, 255, 255, 160), font=time_font)
    
    # Total time
    total_time_bbox = draw.textbbox((0, 0), total_time, font=time_font)
    total_time_width = total_time_bbox[2] - total_time_bbox[0]
    draw.text(
        (width - total_time_width, bar_y + bar_height + 8),
        total_time,
        fill=(255, 255, 255, 160),
        font=time_font
    )
    
    return bar_image

def create_spotify_controls():
    """Create complete Spotify-style control panel"""
    panel_width = 350
    panel_height = 120
    
    panel = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    
    # Glass background for controls
    glass = create_glass_effect((panel_width, panel_height), 15)
    panel = Image.alpha_composite(panel, glass)
    
    # Button positions
    center_x = panel_width // 2
    center_y = panel_height // 2
    
    # Shuffle button (left side)
    shuffle_btn = create_shuffle_button(36)
    shuffle_x = center_x - 120
    shuffle_y = center_y - 18
    panel.alpha_composite(shuffle_btn, (shuffle_x, shuffle_y))
    
    # Previous button
    prev_btn = create_spotify_nav_button(40, "prev")
    prev_x = center_x - 70
    prev_y = center_y - 20
    panel.alpha_composite(prev_btn, (prev_x, prev_y))
    
    # Play button (center, larger)
    play_btn = create_spotify_play_button(64)
    play_x = center_x - 32
    play_y = center_y - 32
    panel.alpha_composite(play_btn, (play_x, play_y))
    
    # Next button
    next_btn = create_spotify_nav_button(40, "next")
    next_x = center_x + 30
    next_y = center_y - 20
    panel.alpha_composite(next_btn, (next_x, next_y))
    
    # Repeat button (right side)
    repeat_btn = create_repeat_button(36)
    repeat_x = center_x + 85
    repeat_y = center_y - 18
    panel.alpha_composite(repeat_btn, (repeat_x, repeat_y))
    
    return panel

def create_now_playing_badge(width, height=30):
    """Create animated-style NOW PLAYING badge"""
    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    
    # Glass background
    draw.rounded_rectangle(
        (0, 0, width, height),
        radius=height // 2,
        fill=(147, 51, 234, 25)
    )
    
    # Border
    draw.rounded_rectangle(
        (0, 0, width, height),
        radius=height // 2,
        outline=(147, 51, 234, 60),
        width=1
    )
    
    return badge

# ================= MAIN FUNCTION =================

async def get_thumb(videoid, user_id=None):
    """
    Generate premium Spotify-style neon purple thumbnail for music bot.
    
    Args:
        videoid: YouTube video ID
        user_id: Optional user ID for caching
        
    Returns:
        Path to generated thumbnail image
    """
    # Ensure cache directory exists
    ensure_cache_dir()
    
    # Generate cache filename
    cache_name = f"spotify_{videoid}_{user_id}.png" if user_id else f"spotify_{videoid}_thumb.png"
    cache_path = os.path.join(CACHE_DIR, cache_name)
    
    # Return cached if exists
    if os.path.exists(cache_path):
        return cache_path
    
    # ========== FETCH VIDEO DATA ==========
    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        vs = VideosSearch(url, limit=1)
        results = await vs.next()
        data = results["result"][0]
        
        # Extract and clean data
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
        traceback.print_exc()
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
        # Load cover art
        cover_img = Image.open(thumb_file).convert("RGBA")
        
        # Create canvas with gradient background
        bg = create_gradient_background(
            CANVAS_SIZE[0], CANVAS_SIZE[1],
            DEEP_PURPLE, DARK_BG
        )
        canvas = Image.new("RGBA", CANVAS_SIZE)
        canvas.paste(bg, (0, 0))
        
        # ===== ADD PREMIUM BACKGROUND EFFECTS =====
        # Radial glow
        glow1 = create_radial_glow(
            CANVAS_SIZE, NEON_PURPLE,
            center=(CANVAS_SIZE[0] // 3, CANVAS_SIZE[1] // 2),
            intensity=0.06
        )
        canvas = Image.alpha_composite(canvas, glow1)
        
        # Second glow for depth
        glow2 = create_radial_glow(
            CANVAS_SIZE, NEON_MAGENTA,
            center=(CANVAS_SIZE[0] * 2 // 3, CANVAS_SIZE[1] // 3),
            intensity=0.04
        )
        canvas = Image.alpha_composite(canvas, glow2)
        
        # Particles
        particles = create_particle_field(CANVAS_SIZE, NEON_PURPLE_LIGHT, 100)
        canvas = Image.alpha_composite(canvas, particles)
        
        # Noise overlay for premium texture
        noise = create_noise_overlay(CANVAS_SIZE, 3)
        canvas = Image.alpha_composite(canvas, noise)
        
        # ===== PROCESS COVER ART ====
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        
        # Enhance cover art
        cover = ImageEnhance.Contrast(cover).enhance(1.15)
        cover = ImageEnhance.Color(cover).enhance(1.1)
        cover = ImageEnhance.Sharpness(cover).enhance(1.2)
        cover = ImageEnhance.Brightness(cover).enhance(1.05)
        
        # Create cover frame with shadow
        frame = create_cover_art_frame((COVER_SIZE, COVER_SIZE), 20)
        
        # Apply rounded corners to cover
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle(
            (0, 0, COVER_SIZE, COVER_SIZE),
            radius=20,
            fill=255
        )
        cover.putalpha(cover_mask)
        
        # Paste frame and cover
        frame_with_cover = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        frame_with_cover.paste(frame, (0, 0))
        frame_with_cover.paste(cover, (20, 20), cover)
        
        canvas.alpha_composite(frame_with_cover, (COVER_X - 20, COVER_Y - 20 - 5))
        
        # ===== LOAD FONTS =====
        font_paths = [
            "AnonXMusic/assets/font2.ttf",
            "AnonXMusic/assets/font.ttf",
        ]
        
        # Try to use premium fonts
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
        
        # ===== NOW PLAYING BADGE =====
        badge_width = 180
        badge = create_now_playing_badge(badge_width, 32)
        canvas.alpha_composite(badge, (RIGHT_START_X, NOW_PLAYING_Y - 8))
        
        # NOW PLAYING text
        draw.text(
            (RIGHT_START_X + 15, NOW_PLAYING_Y - 2),
            "◆ NOW PLAYING",
            font=subtitle_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SONG TITLE WITH GLOW =====
        title_text = trim_text(title, title_font, RIGHT_WIDTH)
        
        # Multiple glow layers for premium look
        for offset in range(5, 0, -1):
            alpha = 30 - offset * 5
            draw.text(
                (RIGHT_START_X - offset, TITLE_Y - offset),
                title_text,
                font=title_font,
                fill=(*NEON_PURPLE, alpha)
            )
        
        # Main title
        draw.text(
            (RIGHT_START_X, TITLE_Y),
            title_text,
            font=title_font,
            fill=WHITE
        )
        
        # Title underline accent
        title_bbox = draw.textbbox((RIGHT_START_X, TITLE_Y), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        accent_y = TITLE_Y + title_font.size + 8
        
        # Gradient accent line under title
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
        
        draw.text(
            (RIGHT_START_X, ARTIST_Y),
            artist_text,
            font=artist_font,
            fill=LIGHT_GRAY
        )
        
        # Verified badge
        badge_size = 20
        badge_x = RIGHT_START_X + draw.textlength(artist_text, font=artist_font) + 10
        badge_y = ARTIST_Y + 8
        
        # Simple checkmark circle
        draw.ellipse(
            (badge_x, badge_y, badge_x + badge_size, badge_y + badge_size),
            fill=SPOTIFY_GREEN
        )
        draw.text(
            (badge_x + 4, badge_y + 2),
            "✓",
            font=small_font,
            fill=WHITE
        )
        
        # ===== ALBUM/YEAR INFO =====
        draw.text(
            (RIGHT_START_X, ALBUM_INFO_Y),
            f"Album • {views} • YouTube Music",
            font=subtitle_font,
            fill=DARK_GRAY
        )
        
        # ===== SPOTIFY-STYLE PROGRESS BAR =====
        # Parse duration for progress display
        current_time = "0:00"
        if ":" in duration:
            time_parts = duration.split(":")
            if len(time_parts) == 2:
                minutes, seconds = time_parts
                current_duration = int(minutes) * 60 + int(seconds)
                # Show 30% progress for preview
                progress_value = min(0.3, current_duration / (current_duration + 180))
                current_time = f"{int(current_duration * progress_value // 60)}:{int(current_duration * progress_value % 60):02d}"
            else:
                current_time = "0:00"
        
        progress_bar = create_spotify_progress_bar(
            RIGHT_WIDTH, 6, 0.3, current_time, duration
        )
        canvas.alpha_composite(progress_bar, (RIGHT_START_X, PROGRESS_Y))
        
        # ===== SPOTIFY-STYLE CONTROLS =====
        controls = create_spotify_controls()
        controls_x = RIGHT_START_X + (RIGHT_WIDTH - 350) // 2
        controls_y = CONTROLS_Y
        canvas.alpha_composite(controls, (controls_x, controls_y))
        
        # ===== VOLUME BAR (BOTTOM) =====
        volume_y = controls_y + 130
        volume_width = 120
        
        # Volume icon
        draw.text(
            (RIGHT_START_X, volume_y),
            "🔊",
            font=small_font,
            fill=LIGHT_GRAY
        )
        
        # Volume bar
        volume_bar_x = RIGHT_START_X + 25
        volume_bar_y = volume_y + 8
        
        # Background
        draw.rounded_rectangle(
            (volume_bar_x, volume_bar_y, volume_bar_x + volume_width, volume_bar_y + 4),
            radius=2,
            fill=(255, 255, 255, 15)
        )
        
        # Fill (70%)
        fill_width = int(volume_width * 0.7)
        draw.rounded_rectangle(
            (volume_bar_x, volume_bar_y, volume_bar_x + fill_width, volume_bar_y + 4),
            radius=2,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SONG QUEUE INFO (BOTTOM RIGHT) =====
        queue_y = volume_y
        queue_x = RIGHT_START_X + RIGHT_WIDTH - 200
        
        draw.text(
            (queue_x, queue_y),
            "📋 Queue",
            font=small_font,
            fill=DARK_GRAY
        )
        
        draw.text(
            (queue_x + 50, queue_y),
            f"▶ {title[:20]}...",
            font=small_font,
            fill=(255, 255, 255, 100)
        )
        
        # ===== BOTTOM DECORATIVE LINE =====
        line_y = CANVAS_SIZE[1] - 55
        # Gradient line
        for i in range(3):
            alpha = 60 - i * 20
            draw.line(
                [(30, line_y + i), (CANVAS_SIZE[0] - 30, line_y + i)],
                fill=(*NEON_PURPLE, alpha),
                width=1
            )
        
        # ===== SIGNATURE (BOTTOM LEFT) =====
        signature = "Made with 🤍 by @DivineDemonn"
        
        # Glow effect
        for offset in range(2, 0, -1):
            draw.text(
                (35 - offset, CANVAS_SIZE[1] - 40 - offset),
                signature,
                font=small_font,
                fill=(*WHITE, 20 - offset * 5)
            )
        
        draw.text(
            (35, CANVAS_SIZE[1] - 40),
            signature,
            font=small_font,
            fill=(255, 255, 255, 150)
        )
        
        # ===== VERSION & QUALITY BADGE (BOTTOM RIGHT) =====
        badge_text = "PREMIUM HD"
        badge_bbox = draw.textbbox((0, 0), badge_text, font=small_font)
        badge_w = badge_bbox[2] - badge_bbox[0] + 20
        badge_h = 24
        
        badge_x = CANVAS_SIZE[0] - badge_w - 30
        badge_y = CANVAS_SIZE[1] - 45
        
        # Badge background
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
        
        # ===== SAVE THUMBNAIL =====
        final_canvas = canvas.convert("RGB")
        final_canvas.save(cache_path, "PNG", quality=100, optimize=True)
        
        # ===== CLEANUP =====
        cover_img.close()
        canvas.close()
        final_canvas.close()
        bg.close()
        
        try:
            os.remove(thumb_file)
        except:
            pass
        
        # ===== MANAGE CACHE SIZE =====
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
