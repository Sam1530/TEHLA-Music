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
DARK_BG = (8, 3, 22)                      # Ultra deep purple-black
NEON_PURPLE = (147, 51, 234)              # #9333EA - Vibrant purple
NEON_PURPLE_LIGHT = (175, 95, 250)        # Brighter light purple for readability
NEON_MAGENTA = (220, 80, 245)             # #D946EF - Magenta
NEON_VIOLET = (145, 100, 250)             # #8B5CF6 - Violet
ACCENT_PURPLE = (190, 110, 205)           # Soft accent
DEEP_PURPLE = (50, 15, 75)                # Very dark purple
PURE_WHITE = (255, 255, 255)              # Pure white for text clarity
SOFT_WHITE = (240, 238, 245)              # Slightly warm white
LIGHT_GRAY = (220, 215, 230)              # Light gray for secondary text
MEDIUM_GRAY = (160, 150, 170)             # Medium gray for metadata
DARK_GRAY = (90, 80, 100)                 # Dark gray for less important text

# ================= SPOTIFY-STYLE COLORS =================
SPOTIFY_GREEN = (30, 215, 96)             # Spotify green accent
PLAY_GREEN = (40, 220, 100)               # Bright play button green

# ================= LAYOUT POSITIONS (Refined for better spacing) =================
COVER_SIZE = 400
COVER_X = 70
COVER_Y = (CANVAS_SIZE[1] - COVER_SIZE) // 2

RIGHT_START_X = COVER_X + COVER_SIZE + 80
RIGHT_WIDTH = CANVAS_SIZE[0] - RIGHT_START_X - 70

# ================= TEXT POSITIONS (Adjusted for clarity) =================
NOW_PLAYING_Y = 135
TITLE_Y = 200
ARTIST_Y = TITLE_Y + 90
ALBUM_INFO_Y = ARTIST_Y + 55
PROGRESS_Y = ALBUM_INFO_Y + 80
TIME_Y = PROGRESS_Y + 55
CONTROLS_Y = TIME_Y + 70

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

def blend_colors(color1, color2, ratio=0.5):
    """Blend two colors"""
    return tuple(
        max(0, min(255, int(c1 * (1 - ratio) + c2 * ratio)))
        for c1, c2 in zip(color1, color2)
    )

def draw_text_with_shadow(draw, text, position, font, fill_color, shadow_color=(0,0,0,100), shadow_offset=2):
    """Draw sharp text with shadow for better readability"""
    x, y = position
    
    # Draw shadow
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    # Draw main text
    draw.text((x, y), text, font=font, fill=fill_color)

# ================= VISUAL EFFECTS =================

def create_gradient_background(width, height, color1, color2):
    """Create smooth vertical gradient with enhanced depth"""
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    for i in range(height):
        ratio = i / height
        # Enhanced curve for more dynamic gradient
        curve_ratio = math.pow(math.sin(ratio * math.pi * 0.5), 1.5)
        r = int(color1[0] * (1 - curve_ratio) + color2[0] * curve_ratio)
        g = int(color1[1] * (1 - curve_ratio) + color2[1] * curve_ratio)
        b = int(color1[2] * (1 - curve_ratio) + color2[2] * curve_ratio)
        draw.line([(0, i), (width, i)], fill=(r, g, b, 255))
    
    return gradient

def create_radial_glow(size, color, center=None, intensity=0.1):
    """Create elegant radial glow"""
    if center is None:
        center = (size[0] // 2, size[1] // 2)
    
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    max_radius = int(math.sqrt(size[0]**2 + size[1]**2)) // 2
    
    for radius in range(max_radius, 0, -100):
        alpha = min(10, int(255 * intensity * (radius / max_radius) * 0.3))
        draw.ellipse(
            (center[0] - radius, center[1] - radius,
             center[0] + radius, center[1] + radius),
            outline=(*color, alpha),
            width=4
        )
    
    return glow.filter(ImageFilter.GaussianBlur(50))

def create_particle_field(size, color, count=80):
    """Create subtle floating particles"""
    particles = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(particles)
    random.seed(42)
    
    for _ in range(count):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        radius = random.randint(1, 2)
        alpha = random.randint(15, 45)
        
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(*color, alpha)
        )
    
    return particles

