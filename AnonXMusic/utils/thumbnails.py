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

# ================= TEXT & CONTROLS POSITIONS =================
NOW_PLAYING_Y = 130
TITLE_Y = 195
ARTIST_Y = TITLE_Y + 65
PROGRESS_Y = ARTIST_Y + 80
TIME_Y = PROGRESS_Y + 45
CONTROLS_Y = TIME_Y + 55

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
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
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
    
    for i in range(15, 0, -2):
        alpha = int(10 * (i / 15))
        draw.rounded_rectangle(
            (i, i, size[0] - i, size[1] - i),
            radius=22 + i,
            outline=(*color, alpha),
            width=ring_width + i // 2
        )
    
    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius=22,
        outline=(*color, 200),
        width=ring_width
    )
    
    draw.rounded_rectangle(
        (2, 2, size[0] - 2, size[1] - 2),
        radius=20,
        outline=(255, 255, 255, 60),
        width=1
    )
    
    return ring

def create_progress_bar_section(width, height, progress, color):
    """Create modern progress bar section properly positioned"""
    bar_section = Image.new("RGBA", (width, height + 50), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar_section)
    
    bar_height = height
    bar_y = 10
    
    # Background track
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_height),
        radius=bar_height // 2,
        fill=(255, 255, 255, 12)
    )
    
    # Track border glow
    for i in range(4, 0, -1):
        alpha = int(10 + i * 5)
        draw.rounded_rectangle(
            (0 - i, bar_y - i, width + i, bar_y + bar_height + i),
            radius=(bar_height + i) // 2,
            outline=(*color, alpha),
            width=1
        )
    
    # Progress fill
    fill_width = int(width * progress)
    
    if fill_width > 0:
        # Glow behind progress
        for i in range(6, 0, -1):
            alpha = int(12 * (i / 6))
            draw.rounded_rectangle(
                (0 - i, bar_y - i, fill_width + i, bar_y + bar_height + i),
                radius=(bar_height + i) // 2,
                fill=(*color, alpha)
            )
        
        # Main progress
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height),
            radius=bar_height // 2,
            fill=color
        )
        
        # Highlight
        draw.rounded_rectangle(
            (0, bar_y, fill_width, bar_y + bar_height // 2),
            radius=bar_height // 2,
            fill=(255, 255, 255, 35)
        )
    
    # Thumb dot
    thumb_x = max(8, fill_width)
    thumb_y = bar_y + bar_height // 2
    thumb_r = 10
    
    # Thumb glow
    for i in range(5, 0, -1):
        alpha = int(35 * (i / 5))
        draw.ellipse(
            (thumb_x - thumb_r - i * 2, thumb_y - thumb_r - i * 2,
             thumb_x + thumb_r + i * 2, thumb_y + thumb_r + i * 2),
            fill=(*color, alpha)
        )
    
    # Thumb white
    draw.ellipse(
        (thumb_x - thumb_r, thumb_y - thumb_r,
         thumb_x + thumb_r, thumb_y + thumb_r),
        fill=WHITE
    )
    
    # Thumb colored core
    draw.ellipse(
        (thumb_x - thumb_r + 3, thumb_y - thumb_r + 3,
         thumb_x + thumb_r - 3, thumb_y + thumb_r - 3),
        fill=color
    )
    
    # Time labels
    try:
        time_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 16)
    except:
        try:
            time_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 16)
        except:
            time_font = ImageFont.load_default()
    
    # Start time
    draw.text((0, bar_y + bar_height + 12), "0:00", fill=(255, 255, 255, 180), font=time_font)
    
    return bar_section

