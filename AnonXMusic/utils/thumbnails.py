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
DARK_BG = (4, 1, 15)
NEON_PURPLE = (147, 51, 234)
NEON_PURPLE_LIGHT = (175, 90, 250)
NEON_PURPLE_PINK = (192, 38, 211)
NEON_MAGENTA = (220, 75, 242)
NEON_VIOLET = (139, 92, 246)
ACCENT_PURPLE = (186, 104, 200)
DEEP_PURPLE = (30, 8, 55)
ROYAL_PURPLE = (60, 15, 100)
WHITE = (255, 255, 255)
PURE_WHITE = (255, 255, 255, 255)
LIGHT_GRAY = (230, 225, 240)
DARK_GRAY = (120, 110, 130)
SOFT_WHITE = (245, 240, 250)

# ================= SPOTIFY-STYLE BUTTON COLORS =================
SPOTIFY_GREEN = (30, 215, 96)
BUTTON_BG = (40, 40, 50, 120)
BUTTON_HOVER = (60, 55, 70, 160)

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
PROGRESS_Y = ALBUM_INFO_Y + 75
TIME_Y = PROGRESS_Y + 55
CONTROLS_Y = TIME_Y + 70

# ================= HELPER FUNCTIONS =================

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def trim_text(text, font, max_width):
    try:
        if font.getlength(text) <= max_width:
            return text
        while font.getlength(text + "…") > max_width:
            text = text[:-1]
        return text + "…"
    except:
        return text[:30] + "..." if len(text) > 30 else text

def blend_colors(color1, color2, ratio=0.5):
    return tuple(
        max(0, min(255, int(c1 * (1 - ratio) + c2 * ratio)))
        for c1, c2 in zip(color1, color2)
    )

def get_centered_x(text, font, container_width, container_start_x=0):
    """Get x position to center text within a container"""
    try:
        text_width = font.getlength(text)
    except:
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0] if bbox else len(text) * 10
    return container_start_x + (container_width - text_width) // 2

# ================= ENHANCED BACKGROUND EFFECTS =================

def create_gradient_background(width, height, color1, color2):
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    for i in range(height):
        ratio = i / height
        curve = math.sin(ratio * math.pi * 0.6) ** 1.8
        r = int(color1[0] * (1 - curve) + color2[0] * curve)
        g = int(color1[1] * (1 - curve) + color2[1] * curve)
        b = int(color1[2] * (1 - curve) + color2[2] * curve)
        draw.line([(0, i), (width, i)], fill=(r, g, b, 255))
    
    return gradient

def create_radial_glow(size, color, center=None, intensity=0.1):
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
            outline=(*color, alpha), width=5
        )
    
    return glow.filter(ImageFilter.GaussianBlur(45))

def create_particle_field(size, color, count=80):
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
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*color, int(a)))
    
    return particles