def create_cover_frame(size, border_width=12):
    """Create premium cover art frame with neon glow"""
    total_width = size[0] + border_width * 2
    total_height = size[1] + border_width * 2
    frame = Image.new("RGBA", (total_width + 20, total_height + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    
    # Deep shadow
    for i in range(15, 0, -1):
        alpha = int(25 * (i / 15))
        draw.rounded_rectangle(
            (10 + i, 15 + i, total_width + 10 - i, total_height + 15 - i),
            radius=22,
            fill=(0, 0, 0, alpha)
        )
    
    # Neon glow
    for i in range(6, 0, -1):
        alpha = int(50 * (i / 6))
        draw.rounded_rectangle(
            (10 - i, 10 - i, total_width + 10 + i, total_height + 10 + i),
            radius=22 + i,
            outline=(*NEON_PURPLE, alpha),
            width=3
        )
    
    # Inner white highlight
    draw.rounded_rectangle(
        (10 + 2, 10 + 2, total_width + 10 - 2, total_height + 10 - 2),
        radius=20,
        outline=(255, 255, 255, 40),
        width=1
    )
    
    return frame.filter(ImageFilter.GaussianBlur(3))

# ================= ENHANCED BUTTONS =================

def create_play_button(size=80):
    """Create premium play button with gradient"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    radius = size // 2 - 2
    
    # Outer glow
    for i in range(10, 0, -2):
        alpha = int(20 * (i / 10))
        draw.ellipse(
            (center - radius - i, center - radius - i,
             center + radius + i, center + radius + i),
            fill=(*SPOTIFY_GREEN, alpha)
        )
    
    # Main circle
    draw.ellipse(
        (center - radius + 2, center - radius + 2,
         center + radius - 2, center + radius - 2),
        fill=SPOTIFY_GREEN
    )
    
    # Highlight
    highlight_radius = radius - 10
    draw.ellipse(
        (center - highlight_radius, center - highlight_radius - 5,
         center + highlight_radius, center + highlight_radius - 5),
        fill=(255, 255, 255, 30)
    )
    
    # Play triangle (larger and centered)
    tri_size = radius // 2
    offset_x = 3
    points = [
        (center - tri_size // 2 + offset_x, center - tri_size),
        (center - tri_size // 2 + offset_x, center + tri_size),
        (center + tri_size + offset_x, center)
    ]
    draw.polygon(points, fill=PURE_WHITE)
    
    return btn

def create_nav_button(size=48, icon_type="prev"):
    """Create clean navigation button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    
    # Circular glass background
    draw.ellipse(
        (4, 4, size - 4, size - 4),
        fill=(255, 255, 255, 15),
        outline=(255, 255, 255, 30),
        width=2
    )
    
    if icon_type == "prev":
        # Previous icon (⏮)
        bar_x = size // 3
        tri_w = size // 5
        tri_h = size // 4
        center = size // 2
        
        # Vertical bar
        draw.rectangle(
            (bar_x - 1, center - tri_h, bar_x + 1, center + tri_h),
            fill=(255, 255, 255, 230)
        )
        
        # Triangle
        points = [
            (bar_x + 6, center - tri_h),
            (bar_x + 6, center + tri_h),
            (bar_x + 6 - tri_w, center)
        ]
        draw.polygon(points, fill=(255, 255, 255, 230))
    
    elif icon_type == "next":
        # Next icon (⏭)
        bar_x = size - size // 3
        tri_w = size // 5
        tri_h = size // 4
        center = size // 2
        
        # Vertical bar
        draw.rectangle(
            (bar_x - 1, center - tri_h, bar_x + 1, center + tri_h),
            fill=(255, 255, 255, 230)
        )
        
        # Triangle
        points = [
            (bar_x - 6, center - tri_h),
            (bar_x - 6, center + tri_h),
            (bar_x - 6 + tri_w, center)
        ]
        draw.polygon(points, fill=(255, 255, 255, 230))
    
    return btn

def create_progress_bar(width, height, progress=0.3, current_time="0:00", total_time="3:45"):
    """Create modern progress bar"""
    bar = Image.new("RGBA", (width, height + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)
    
    bar_y = 15
    bar_height = height
    bar_radius = height // 2
    
    # Track background
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_height),
        radius=bar_radius,
        fill=(255, 255, 255, 20)
    )
    
    # Progress fill
    fill_width = int(width * progress)
    if fill_width > 0:
        # Progress glow
        for i in range(3, 0, -1):
            alpha = int(15 * (i / 3))
            draw.rounded_rectangle(
                (0 - i, bar_y - i, fill_width + i, bar_y + bar_height + i),
                radius=bar_radius + i,
                fill=(*SPOTIFY_GREEN, alpha)
            )
        
        # Main fill
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height),
            radius=bar_radius,
            fill=SPOTIFY_GREEN
        )
        
        # Dot
        dot_r = 8
        dot_x = fill_width
        dot_y = bar_y + bar_height // 2
        
        # Dot glow
        draw.ellipse(
            (dot_x - dot_r - 3, dot_y - dot_r - 3,
             dot_x + dot_r + 3, dot_y + dot_r + 3),
            fill=(*SPOTIFY_GREEN, 40)
        )
        
        # Dot
        draw.ellipse(
            (dot_x - dot_r, dot_y - dot_r,
             dot_x + dot_r, dot_y + dot_r),
            fill=PURE_WHITE,
            outline=SPOTIFY_GREEN,
            width=2
        )
    
    # Time labels
    try:
        time_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 16)
    except:
        try:
            time_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 16)
        except:
            time_font = ImageFont.load_default()
    
    draw.text((0, bar_y + bar_height + 10), current_time, fill=PURE_WHITE, font=time_font)
    
    # Right align total time
    bbox = draw.textbbox((0, 0), total_time, font=time_font)
    text_w = bbox[2] - bbox[0]
    draw.text((width - text_w, bar_y + bar_height + 10), total_time, fill=PURE_WHITE, font=time_font)
    
    return bar