def create_navigation_controls(size_config):
    """
    Create navigation controls: ⏮ ▷ ⏭
    Returns tuple of (controls_image, total_width)
    """
    btn_size = size_config.get('btn_size', 48)
    play_size = size_config.get('play_size', 64)
    spacing = size_config.get('spacing', 30)
    color = size_config.get('color', NEON_PURPLE)
    
    total_width = btn_size * 3 + play_size + spacing * 3
    total_height = max(btn_size, play_size) + 40
    
    controls = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(controls)
    
    # Positions
    prev_x = 0
    play_x = btn_size + spacing
    next_x = btn_size + spacing + play_size + spacing
    
    center_y = total_height // 2
    
    # ⏮ Previous button (glowing)
    prev_btn = create_icon_button(btn_size, "prev", color)
    controls.alpha_composite(prev_btn, (prev_x, center_y - btn_size // 2))
    
    # ▶ Play button (large, glowing)
    play_btn = create_play_button(play_size, color)
    controls.alpha_composite(play_btn, (play_x, center_y - play_size // 2))
    
    # ⏭ Next button (glowing)
    next_btn = create_icon_button(btn_size, "next", color)
    controls.alpha_composite(next_btn, (next_x, center_y - btn_size // 2))
    
    return controls, total_width

def create_play_button(size, color=NEON_PURPLE):
    """Create glowing play button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    radius = size // 3 + 2
    
    # Outer glow rings
    for i in range(6, 0, -1):
        alpha = int(20 * (i / 6))
        draw.ellipse(
            (center - radius - i * 3, center - radius - i * 3,
             center + radius + i * 3, center + radius + i * 3),
            fill=(*color, alpha)
        )
    
    # Main circle background
    draw.ellipse(
        (center - radius, center - radius,
         center + radius, center + radius),
        fill=(*color, 230)
    )
    
    # Circle border highlight
    draw.ellipse(
        (center - radius, center - radius,
         center + radius, center + radius),
        outline=(255, 255, 255, 80),
        width=2
    )
    
    # Play triangle (centered)
    tri_size = int(radius * 0.75)
    # Slightly offset right for visual balance
    offset_x = 2
    points = [
        (center - tri_size // 3 + offset_x, center - tri_size // 2),
        (center - tri_size // 3 + offset_x, center + tri_size // 2),
        (center + tri_size * 2 // 3 + offset_x, center)
    ]
    draw.polygon(points, fill=WHITE)
    
    return btn

def create_icon_button(size, icon_type, color=NEON_PURPLE):
    """Create navigation icon buttons (prev/next)"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    # Glow background
    for i in range(3, 0, -1):
        alpha = int(12 * (i / 3))
        draw.rounded_rectangle(
            (i, i, size - i, size - i),
            radius=size // 4,
            fill=(*color, alpha)
        )
    
    # Main circle
    draw.rounded_rectangle(
        (4, 4, size - 4, size - 4),
        radius=size // 4,
        fill=(*color, 40),
        outline=(*color, 130),
        width=2
    )
    
    if icon_type == "prev":
        # ⏮ Previous (two triangles + bar)
        bar_x = size // 4
        tri_w = size // 5
        tri_h = size // 4
        
        # Vertical bar
        draw.rectangle(
            (bar_x - 2, center - tri_h, bar_x + 2, center + tri_h),
            fill=(255, 255, 255, 220)
        )
        
        # Two triangles pointing left
        for offset in [0, size // 5]:
            points = [
                (bar_x + 6 + offset, center - tri_h),
                (bar_x + 6 + offset, center + tri_h),
                (bar_x + 6 - tri_w + offset, center)
            ]
            draw.polygon(points, fill=(255, 255, 255, 220))
    
    elif icon_type == "next":
        # ⏭ Next (two triangles + bar) - mirrored
        bar_x = size - size // 4
        tri_w = size // 5
        tri_h = size // 4
        
        # Vertical bar
        draw.rectangle(
            (bar_x - 2, center - tri_h, bar_x + 2, center + tri_h),
            fill=(255, 255, 255, 220)
        )
        
        # Two triangles pointing right
        for offset in [0, -size // 5]:
            points = [
                (bar_x - 6 + offset, center - tri_h),
                (bar_x - 6 + offset, center + tri_h),
                (bar_x - 6 + tri_w + offset, center)
            ]
            draw.polygon(points, fill=(255, 255, 255, 220))
    
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
        radial_glow = create_radial_glow(
            CANVAS_SIZE, NEON_PURPLE,
            center=(CANVAS_SIZE[0] // 2 + 100, CANVAS_SIZE[1] // 2),
            intensity=0.12
        )
        canvas = Image.alpha_composite(canvas, radial_glow)
        
        particles = create_particle_field(CANVAS_SIZE, NEON_PURPLE_LIGHT)
        canvas = Image.alpha_composite(canvas, particles)
        
        # ===== PROCESS COVER ART =====
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        cover = ImageEnhance.Contrast(cover).enhance(1.2)
        cover = ImageEnhance.Color(cover).enhance(1.15)
        cover = ImageEnhance.Sharpness(cover).enhance(1.3)
        
        # Shadow
        shadow = create_shadow((COVER_SIZE, COVER_SIZE), 40, (15, 15))
        canvas.alpha_composite(shadow, (COVER_X - 20, COVER_Y - 20))
        
        # Glow border
        glow_border = create_glow_border(cover, 20, NEON_PURPLE)
        canvas.alpha_composite(glow_border, (COVER_X - 20, COVER_Y - 20))
        
        # Rounded corners
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle(
            (0, 0, COVER_SIZE, COVER_SIZE),
            radius=20,
            fill=255
        )
        cover.putalpha(cover_mask)
        canvas.alpha_composite(cover, (COVER_X, COVER_Y))
        
        # Neon ring
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
        
        # ===== PROGRESS BAR (RIGHT SIDE, BELOW ARTIST) =====
        progress_section = create_progress_bar_section(
            RIGHT_WIDTH, 8, 0.55, NEON_PURPLE
        )
        canvas.alpha_composite(progress_section, (RIGHT_START_X, PROGRESS_Y))
        
        # Duration label on right side of progress bar
        duration_text = str(duration) if duration else "0:00"
        try:
            dur_bbox = draw.textbbox((0, 0), duration_text, font=small_font)
            dur_width = dur_bbox[2] - dur_bbox[0]
        except:
            dur_width = len(duration_text) * 10
        
        draw.text(
            (RIGHT_START_X + RIGHT_WIDTH - dur_width, PROGRESS_Y + 18),
            duration_text,
            font=small_font,
            fill=(255, 255, 255, 180)
        )
        
        # ===== NAVIGATION CONTROLS (⏮ ▷ ⏭) BELOW PROGRESS BAR =====
        controls, controls_width = create_navigation_controls({
            'btn_size': 48,
            'play_size': 64,
            'spacing': 35,
            'color': NEON_PURPLE
        })
        
        controls_x = RIGHT_START_X + (RIGHT_WIDTH - controls_width) // 2
        controls_y = TIME_Y + 15
        canvas.alpha_composite(controls, (controls_x, controls_y))
        
        # ===== BOT NAME LABEL (BELOW CONTROLS) =====
        bot_name = getattr(app, 'name', 'RaspberryRhythm')
        
        draw.text(
            (RIGHT_START_X + (RIGHT_WIDTH - len(bot_name) * 8) // 2, controls_y + 75),
            f"⚡ {bot_name}",
            font=small_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SIGNATURE (BOTTOM LEFT) =====
        signature = "Made with 🤍 by @DivineDemonn"
        try:
            sig_bbox = draw.textbbox((0, 0), signature, font=small_font)
            sig_width = sig_bbox[2] - sig_bbox[0]
        except:
            sig_width = len(signature) * 8
        
        # Signature with subtle glow
        for offset in range(2, 0, -1):
            draw.text(
                (30 - offset, CANVAS_SIZE[1] - 45 - offset),
                signature,
                font=small_font,
                fill=(*WHITE, 30 - offset * 10)
            )
        
        draw.text(
            (30, CANVAS_SIZE[1] - 45),
            signature,
            font=small_font,
            fill=WHITE
        )
        
        # ===== VERSION LABEL (BOTTOM RIGHT) =====
        version_text = "v3.0"
        draw.text(
            (CANVAS_SIZE[0] - 70, CANVAS_SIZE[1] - 45),
            version_text,
            font=small_font,
            fill=(*NEON_PURPLE_LIGHT, 150)
        )
        
        # ===== DECORATIVE LINE ABOVE SIGNATURE =====
        line_y = CANVAS_SIZE[1] - 60
        draw.line(
            [(30, line_y), (CANVAS_SIZE[0] - 70, line_y)],
            fill=(*NEON_PURPLE, 40),
            width=1
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
            
            for old_file in cache_files[20:]:
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