def create_light_streaks(size, color, count=5):
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
    frame = Image.new("RGBA", (size[0] + border_width * 2, size[1] + border_width * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    
    for i in range(border_width, 0, -1):
        alpha = int(30 * (i / border_width))
        draw.rounded_rectangle(
            (i, i + 5, size[0] + border_width * 2 - i, size[1] + border_width * 2 - i + 5),
            radius=24, fill=(0, 0, 0, alpha)
        )
    
    for i in range(3, 0, -1):
        alpha = int(40 * (i / 3))
        draw.rounded_rectangle(
            (border_width - i, border_width - i,
             size[0] + border_width + i, size[1] + border_width + i),
            radius=22 + i, outline=(*NEON_PURPLE, alpha), width=2
        )
    
    draw.rounded_rectangle(
        (border_width + 2, border_width + 2,
         size[0] + border_width - 2, size[1] + border_width - 2),
        radius=18, outline=(255, 255, 255, 30), width=1
    )
    
    return frame.filter(ImageFilter.GaussianBlur(5))

# ================= SPOTIFY-STYLE BUTTONS =================

def create_spotify_play_button(size=72):
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
        draw.ellipse((center - i, center - i, center + i, center + i), fill=(*color, alpha))
    
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
        outline=(255, 255, 255, 30), width=1
    )
    
    return btn

def create_spotify_nav_button(size=44, direction="prev"):
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
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    arrow_color = (255, 255, 255, 180)
    offset = size // 4
    
    points1 = [
        (offset, size - offset), (size - offset, offset),
        (size - offset - 5, offset + 5), (offset + 3, size - offset - 3)
    ]
    draw.line([points1[0], points1[1]], fill=arrow_color, width=2)
    draw.line([points1[2], points1[3]], fill=arrow_color, width=2)
    
    points2 = [
        (offset, offset), (size - offset, size - offset),
        (size - offset - 5, size - offset - 5), (offset + 3, offset + 3)
    ]
    draw.line([points2[0], points2[1]], fill=arrow_color, width=2)
    draw.line([points2[2], points2[3]], fill=arrow_color, width=2)
    
    draw.polygon([
        (size - offset, offset), (size - offset - 8, offset + 3), (size - offset - 3, offset + 8)
    ], fill=arrow_color)
    draw.polygon([
        (size - offset, size - offset), (size - offset - 8, size - offset - 3),
        (size - offset - 3, size - offset - 8)
    ], fill=arrow_color)
    
    return btn

def create_repeat_button(size=40):
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    bbox = (center - 10, center - 14, center + 10, center + 14)
    draw.arc(bbox, 45, 315, fill=(255, 255, 255, 180), width=2)
    
    arrow_x, arrow_y = bbox[2], bbox[1] + 8
    draw.polygon([
        (arrow_x + 5, arrow_y - 5), (arrow_x - 5, arrow_y), (arrow_x + 5, arrow_y + 5)
    ], fill=(255, 255, 255, 180))
    
    dot_size = 3
    draw.ellipse(
        (center - dot_size, center - dot_size - 8, center + dot_size, center + dot_size - 8),
        fill=(255, 255, 255, 100)
    )
    
    return btn

# ================= PERFECTLY POSITIONED PROGRESS BAR =================
def create_spotify_progress_bar(width, height, progress=0.3, current_time="1:15", total_time="3:56"):
    """Progress bar with perfectly centered timer numbers"""
    bar_height = height
    total_bar_height = bar_height + 50
    bar_image = Image.new("RGBA", (width, total_bar_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar_image)
    
    bar_y = 10
    bar_radius = bar_height // 2
    
    # Track
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_height),
        radius=bar_radius, fill=(255, 255, 255, 18)
    )
    
    for i in range(2, 0, -1):
        alpha = int(25 * (i / 2))
        draw.rounded_rectangle(
            (0 - i, bar_y - i, width + i, bar_y + bar_height + i),
            radius=bar_radius + i, outline=(*NEON_PURPLE, alpha), width=1
        )
    
    fill_width = int(width * progress)
    if fill_width > 0:
        for i in range(5, 0, -1):
            alpha = int(18 * (i / 5))
            draw.rounded_rectangle(
                (0 - i, bar_y - i, fill_width + i, bar_y + bar_height + i),
                radius=bar_radius + i, fill=(*NEON_PURPLE, alpha)
            )
        
        for x in range(fill_width):
            ratio = x / max(fill_width, 1)
            color = blend_colors(NEON_PURPLE, NEON_PURPLE_LIGHT, ratio)
            draw.rectangle((x, bar_y, x + 1, bar_y + bar_height), fill=color)
        
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height // 2),
            radius=bar_radius, fill=(255, 255, 255, 30)
        )
        
        # Dot
        dot_radius = 8
        dot_x, dot_y = fill_width, bar_y + bar_height // 2
        
        for i in range(4, 0, -1):
            alpha = int(40 * (i / 4))
            draw.ellipse(
                (dot_x - dot_radius - i*2, dot_y - dot_radius - i*2,
                 dot_x + dot_radius + i*2, dot_y + dot_radius + i*2),
                fill=(*NEON_PURPLE, alpha)
            )
        
        draw.ellipse(
            (dot_x - dot_radius, dot_y - dot_radius,
             dot_x + dot_radius, dot_y + dot_radius), fill=WHITE
        )
        draw.ellipse(
            (dot_x - dot_radius + 3, dot_y - dot_radius + 3,
             dot_x + dot_radius - 3, dot_y + dot_radius - 3), fill=NEON_PURPLE
        )
        draw.ellipse(
            (dot_x - dot_radius//2, dot_y - dot_radius//2,
             dot_x + dot_radius//2, dot_y + dot_radius//2), fill=(255, 255, 255, 50)
        )
    
    # ===== TIMER FONT =====
    try:
        time_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 17)
    except:
        try:
            time_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 17)
        except:
            time_font = ImageFont.load_default()
    
    # ===== PERFECTLY POSITIONED TIMER NUMBERS =====
    timer_y = bar_y + bar_height + 12
    pill_pad_x, pill_pad_y, pill_radius = 12, 5, 8
    
    # --- LEFT PILL (Current Time) ---
    left_text = current_time
    left_bbox = draw.textbbox((0, 0), left_text, font=time_font)
    left_w = left_bbox[2] - left_bbox[0]
    left_h = left_bbox[3] - left_bbox[1]
    
    left_pill_w = left_w + pill_pad_x * 2
    left_pill_h = left_h + pill_pad_y * 2
    left_pill_x = 0
    left_pill_y = timer_y - pill_pad_y
    
    # Pill background
    draw.rounded_rectangle(
        (left_pill_x, left_pill_y, left_pill_x + left_pill_w, left_pill_y + left_pill_h),
        radius=pill_radius, fill=(147, 51, 234, 60), outline=(147, 51, 234, 120), width=1
    )
    
    # Text perfectly centered in pill
    left_text_center_x = left_pill_x + (left_pill_w - left_w) // 2
    left_text_center_y = left_pill_y + (left_pill_h - left_h) // 2
    draw.text((left_text_center_x, left_text_center_y - 1), left_text, fill=PURE_WHITE, font=time_font)
    
    # --- RIGHT PILL (Total Time) ---
    right_text = total_time
    right_bbox = draw.textbbox((0, 0), right_text, font=time_font)
    right_w = right_bbox[2] - right_bbox[0]
    right_h = right_bbox[3] - right_bbox[1]
    
    right_pill_w = right_w + pill_pad_x * 2
    right_pill_h = left_pill_h  # Same height as left
    right_pill_x = width - right_pill_w
    right_pill_y = left_pill_y  # Same y
    
    # Pill background
    draw.rounded_rectangle(
        (right_pill_x, right_pill_y, right_pill_x + right_pill_w, right_pill_y + right_pill_h),
        radius=pill_radius, fill=(147, 51, 234, 60), outline=(147, 51, 234, 120), width=1
    )
    
    # Text perfectly centered in pill
    right_text_center_x = right_pill_x + (right_pill_w - right_w) // 2
    right_text_center_y = right_pill_y + (right_pill_h - right_h) // 2
    draw.text((right_text_center_x, right_text_center_y - 1), right_text, fill=PURE_WHITE, font=time_font)
    
    # --- CENTER PROGRESS TEXT ---
    center_text = f"● {int(progress * 100)}%"
    center_bbox = draw.textbbox((0, 0), center_text, font=time_font)
    center_w = center_bbox[2] - center_bbox[0]
    center_h = center_bbox[3] - center_bbox[1]
    center_x = (width - center_w) // 2
    center_y = left_pill_y + (left_pill_h - center_h) // 2
    draw.text((center_x, center_y - 1), center_text, fill=(200, 150, 255, 220), font=time_font)
    
    return bar_image