def create_controls_panel():
    """Create complete controls panel"""
    panel_w = 320
    panel_h = 100
    panel = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    
    # Previous button
    prev = create_nav_button(44, "prev")
    panel.alpha_composite(prev, (20, (panel_h - 44) // 2))
    
    # Play button (larger, centered)
    play = create_play_button(70)
    play_x = (panel_w - 70) // 2
    play_y = (panel_h - 70) // 2
    panel.alpha_composite(play, (play_x, play_y))
    
    # Next button
    next_btn = create_nav_button(44, "next")
    panel.alpha_composite(next_btn, (panel_w - 20 - 44, (panel_h - 44) // 2))
    
    return panel

# ================= MAIN FUNCTION =================

async def get_thumb(videoid, user_id=None):
    """Generate premium music thumbnail with crystal clear text"""
    
    ensure_cache_dir()
    
    # Cache check
    cache_name = f"premium_{videoid}_{user_id}.png" if user_id else f"premium_{videoid}_thumb.png"
    cache_path = os.path.join(CACHE_DIR, cache_name)
    
    if os.path.exists(cache_path):
        return cache_path
    
    # ===== FETCH DATA =====
    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        vs = VideosSearch(url, limit=1)
        results = await vs.next()
        data = results["result"][0]
        
        # Clean data
        title = re.sub(r"[^\w\s\-&()]", "", data.get("title", "Unknown Title")).strip()
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
        print(f"[Thumbnail] Data error: {e}")
        return YOUTUBE_IMG_URL
    
    # ===== DOWNLOAD COVER =====
    thumb_file = os.path.join(CACHE_DIR, f"{videoid}_raw.jpg")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url, timeout=10) as resp:
                if resp.status != 200:
                    return YOUTUBE_IMG_URL
                async with aiofiles.open(thumb_file, "wb") as f:
                    await f.write(await resp.read())
    except:
        return YOUTUBE_IMG_URL
    
    # ===== BUILD THUMBNAIL =====
    try:
        # Load cover
        cover_img = Image.open(thumb_file).convert("RGBA")
        
        # Background
        bg = create_gradient_background(CANVAS_SIZE[0], CANVAS_SIZE[1], DEEP_PURPLE, DARK_BG)
        canvas = Image.new("RGBA", CANVAS_SIZE)
        canvas.paste(bg, (0, 0))
        
        # Glow effects
        glow1 = create_radial_glow(CANVAS_SIZE, NEON_PURPLE, 
                                   (CANVAS_SIZE[0]//3, CANVAS_SIZE[1]//2), 0.08)
        canvas = Image.alpha_composite(canvas, glow1)
        
        glow2 = create_radial_glow(CANVAS_SIZE, NEON_MAGENTA,
                                   (CANVAS_SIZE[0]*2//3, CANVAS_SIZE[1]//3), 0.05)
        canvas = Image.alpha_composite(canvas, glow2)
        
        # Particles
        particles = create_particle_field(CANVAS_SIZE, NEON_PURPLE_LIGHT, 60)
        canvas = Image.alpha_composite(canvas, particles)
        
        # ===== COVER ART =====
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        
        # Enhance cover
        cover = ImageEnhance.Contrast(cover).enhance(1.2)
        cover = ImageEnhance.Color(cover).enhance(1.15)
        cover = ImageEnhance.Sharpness(cover).enhance(1.25)
        cover = ImageEnhance.Brightness(cover).enhance(1.08)
        
        # Frame
        frame = create_cover_frame((COVER_SIZE, COVER_SIZE), 12)
        frame_w, frame_h = frame.size
        
        # Round corners on cover
        mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, COVER_SIZE, COVER_SIZE), radius=22, fill=255)
        cover.putalpha(mask)
        
        # Composite
        frame_with_cover = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        frame_with_cover.paste(frame, (0, 0))
        frame_with_cover.paste(cover, (16, 16), cover)
        
        canvas.alpha_composite(frame_with_cover, (COVER_X - 16, COVER_Y - 16))
        
        # ===== LOAD FONTS (Larger sizes for clarity) =====
        title_font = None
        artist_font = None
        subtitle_font = None
        small_font = None
        
        font_paths = [
            "AnonXMusic/assets/font2.ttf",
            "AnonXMusic/assets/font.ttf",
        ]
        
        for fp in font_paths:
            try:
                if os.path.exists(fp):
                    title_font = ImageFont.truetype(fp, 52)      # Bigger for clarity
                    artist_font = ImageFont.truetype(fp, 30)
                    subtitle_font = ImageFont.truetype(fp, 20)
                    small_font = ImageFont.truetype(fp, 17)
                    break
            except:
                continue
        
        # Fallback fonts
        if title_font is None:
            title_font = ImageFont.load_default()
            artist_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(canvas)
        
        # ===== NOW PLAYING BADGE =====
        badge_w = 200
        badge_h = 36
        badge_x = RIGHT_START_X
        badge_y = NOW_PLAYING_Y - 15
        
        draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
            radius=18,
            fill=(147, 51, 234, 30),
            outline=(147, 51, 234, 80),
            width=1
        )
        
        draw.text(
            (badge_x + 18, badge_y + 8),
            "◆ NOW PLAYING",
            font=subtitle_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== TITLE (Crystal clear) =====
        title_text = trim_text(title, title_font, RIGHT_WIDTH)
        title_y = TITLE_Y
        
        # Strong shadow for depth
        draw_text_with_shadow(draw, title_text, (RIGHT_START_X, title_y),
                              title_font, PURE_WHITE, (0, 0, 0, 120), 3)
        
        # ===== ARTIST =====
        artist_text = trim_text(artist, artist_font, RIGHT_WIDTH - 40)
        artist_y = ARTIST_Y
        
        draw_text_with_shadow(draw, artist_text, (RIGHT_START_X, artist_y),
                              artist_font, LIGHT_GRAY, (0, 0, 0, 80), 2)
        
        # ===== METADATA =====
        meta_y = ALBUM_INFO_Y
        meta_text = f"🎵 YouTube Music • {views}"
        draw.text((RIGHT_START_X, meta_y), meta_text, font=subtitle_font, fill=MEDIUM_GRAY)
        
        # ===== PROGRESS BAR =====
        # Calculate progress
        current_time = "0:00"
        progress_val = 0.3
        
        try:
            if ":" in duration:
                parts = duration.split(":")
                total_secs = int(parts[0]) * 60 + int(parts[1])
                progress_val = min(0.35, 30 / max(total_secs, 30))
                elapsed = int(total_secs * progress_val)
                current_time = f"{elapsed//60}:{elapsed%60:02d}"
        except:
            pass
        
        progress = create_progress_bar(RIGHT_WIDTH, 8, progress_val, current_time, duration)
        canvas.alpha_composite(progress, (RIGHT_START_X, PROGRESS_Y))
        
        # ===== CONTROLS =====
        controls = create_controls_panel()
        controls_x = RIGHT_START_X + (RIGHT_WIDTH - 320) // 2
        controls_y = CONTROLS_Y - 20
        canvas.alpha_composite(controls, (controls_x, controls_y))
        
        # ===== QUEUE INFO (Properly updated) =====
        queue_y = CANVAS_SIZE[1] - 110
        queue_bg_w = RIGHT_WIDTH
        queue_bg_h = 55
        
        # Queue background panel
        draw.rounded_rectangle(
            (RIGHT_START_X, queue_y, RIGHT_START_X + queue_bg_w, queue_y + queue_bg_h),
            radius=12,
            fill=(255, 255, 255, 6),
            outline=(255, 255, 255, 12),
            width=1
        )
        
        # Queue header
        draw.text(
            (RIGHT_START_X + 15, queue_y + 8),
            "📋 QUEUE",
            font=small_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # Next track info (actual dynamic data)
        next_song = f"Next: {title[:35]}{'...' if len(title) > 35 else ''}"
        draw.text(
            (RIGHT_START_X + 15, queue_y + 30),
            next_song,
            font=small_font,
            fill=PURE_WHITE
        )
        
        # Queue count indicator
        queue_count = "▶ 1 of 15"
        bbox = draw.textbbox((0, 0), queue_count, font=small_font)
        qw = bbox[2] - bbox[0]
        draw.text(
            (RIGHT_START_X + queue_bg_w - qw - 15, queue_y + 30),
            queue_count,
            font=small_font,
            fill=MEDIUM_GRAY
        )
        
        # ===== BOTTOM DIVIDER =====
        div_y = CANVAS_SIZE[1] - 50
        for i in range(2):
            alpha = 80 - i * 40
            draw.line(
                [(35, div_y + i), (CANVAS_SIZE[0] - 35, div_y + i)],
                fill=(*NEON_PURPLE, alpha),
                width=1
            )
        
        # ===== SIGNATURE (Clean, visible) =====
        sig_text = "Crafted with ❤️ by @DivineDemonn"
        draw.text((35, CANVAS_SIZE[1] - 38), sig_text, font=small_font, fill=SOFT_WHITE)
        
        # ===== HD BADGE =====
        badge_text = "✦ HD PREMIUM ✦"
        bbox = draw.textbbox((0, 0), badge_text, font=small_font)
        bw = bbox[2] - bbox[0] + 24
        bh = 28
        
        bx = CANVAS_SIZE[0] - bw - 30
        by = CANVAS_SIZE[1] - 42
        
        draw.rounded_rectangle(
            (bx, by, bx + bw, by + bh),
            radius=14,
            fill=(147, 51, 234, 35),
            outline=(147, 51, 234, 70),
            width=1
        )
        
        draw.text((bx + 12, by + 6), badge_text, font=small_font, fill=NEON_PURPLE_LIGHT)
        
        # ===== SAVE =====
        final = canvas.convert("RGB")
        final.save(cache_path, "PNG", quality=100, optimize=True)
        
        # Cleanup
        cover_img.close()
        canvas.close()
        final.close()
        bg.close()
        
        try:
            os.remove(thumb_file)
        except:
            pass
        
        # Cache cleanup
        try:
            files = sorted(
                [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f.endswith('.png')],
                key=os.path.getmtime, reverse=True
            )
            for old in files[12:]:
                try:
                    os.remove(old)
                except:
                    pass
        except:
            pass
        
        return cache_path
        
    except Exception as e:
        print(f"[Thumbnail] Generation error: {e}")
        traceback.print_exc()
        
        try:
            os.remove(thumb_file)
        except:
            pass
        
        return YOUTUBE_IMG_URL
