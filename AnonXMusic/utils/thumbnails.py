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

# ================= NEON PURPLE COLOR SCHEME =================
DARK_BG = (8, 4, 18)                    # Deep dark purple-black
NEON_PURPLE = (147, 51, 234)            # #9333EA - Vibrant purple
NEON_PURPLE_LIGHT = (168, 85, 247)      # #A855F7 - Light purple
NEON_PURPLE_PINK = (192, 38, 211)       # #C026D3 - Purple-pink
NEON_MAGENTA = (217, 70, 239)           # #D946EF - Magenta
NEON_VIOLET = (139, 92, 246)            # #8B5CF6 - Violet
WHITE = (255, 255, 255)
LIGHT_GRAY = (210, 210, 220)
DARK_GRAY = (100, 90, 110)
SOFT_PURPLE = (196, 167, 231)           # Soft purple accent
DEEP_PURPLE = (48, 12, 72)              # Very dark purple

# ================= LAYOUT POSITIONS =================
COVER_SIZE = 380
COVER_X = 70
COVER_Y = (CANVAS_SIZE[1] - COVER_SIZE) // 2

RIGHT_START_X = COVER_X + COVER_SIZE + 55
RIGHT_WIDTH = CANVAS_SIZE[0] - RIGHT_START_X - 70

# ================= TEXT POSITIONS =================
NOW_PLAYING_Y = 150
TITLE_Y = 210
ARTIST_Y = 275
PROGRESS_Y = 345
TIME_Y = 375
CONTROLS_Y = 430

# ================= HELPER FUNCTIONS =================

def ensure_cache_dir():
    """Ensure cache directory exists"""
    os.makedirs(CACHE_DIR, exist_ok=True)

def trim_text(text, font, max_width):
    """Trim text to fit within max_width with ellipsis"""
    if font.getlength(text) <= max_width:
        return text
    while font.getlength(text + "…") > max_width:
        text = text[:-1]
    return text + "…"

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def blend_colors(color1, color2, ratio=0.5):
    """Blend two colors"""
    return tuple(int(c1 * (1 - ratio) + c2 * ratio) for c1, c2 in zip(color1, color2))

# ================= VISUAL EFFECTS =================

def create_gradient_background(width, height, color1, color2):
    """Create smooth vertical gradient"""
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    for y in range(height):
        ratio = y / height
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        alpha = 255
        draw.line([(0, y), (width, y)], fill=(r, g, b, alpha))
    
    return gradient

def create_radial_glow(size, color, center=None, intensity=0.15):
    """Create radial glow from center"""
    if center is None:
        center = (size[0] // 2, size[1] // 2)
    
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    max_radius = int(math.sqrt(size[0]**2 + size[1]**2))
    
    for radius in range(max_radius, 0, -40):
        alpha = int(255 * intensity * (radius / max_radius))
        draw.ellipse(
            (center[0] - radius, center[1] - radius,
             center[0] + radius, center[1] + radius),
            outline=(*color, min(alpha, 15)),
            width=2
        )
    
    return glow.filter(ImageFilter.GaussianBlur(30))

def create_particle_field(size, color, count=150):
    """Create floating particles"""
    particles = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(particles)
    random.seed(42)
    
    for _ in range(count):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        radius = random.randint(1, 4)
        alpha = random.randint(15, 55)
        
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(*color, alpha)
        )
    
    return particles

def create_glow_border(image, border_size, color, blur_radius=15):
    """Create glowing border around image"""
    size = (image.size[0] + border_size * 2, image.size[1] + border_size * 2)
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    # Multiple glow layers
    for i in range(border_size, 0, -1):
        alpha = int(20 * (i / border_size))
        draw.rounded_rectangle(
            (i, i, size[0] - i, size[1] - i),
            radius=22 + i,
            outline=(*color, alpha),
            width=2
        )
    
    return glow.filter(ImageFilter.GaussianBlur(blur_radius))