def create_spotify_controls():
    panel_width, panel_height = 350, 120
    panel = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
    
    glass = Image.new("RGBA", (panel_width, panel_height), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glass)
    gdraw.rounded_rectangle((0, 0, panel_width, panel_height), radius=15, fill=(255, 255, 255, 8))
    gdraw.rounded_rectangle((0, 0, panel_width, panel_height), radius=15, outline=(255, 255, 255, 20), width=1)
    panel = Image.alpha_composite(panel, glass)
    
    cx, cy = panel_width // 2, panel_height // 2
    
    panel.alpha_composite(create_shuffle_button(36), (cx - 120, cy - 18))
    panel.alpha_composite(create_spotify_nav_button(40, "prev"), (cx - 70, cy - 20))
    panel.alpha_composite(create_spotify_play_button(64), (cx - 32, cy - 32))
    panel.alpha_composite(create_spotify_nav_button(40, "next"), (cx + 30, cy - 20))
    panel.alpha_composite(create_repeat_button(36), (cx + 85, cy - 18))
    
    return panel

def create_now_playing_badge(width, height=30):
    badge = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle(
        (0, 0, width, height), radius=height // 2,
        fill=(147, 51, 234, 30), outline=(147, 51, 234, 80), width=1
    )
    return badge

# ================= SPOILER GENERATOR =================
def create_spoiler_overlay(thumbnail_path, output_path=None):
    """
    Create blurred spoiler version of thumbnail.
    Telegram uses 'has_spoiler' parameter, but this generates a blurred
    preview image that can be sent as a separate spoiler image.
    """
    if output_path is None:
        output_path = thumbnail_path.replace('.png', '_spoiler.png')
    
    try:
        img = Image.open(thumbnail_path).convert("RGBA")
        
        # Apply strong gaussian blur for spoiler effect
        blurred = img.filter(ImageFilter.GaussianBlur(60))
        blurred = blurred.filter(ImageFilter.GaussianBlur(40))
        
        # Darken the blurred image for more mystery
        enhancer = ImageEnhance.Brightness(blurred)
        blurred = enhancer.enhance(0.5)
        
        # Add "SPOILER" text overlay
        draw = ImageDraw.Draw(blurred)
        
        # Load large font for spoiler text
        try:
            spoiler_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 80)
        except:
            try:
                spoiler_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 80)
            except:
                spoiler_font = ImageFont.load_default()
        
        try:
            tap_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 30)
        except:
            try:
                tap_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 30)
            except:
                tap_font = ImageFont.load_default()
        
        # Center the spoiler text
        spoiler_text = "🔮 SPOILER"
        spoiler_bbox = draw.textbbox((0, 0), spoiler_text, font=spoiler_font)
        spoiler_w = spoiler_bbox[2] - spoiler_bbox[0]
        spoiler_h = spoiler_bbox[3] - spoiler_bbox[1]
        spoiler_x = (CANVAS_SIZE[0] - spoiler_w) // 2
        spoiler_y = (CANVAS_SIZE[1] - spoiler_h) // 2 - 20
        
        # Shadow
        draw.text((spoiler_x + 3, spoiler_y + 3), spoiler_text, font=spoiler_font, fill=(0, 0, 0, 200))
        # Main text
        draw.text((spoiler_x, spoiler_y), spoiler_text, font=spoiler_font, fill=(255, 255, 255, 255))
        
        # "Tap to reveal" text
        tap_text = "👆 Tap to reveal"
        tap_bbox = draw.textbbox((0, 0), tap_text, font=tap_font)
        tap_w = tap_bbox[2] - tap_bbox[0]
        tap_x = (CANVAS_SIZE[0] - tap_w) // 2
        tap_y = spoiler_y + spoiler_h + 30
        
        draw.text((tap_x + 2, tap_y + 2), tap_text, font=tap_font, fill=(0, 0, 0, 180))
        draw.text((tap_x, tap_y), tap_text, font=tap_font, fill=(200, 180, 230, 255))
        
        # Save spoiler image
        final_spoiler = blurred.convert("RGB")
        final_spoiler.save(output_path, "PNG", quality=90)
        
        img.close()
        blurred.close()
        final_spoiler.close()
        
        return output_path
        
    except Exception as e:
        print(f"[Spoiler] Error creating spoiler: {e}")
        return thumbnail_path  # Return original if spoiler fails