def create_shadow(image_size, shadow_size, offset=(10, 10)):
    """Create drop shadow"""
    shadow = Image.new("RGBA", 
                       (image_size[0] + shadow_size, image_size[1] + shadow_size),
                       (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    
    draw.rounded_rectangle(
        (offset[0], offset[1], image_size[0] + offset[0], image_size[1] + offset[1]),
        radius=20,
        fill=(0, 0, 0, 120)
    )
    
    return shadow.filter(ImageFilter.GaussianBlur(25))

def create_neon_ring(size, color, ring_width=4):
    """Create neon ring effect"""
    ring = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ring)
    
    # Outer glow
    for i in range(15, 0, -2):
        alpha = int(10 * (i / 15))
        draw.rounded_rectangle(
            (i, i, size[0] - i, size[1] - i),
            radius=22 + i,
            outline=(*color, alpha),
            width=ring_width + i // 2
        )
    
    # Main ring
    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius=22,
        outline=(*color, 200),
        width=ring_width
    )
    
    # Inner highlight
    draw.rounded_rectangle(
        (2, 2, size[0] - 2, size[1] - 2),
        radius=20,
        outline=(255, 255, 255, 60),
        width=1
    )
    
    return ring

def create_progress_bar(x, y, width, height, progress, color):
    """Create modern progress bar"""
    bar = Image.new("RGBA", (width, height + 30), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar)
    
    # Background track
    draw.rounded_rectangle(
        (0, 15, width, height + 15),
        radius=height // 2,
        fill=(255, 255, 255, 15)
    )
    
    # Progress fill
    fill_width = int(width * progress)
    
    # Glow behind progress
    for i in range(8, 0, -1):
        alpha = int(15 * (i / 8))
        draw.rounded_rectangle(
            (0 - i, 15 - i, fill_width + i, height + 15 + i),
            radius=(height + i * 2) // 2,
            fill=(*color, alpha)
        )
    
    # Main progress fill
    if fill_width > 0:
        draw.rounded_rectangle(
            (0, 15, fill_width, height + 15),
            radius=height // 2,
            fill=color
        )
        
        # Highlight on progress
        draw.rounded_rectangle(
            (0, 15, fill_width, height // 2 + 15),
            radius=height // 2,
            fill=(255, 255, 255, 40)
        )
    
    # Thumb dot
    thumb_x = fill_width
    thumb_y = height // 2 + 15
    
    # Thumb glow
    for i in range(6, 0, -1):
        alpha = int(40 * (i / 6))
        draw.ellipse(
            (thumb_x - 8 - i * 2, thumb_y - 8 - i * 2,
             thumb_x + 8 + i * 2, thumb_y + 8 + i * 2),
            fill=(*color, alpha)
        )
    
    # Thumb main
    draw.ellipse(
        (thumb_x - 8, thumb_y - 8, thumb_x + 8, thumb_y + 8),
        fill=WHITE
    )
    draw.ellipse(
        (thumb_x - 4, thumb_y - 4, thumb_x + 4, thumb_y + 4),
        fill=color
    )
    
    return bar

def create_control_button(symbol, size, active=True):
    """Create neon control button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    if symbol == "play":
        # Play button with circle
        radius = size // 3
        
        # Outer glow rings
        for i in range(5, 0, -1):
            alpha = int(30 * (i / 5))
            draw.ellipse(
                (center - radius - i * 3, center - radius - i * 3,
                 center + radius + i * 3, center + radius + i * 3),
                fill=(*NEON_PURPLE, alpha)
            )
        
        # Main circle
        draw.ellipse(
            (center - radius, center - radius,
             center + radius, center + radius),
            fill=NEON_PURPLE
        )
        
        # Play triangle
        triangle_size = int(radius * 0.8)
        points = [
            (center - triangle_size // 3, center - triangle_size // 2),
            (center - triangle_size // 3, center + triangle_size // 2),
            (center + triangle_size * 2 // 3, center)
        ]
        draw.polygon(points, fill=WHITE)
        
    elif symbol == "pause":
        bar_width = size // 6
        bar_height = size // 2
        
        draw.rectangle(
            (center - bar_width - 4, center - bar_height // 2,
             center - 4, center + bar_height // 2),
            fill=WHITE if active else DARK_GRAY,
            outline=None
        )
        draw.rectangle(
            (center + 4, center - bar_height // 2,
             center + bar_width + 4, center + bar_height // 2),
            fill=WHITE if active else DARK_GRAY,
            outline=None
        )
    
    return btn

# ================= MAIN FUNCTION =================

async def get_thumb(videoid, user_id=None):
    """
    Generate premium neon purple thumbnail for music bot.
    
    Args:
        videoid: YouTube video ID
        user_id: Optional user ID for caching
        
    Returns:
        Path to generated thumbnail image
    """
    # Ensure cache directory exists
    ensure_cache_dir()
    
    # Generate cache filename
    cache_name = f"{videoid}_{user_id}.png" if user_id else f"{videoid}_thumb.png"
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
    
    # ========== CREATE CANVAS ==========
    try:
        # Load cover art
        cover_img = Image.open(thumb_file).convert("RGBA")
        
        # Create gradient background
        bg = create_gradient_background(
            CANVAS_SIZE[0], CANVAS_SIZE[1],
            DEEP_PURPLE, DARK_BG
        )
        
        # Create canvas
        canvas = Image.new("RGBA", CANVAS_SIZE)
        canvas.paste(bg, (0, 0))
        
        # ===== ADD BACKGROUND EFFECTS =====
        
        # Radial glow from center
        radial_glow = create_radial_glow(
            CANVAS_SIZE, NEON_PURPLE,
            center=(CANVAS_SIZE[0] // 2 + 100, CANVAS_SIZE[1] // 2),
            intensity=0.12
        )
        canvas = Image.alpha_composite(canvas, radial_glow)
        
        # Particle field
        particles = create_particle_field(CANVAS_SIZE, NEON_PURPLE_LIGHT)
        canvas = Image.alpha_composite(canvas, particles)
        
        # ===== PROCESS COVER ART =====
        
        # Resize cover
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        
        # Enhance cover
        cover = ImageEnhance.Contrast(cover).enhance(1.2)
        cover = ImageEnhance.Color(cover).enhance(1.15)
        cover = ImageEnhance.Sharpness(cover).enhance(1.3)
        
        # Create shadow
        shadow = create_shadow(
            (COVER_SIZE, COVER_SIZE), 40, (15, 15)
        )
        canvas.alpha_composite(
            shadow,
            (COVER_X - 20, COVER_Y - 20)
        )
        
        # Create glow border
        glow_border = create_glow_border(cover, 20, NEON_PURPLE)
        canvas.alpha_composite(
            glow_border,
            (COVER_X - 20, COVER_Y - 20)
        )
        
        # Apply rounded corners to cover
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle(
            (0, 0, COVER_SIZE, COVER_SIZE),
            radius=20,
            fill=255
        )
        cover.putalpha(cover_mask)
        
        # Place cover
        canvas.alpha_composite(cover, (COVER_X, COVER_Y))
        
        # Create neon ring around cover
        neon_ring = create_neon_ring(
            (COVER_SIZE + 16, COVER_SIZE + 16),
            NEON_PURPLE_LIGHT,
            ring_width=3
        )
        canvas.alpha_composite(neon_ring, (COVER_X - 8, COVER_Y - 8))
        
        # ===== LOAD FONTS =====
        font_paths = [
            "AnonXMusic/assets/font2.ttf",
            "AnonXMusic/assets/font.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        
        now_playing_font = None
        title_font = None
        artist_font = None
        small_font = None
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    if now_playing_font is None:
                        now_playing_font = ImageFont.truetype(font_path, 18)
                    if title_font is None:
                        title_font = ImageFont.truetype(font_path, 48)
                    if artist_font is None:
                        artist_font = ImageFont.truetype(font_path, 28)
                    if small_font is None:
                        small_font = ImageFont.truetype(font_path, 16)
            except:
                continue
        
        # Fallback to default
        if title_font is None:
            title_font = ImageFont.load_default()
        if artist_font is None:
            artist_font = ImageFont.load_default()
        if now_playing_font is None:
            now_playing_font = ImageFont.load_default()
        if small_font is None:
            small_font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(canvas)
        
        # ===== "NOW PLAYING" LABEL =====
        now_playing_text = "◆ NOW PLAYING"
        now_playing_bbox = draw.textbbox((0, 0), now_playing_text, font=now_playing_font)
        
        # Glow effect for label
        for offset in range(3, 0, -1):
            glow_alpha = 50 - offset * 10
            draw.text(
                (RIGHT_START_X - offset, NOW_PLAYING_Y - offset),
                now_playing_text,
                font=now_playing_font,
                fill=(*NEON_PURPLE, glow_alpha)
            )
        
        draw.text(
            (RIGHT_START_X, NOW_PLAYING_Y),
            now_playing_text,
            font=now_playing_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SONG TITLE =====
        title_text = trim_text(title, title_font, RIGHT_WIDTH)
        
        # Title glow
        for offset in range(4, 0, -1):
            glow_alpha = 40 - offset * 8
            draw.text(
                (RIGHT_START_X - offset, TITLE_Y - offset),
                title_text,
                font=title_font,
                fill=(*NEON_PURPLE, glow_alpha)
            )
        
        draw.text(
            (RIGHT_START_X, TITLE_Y),
            title_text,
            font=title_font,
            fill=WHITE
        )
        
        # ===== ARTIST NAME =====
        artist_text = trim_text(artist, artist_font, RIGHT_WIDTH - 20)
        
        draw.text(
            (RIGHT_START_X, ARTIST_Y),
            f"🎤 {artist_text}",
            font=artist_font,
            fill=LIGHT_GRAY
        )
        
        # ===== PROGRESS BAR =====
        progress_bar = create_progress_bar(
            RIGHT_START_X, PROGRESS_Y,
            RIGHT_WIDTH, 6,
            0.55,  # Dummy progress
            NEON_PURPLE
        )
        canvas.alpha_composite(progress_bar, (0, 0))
        
        # ===== TIME LABELS =====
        draw.text(
            (RIGHT_START_X, TIME_Y),
            "0:00",
            font=small_font,
            fill=(255, 255, 255, 180)
        )
        
        duration_text = str(duration) if duration else "0:00"
        dur_bbox = draw.textbbox((0, 0), duration_text, font=small_font)
        dur_width = dur_bbox[2] - dur_bbox[0]
        
        draw.text(
            (RIGHT_START_X + RIGHT_WIDTH - dur_width, TIME_Y),
            duration_text,
            font=small_font,
            fill=(255, 255, 255, 180)
        )
        
        # ===== CONTROL BUTTONS =====
        controls_center_x = RIGHT_START_X + RIGHT_WIDTH // 2
        controls_y = CONTROLS_Y
        
        # Play button
        play_btn = create_control_button("play", 80)
        canvas.alpha_composite(
            play_btn,
            (controls_center_x - 40, controls_y)
        )
        
        # ===== BOT NAME LABEL =====
        bot_name = getattr(app, 'name', 'RaspberryRhythm')
        
        name_bbox = draw.textbbox((0, 0), bot_name, font=small_font)
        
        draw.text(
            (RIGHT_START_X, controls_y + 100),
            f"⚡ {bot_name}",
            font=small_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SIGNATURE =====
        signature = "Made with 💜 by @DivineDemonn"
        draw.text(
            (30, CANVAS_SIZE[1] - 35),
            signature,
            font=small_font,
            fill=(*NEON_PURPLE, 150)
        )
        
        # ===== VERSION LABEL =====
        draw.text(
            (CANVAS_SIZE[0] - 100, CANVAS_SIZE[1] - 35),
            "v2.0",
            font=small_font,
            fill=(*NEON_PURPLE, 120)
        )
        
        # ===== SAVE THUMBNAIL =====
        # Convert to RGB for saving
        final_canvas = canvas.convert("RGB")
        
        # Save with high quality
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
        cache_files = sorted(
            [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f.endswith('.png')],
            key=os.path.getmtime,
            reverse=True
        )
        
        # Keep only last 20 thumbnails
        for old_file in cache_files[20:]:
            try:
                os.remove(old_file)
            except:
                pass
        
        return cache_path
        
    except Exception as e:
        print(f"[Thumbnail] Error generating thumbnail: {e}")
        traceback.print_exc()
        
        # Cleanup on error
        try:
            os.remove(thumb_file)
        except:
            pass
        
        return YOUTUBE_IMG_URL