# ================= MAIN FUNCTION =================

async def get_thumb(videoid, user_id=None):
    """Generate premium neon purple thumbnail + spoiler version"""
    
    ensure_cache_dir()
    
    cache_name = f"spotify_{videoid}_{user_id}.png" if user_id else f"spotify_{videoid}_thumb.png"
    cache_path = os.path.join(CACHE_DIR, cache_name)
    spoiler_path = cache_path.replace('.png', '_spoiler.png')
    
    # Return cached if both exist
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
        
        # Background
        bg = create_gradient_background(CANVAS_SIZE[0], CANVAS_SIZE[1], ROYAL_PURPLE, DARK_BG)
        canvas = Image.new("RGBA", CANVAS_SIZE)
        canvas.paste(bg, (0, 0))
        
        # Glows
        canvas = Image.alpha_composite(canvas, create_radial_glow(
            CANVAS_SIZE, NEON_PURPLE, (CANVAS_SIZE[0]//3, CANVAS_SIZE[1]//2), 0.08))
        canvas = Image.alpha_composite(canvas, create_radial_glow(
            CANVAS_SIZE, NEON_MAGENTA, (CANVAS_SIZE[0]*2//3, CANVAS_SIZE[1]//3), 0.06))
        canvas = Image.alpha_composite(canvas, create_radial_glow(
            CANVAS_SIZE, NEON_VIOLET, (CANVAS_SIZE[0]//2, CANVAS_SIZE[1]*3//4), 0.05))
        canvas = Image.alpha_composite(canvas, create_light_streaks(CANVAS_SIZE, NEON_PURPLE_LIGHT, 4))
        canvas = Image.alpha_composite(canvas, create_particle_field(CANVAS_SIZE, NEON_PURPLE_LIGHT, 70))
        
        # Cover art processing
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        cover = ImageEnhance.Contrast(cover).enhance(1.15)
        cover = ImageEnhance.Color(cover).enhance(1.1)
        cover = ImageEnhance.Sharpness(cover).enhance(1.2)
        cover = ImageEnhance.Brightness(cover).enhance(1.05)
        
        frame = create_cover_art_frame((COVER_SIZE, COVER_SIZE), 20)
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle((0, 0, COVER_SIZE, COVER_SIZE), radius=20, fill=255)
        cover.putalpha(cover_mask)
        
        frame_with_cover = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        frame_with_cover.paste(frame, (0, 0))
        frame_with_cover.paste(cover, (20, 20), cover)
        canvas.alpha_composite(frame_with_cover, (COVER_X - 20, COVER_Y - 20 - 5))
        
        # Load fonts
        font_paths = ["AnonXMusic/assets/font2.ttf", "AnonXMusic/assets/font.ttf"]
        title_font = artist_font = subtitle_font = small_font = None
        
        for fp in font_paths:
            try:
                if os.path.exists(fp):
                    title_font = ImageFont.truetype(fp, 46)
                    artist_font = ImageFont.truetype(fp, 26)
                    subtitle_font = ImageFont.truetype(fp, 18)
                    small_font = ImageFont.truetype(fp, 15)
                    break
            except:
                continue
        
        if title_font is None:
            title_font = artist_font = subtitle_font = small_font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(canvas)
        
        # ===== NOW PLAYING =====
        badge = create_now_playing_badge(210, 34)
        canvas.alpha_composite(badge, (RIGHT_START_X - 5, NOW_PLAYING_Y - 10))
        draw.text((RIGHT_START_X + 17, NOW_PLAYING_Y), "◆ NOW PLAYING",
                  font=subtitle_font, fill=(0, 0, 0, 180))
        draw.text((RIGHT_START_X + 15, NOW_PLAYING_Y - 3), "◆ NOW PLAYING",
                  font=subtitle_font, fill=PURE_WHITE)
        
        # ===== SONG TITLE =====
        title_text = trim_text(title, title_font, RIGHT_WIDTH)
        draw.text((RIGHT_START_X + 2, TITLE_Y + 2), title_text, font=title_font, fill=(0, 0, 0, 100))
        draw.text((RIGHT_START_X, TITLE_Y), title_text, font=title_font, fill=WHITE)
        
        title_bbox = draw.textbbox((RIGHT_START_X, TITLE_Y), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        accent_y = TITLE_Y + title_font.size + 8
        accent_width = min(title_width, 200)
        for i in range(3):
            draw.line([(RIGHT_START_X, accent_y + i), (RIGHT_START_X + accent_width, accent_y + i)],
                      fill=(*NEON_PURPLE, 150 - i * 50), width=2)
        
        # ===== ARTIST =====
        artist_text = trim_text(artist, artist_font, RIGHT_WIDTH - 40)
        draw.text((RIGHT_START_X, ARTIST_Y), artist_text, font=artist_font, fill=LIGHT_GRAY)
        
        try:
            artist_text_width = draw.textlength(artist_text, font=artist_font)
        except:
            artist_bbox = draw.textbbox((0, 0), artist_text, font=artist_font)
            artist_text_width = artist_bbox[2] - artist_bbox[0]
        
        badge_x, badge_y = RIGHT_START_X + int(artist_text_width) + 10, ARTIST_Y + 8
        draw.ellipse((badge_x, badge_y, badge_x + 20, badge_y + 20), fill=SPOTIFY_GREEN)
        draw.text((badge_x + 4, badge_y + 2), "✓", font=small_font, fill=WHITE)
        
        # ===== ALBUM INFO =====
        draw.text((RIGHT_START_X, ALBUM_INFO_Y),
                  f"Album • {views} • YouTube Music", font=subtitle_font, fill=DARK_GRAY)
        
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
        
        progress_bar = create_spotify_progress_bar(RIGHT_WIDTH, 6, progress_value, current_time, duration)
        canvas.alpha_composite(progress_bar, (RIGHT_START_X, PROGRESS_Y))
        
        # ===== CONTROLS =====
        try:
            controls = create_spotify_controls()
            controls_x = RIGHT_START_X + (RIGHT_WIDTH - 350) // 2
            canvas.alpha_composite(controls, (controls_x, CONTROLS_Y))
        except Exception as e:
            print(f"[Thumbnail] Controls error: {e}")
            draw.text((RIGHT_START_X + RIGHT_WIDTH // 4, CONTROLS_Y + 30),
                      "⏮  ▶  ⏭", font=title_font, fill=WHITE)
        
        # ===== VOLUME BAR =====
        volume_y = CONTROLS_Y + 130
        draw.text((RIGHT_START_X, volume_y), "🔊", font=small_font, fill=LIGHT_GRAY)
        
        volume_bar_x, volume_bar_y = RIGHT_START_X + 25, volume_y + 8
        draw.rounded_rectangle(
            (volume_bar_x, volume_bar_y, volume_bar_x + 120, volume_bar_y + 4),
            radius=2, fill=(255, 255, 255, 15))
        draw.rounded_rectangle(
            (volume_bar_x, volume_bar_y, volume_bar_x + 84, volume_bar_y + 4),
            radius=2, fill=NEON_PURPLE_LIGHT)
        
        # ===== BOTTOM LINE =====
        line_y = CANVAS_SIZE[1] - 55
        for i in range(3):
            draw.line([(30, line_y + i), (CANVAS_SIZE[0] - 30, line_y + i)],
                      fill=(*NEON_PURPLE, 60 - i * 20), width=1)
        
        # ===== SIGNATURE =====
        signature = "Made with ❤ by @DivineDemonn"
        draw.text((37, CANVAS_SIZE[1] - 38), signature, font=small_font, fill=(0, 0, 0, 200))
        draw.text((35, CANVAS_SIZE[1] - 40), signature, font=small_font, fill=PURE_WHITE)
        
        # ===== PREMIUM HD BADGE =====
        badge_text = "PREMIUM HD"
        badge_bbox = draw.textbbox((0, 0), badge_text, font=small_font)
        badge_w, badge_h = badge_bbox[2] - badge_bbox[0] + 20, 24
        badge_x, badge_y = CANVAS_SIZE[0] - badge_w - 30, CANVAS_SIZE[1] - 45
        
        draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
            radius=12, fill=(147, 51, 234, 60), outline=(147, 51, 234, 120), width=2)
        draw.text((badge_x + 11, badge_y + 5), badge_text, font=small_font, fill=(0, 0, 0, 150))
        draw.text((badge_x + 10, badge_y + 4), badge_text, font=small_font, fill=PURE_WHITE)
        
        # ===== SAVE THUMBNAIL =====
        final_canvas = canvas.convert("RGB")
        final_canvas.save(cache_path, "PNG", quality=100, optimize=True)
        
        # ===== GENERATE SPOILER VERSION =====
        create_spoiler_overlay(cache_path, spoiler_path)
        
        # Cleanup
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
                key=os.path.getmtime, reverse=True
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
        print(f"[Thumbnail] Error: {e}")
        traceback.print_exc()
        try:
            os.remove(thumb_file)
        except:
            pass
        return YOUTUBE_IMG_URL
