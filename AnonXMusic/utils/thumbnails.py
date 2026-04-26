import os
import re
import math
import random
import traceback
from io import BytesIO

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

# ================= ULTRA PREMIUM NEON PURPLE COLOR SCHEME =================
DEEP_VOID = (4, 2, 12)                      # Ultra dark void background
DARK_BG = (10, 6, 24)                       # Deep dark purple-black
NEON_PURPLE = (147, 51, 234)                # #9333EA - Vibrant purple
NEON_PURPLE_LIGHT = (168, 85, 247)          # #A855F7 - Light purple
NEON_PURPLE_BRIGHT = (178, 100, 252)        # Bright purple highlight
NEON_PURPLE_PINK = (192, 38, 211)           # #C026D3 - Purple-pink
NEON_MAGENTA = (217, 70, 239)               # #D946EF - Magenta
NEON_VIOLET = (139, 92, 246)                # #8B5CF6 - Violet
NEON_LAVENDER = (180, 140, 255)             # Lavender glow
WHITE = (255, 255, 255)
LIGHT_GRAY = (210, 210, 225)
DARK_GRAY = (100, 90, 115)
SOFT_PURPLE = (196, 167, 231)               # Soft purple accent
DEEP_PURPLE = (48, 12, 72)                  # Very dark purple
MIDNIGHT_PURPLE = (35, 8, 55)               # Midnight purple
PLATINUM = (230, 225, 240)                  # Platinum white

# ================= PREMIUM LAYOUT POSITIONS =================
COVER_SIZE = 380
COVER_X = 60
COVER_Y = (CANVAS_SIZE[1] - COVER_SIZE) // 2

RIGHT_START_X = COVER_X + COVER_SIZE + 50
RIGHT_WIDTH = CANVAS_SIZE[0] - RIGHT_START_X - 60

# ================= REFINED TEXT & CONTROLS POSITIONS =================
NOW_PLAYING_Y = 115
TITLE_Y = 180
ARTIST_Y = TITLE_Y + 70
PROGRESS_Y = ARTIST_Y + 85
TIME_Y = PROGRESS_Y + 45
CONTROLS_Y = TIME_Y + 50

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

def create_circular_image(image, size):
    """Create circular cropped image"""
    image = image.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result

# ================= ADVANCED VISUAL EFFECTS =================

def create_dynamic_gradient_background(width, height, base_color, accent_color):
    """Create multi-layer dynamic gradient background"""
    gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    
    # Multiple gradient layers for depth
    for y in range(height):
        ratio = y / height
        # Complex color blending
        r = int(base_color[0] * (1 - ratio**0.8) + accent_color[0] * ratio**1.2 * 0.3)
        g = int(base_color[1] * (1 - ratio**0.8) + accent_color[1] * ratio**1.2 * 0.3)
        b = int(base_color[2] * (1 - ratio**0.8) + accent_color[2] * ratio**1.2 * 0.3)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    return gradient

def create_cinematic_glow(size, color, center=None, intensity=0.15):
    """Create cinematic radial glow"""
    if center is None:
        center = (size[0] // 2, size[1] // 2)
    
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    max_radius = int(math.sqrt(size[0]**2 + size[1]**2))
    
    for radius in range(max_radius, 0, -30):
        alpha = int(255 * intensity * (radius / max_radius) * (1 - radius/max_radius)**0.5)
        draw.ellipse(
            (center[0] - radius, center[1] - radius,
             center[0] + radius, center[1] + radius),
            outline=(*color, min(alpha, 12)),
            width=2
        )
    
    return glow.filter(ImageFilter.GaussianBlur(35))

def create_premium_particles(size, color1, color2, count=200):
    """Create premium floating particles with two colors"""
    particles = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(particles)
    random.seed(42)
    
    for _ in range(count):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        radius = random.randint(1, 3)
        alpha = random.randint(10, 45)
        color = color1 if random.random() > 0.5 else color2
        
        # Draw tiny stars/crosses for some particles
        if random.random() > 0.7:
            draw.line([(x-2, y), (x+2, y)], fill=(*color, alpha), width=1)
            draw.line([(x, y-2), (x, y+2)], fill=(*color, alpha), width=1)
        else:
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                fill=(*color, alpha)
            )
    
    return particles

def create_glass_morphism_panel(size, color, radius=25, opacity=10):
    """Create glass morphism panel effect"""
    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    
    # Glass background
    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius=radius,
        fill=(*color, opacity)
    )
    
    # Glass border highlight
    draw.rounded_rectangle(
        (1, 1, size[0]-1, size[1]-1),
        radius=radius,
        outline=(255, 255, 255, 15),
        width=1
    )
    
    return panel

def create_luxury_border(size, color, border_width=3):
    """Create luxury golden/neon border"""
    border = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(border)
    
    # Outer glow
    for i in range(12, 0, -2):
        alpha = int(8 * (i / 12))
        draw.rounded_rectangle(
            (i, i, size[0]-i, size[1]-i),
            radius=25 + i,
            outline=(*color, alpha),
            width=border_width + i//3
        )
    
    # Main border
    draw.rounded_rectangle(
        (2, 2, size[0]-2, size[1]-2),
        radius=25,
        outline=(*color, 180),
        width=border_width
    )
    
    # Inner white highlight
    draw.rounded_rectangle(
        (4, 4, size[0]-4, size[1]-4),
        radius=23,
        outline=(255, 255, 255, 50),
        width=1
    )
    
    return border

def create_premium_progress_bar(width, height, progress, color, accent_color):
    """Create ultra-premium progress bar with gradients"""
    bar_section = Image.new("RGBA", (width, height + 55), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar_section)
    
    bar_height = height
    bar_y = 15
    
    # Outer glow track
    for i in range(5, 0, -1):
        alpha = int(8 + i * 3)
        draw.rounded_rectangle(
            (0 - i, bar_y - i, width + i, bar_y + bar_height + i),
            radius=(bar_height + i) // 2,
            fill=(*color, alpha)
        )
    
    # Track background
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_height),
        radius=bar_height // 2,
        fill=(255, 255, 255, 10)
    )
    
    # Track inner line
    draw.rounded_rectangle(
        (1, bar_y+1, width-1, bar_y + bar_height-1),
        radius=(bar_height-1) // 2,
        outline=(255, 255, 255, 20),
        width=1
    )
    
    # Progress fill
    fill_width = int(width * progress)
    
    if fill_width > 0:
        # Progress glow
        for i in range(8, 0, -1):
            alpha = int(10 * (i / 8))
            draw.rounded_rectangle(
                (0 - i, bar_y - i, fill_width + i, bar_y + bar_height + i),
                radius=(bar_height + i) // 2,
                fill=(*accent_color, alpha)
            )
        
        # Gradient progress fill
        for x in range(fill_width):
            ratio = x / width
            r = int(color[0] * (1 - ratio) + accent_color[0] * ratio)
            g = int(color[1] * (1 - ratio) + accent_color[1] * ratio)
            b = int(color[2] * (1 - ratio) + accent_color[2] * ratio)
            draw.line(
                [(x, bar_y), (x, bar_y + bar_height)],
                fill=(r, g, b, 240)
            )
        
        # Highlight on progress
        draw.rounded_rectangle(
            (2, bar_y+2, fill_width-2, bar_y + bar_height//2),
            radius=bar_height//2,
            fill=(255, 255, 255, 30)
        )
    
    # Premium thumb with diamond shape
    thumb_x = max(14, fill_width)
    thumb_y = bar_y + bar_height // 2
    
    # Thumb glow
    for i in range(6, 0, -1):
        alpha = int(40 * (i / 6))
        draw.ellipse(
            (thumb_x - 12 - i*2, thumb_y - 12 - i*2,
             thumb_x + 12 + i*2, thumb_y + 12 + i*2),
            fill=(*accent_color, alpha)
        )
    
    # Thumb outer ring
    draw.ellipse(
        (thumb_x - 12, thumb_y - 12, thumb_x + 12, thumb_y + 12),
        fill=(30, 10, 50, 255),
        outline=(*accent_color, 200),
        width=2
    )
    
    # Thumb inner diamond
    diamond_size = 6
    draw.polygon([
        (thumb_x, thumb_y - diamond_size),
        (thumb_x + diamond_size, thumb_y),
        (thumb_x, thumb_y + diamond_size),
        (thumb_x - diamond_size, thumb_y)
    ], fill=WHITE)
    
    return bar_section

async def download_profile_pic(user_id, size=64):
    """Download user's Telegram profile picture"""
    try:
        import asyncio
        
        # Try to get profile photos
        photos = await app.get_profile_photos(user_id, limit=1)
        if photos and len(photos) > 0:
            file_id = photos[0].file_id
            file_path = await app.download_media(file_id)
            
            if file_path:
                profile_img = Image.open(file_path).convert("RGBA")
                os.remove(file_path)
                return create_circular_image(profile_img, size)
    except:
        pass
    
    # Return default avatar
    default = Image.new("RGBA", (size, size), (*NEON_PURPLE, 200))
    draw = ImageDraw.Draw(default)
    # Draw person icon
    draw.ellipse((size//4, size//3, size-size//4, size-size//3), 
                 outline=WHITE, width=2)
    draw.ellipse((size//4, size//2, size-size//4, size-size//3), 
                 fill=WHITE)
    
    return create_circular_image(default, size)

def create_profile_badge(profile_pic, size=80, border_color=NEON_PURPLE):
    """Create profile picture badge with neon border"""
    badge = Image.new("RGBA", (size + 20, size + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    
    center = (size + 20) // 2
    
    # Glow border
    for i in range(5, 0, -1):
        alpha = int(25 * (i / 5))
        r = size//2 + 5 + i*2
        draw.ellipse(
            (center - r, center - r, center + r, center + r),
            outline=(*border_color, alpha),
            width=2
        )
    
    # Main border
    r = size//2 + 3
    draw.ellipse(
        (center - r, center - r, center + r, center + r),
        fill=(20, 8, 40, 200),
        outline=(*border_color, 180),
        width=2
    )
    
    # Paste profile picture
    badge.paste(profile_pic, (10, 10), profile_pic)
    
    return badge

def load_play_icons():
    """Load play icons from assets or create premium default ones"""
    icon_paths = [
        "AnonXMusic/assets/play_icons.png",
        "AnonXMusic/assets/play_icons.jpeg",
        "AnonXMusic/assets/play_icons.jpg",
    ]
    
    for path in icon_paths:
        if os.path.exists(path):
            try:
                icons = Image.open(path).convert("RGBA")
                return icons
            except:
                continue
    
    return None

def create_premium_controls(icons_image, size_config):
    """Create premium controls from asset image or generate them"""
    btn_size = size_config.get('btn_size', 52)
    play_size = size_config.get('play_size', 72)
    spacing = size_config.get('spacing', 30)
    color = size_config.get('color', NEON_PURPLE)
    
    total_width = btn_size * 2 + play_size + spacing * 3
    total_height = max(btn_size, play_size) + 50
    
    controls = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    
    if icons_image:
        # Use asset image for controls
        # Assuming the asset has icons arranged horizontally
        img_width = icons_image.width
        section_width = img_width // 3
        
        # Previous
        prev = icons_image.crop((0, 0, section_width, icons_image.height))
        prev = prev.resize((btn_size, btn_size), Image.LANCZOS)
        
        # Play
        play = icons_image.crop((section_width, 0, section_width*2, icons_image.height))
        play = play.resize((play_size, play_size), Image.LANCZOS)
        
        # Next
        next_icon = icons_image.crop((section_width*2, 0, img_width, icons_image.height))
        next_icon = next_icon.resize((btn_size, btn_size), Image.LANCZOS)
        
        # Apply neon tint
        for img in [prev, play, next_icon]:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.5)
        
        # Positions
        prev_x = 0
        play_x = btn_size + spacing
        next_x = btn_size + spacing + play_size + spacing
        
        center_y = total_height // 2
        
        controls.alpha_composite(prev, (prev_x, center_y - btn_size // 2))
        controls.alpha_composite(play, (play_x, center_y - play_size // 2))
        controls.alpha_composite(next_icon, (next_x, center_y - btn_size // 2))
    else:
        # Fallback to generated icons
        prev_x = 0
        play_x = btn_size + spacing
        next_x = btn_size + spacing + play_size + spacing
        center_y = total_height // 2
        
        prev_btn = create_fallback_icon(btn_size, "prev", color)
        play_btn = create_fallback_play(play_size, color)
        next_btn = create_fallback_icon(btn_size, "next", color)
        
        controls.alpha_composite(prev_btn, (prev_x, center_y - btn_size // 2))
        controls.alpha_composite(play_btn, (play_x, center_y - play_size // 2))
        controls.alpha_composite(next_btn, (next_x, center_y - btn_size // 2))
    
    return controls, total_width

def create_fallback_play(size, color):
    """Create fallback premium play button"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    radius = size // 3
    
    # Multi-layer glow
    for i in range(8, 0, -1):
        alpha = int(15 * (i / 8))
        draw.ellipse(
            (center - radius - i*4, center - radius - i*4,
             center + radius + i*4, center + radius + i*4),
            fill=(*color, alpha)
        )
    
    # Main circle with gradient effect
    draw.ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        fill=(*color, 240)
    )
    
    # Inner highlight
    draw.ellipse(
        (center - radius//2, center - radius, center + radius//2, center - radius//2),
        fill=(255, 255, 255, 40)
    )
    
    # Play triangle
    tri_size = int(radius * 0.7)
    offset = 3
    points = [
        (center - tri_size//3 + offset, center - tri_size//2),
        (center - tri_size//3 + offset, center + tri_size//2),
        (center + tri_size*2//3 + offset, center)
    ]
    draw.polygon(points, fill=PLATINUM)
    
    return btn

def create_fallback_icon(size, icon_type, color):
    """Create fallback navigation icons"""
    btn = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = size // 2
    
    # Glow circle
    for i in range(4, 0, -1):
        alpha = int(15 * (i / 4))
        draw.rounded_rectangle(
            (i, i, size-i, size-i),
            radius=size//4,
            fill=(*color, alpha)
        )
    
    # Main circle
    draw.rounded_rectangle(
        (3, 3, size-3, size-3),
        radius=size//4,
        fill=(*color, 50),
        outline=(*NEON_PURPLE_LIGHT, 150),
        width=2
    )
    
    if icon_type == "prev":
        # Double left arrows
        bar_x = size//4 - 2
        tri_w, tri_h = size//6, size//5
        
        draw.rectangle((bar_x, center-tri_h, bar_x+3, center+tri_h), fill=PLATINUM)
        
        for offset in [0, size//6]:
            points = [
                (bar_x+5+offset, center-tri_h),
                (bar_x+5+offset, center+tri_h),
                (bar_x+5-tri_w+offset, center)
            ]
            draw.polygon(points, fill=PLATINUM)
    
    elif icon_type == "next":
        # Double right arrows
        bar_x = size - size//4 + 2
        tri_w, tri_h = size//6, size//5
        
        draw.rectangle((bar_x-3, center-tri_h, bar_x, center+tri_h), fill=PLATINUM)
        
        for offset in [0, -size//6]:
            points = [
                (bar_x-5+offset, center-tri_h),
                (bar_x-5+offset, center+tri_h),
                (bar_x-5+tri_w+offset, center)
            ]
            draw.polygon(points, fill=PLATINUM)
    
    return btn

# ================= MAIN PREMIUM FUNCTION =================

async def get_thumb(videoid, user_id=None):
    """
    Generate ultra-premium neon purple thumbnail.
    Features:
    - User profile picture badge
    - Premium play icons from assets
    - Cinematic lighting effects
    - Glass morphism elements
    """
    ensure_cache_dir()
    
    cache_name = f"{videoid}_{user_id}_premium.png" if user_id else f"{videoid}_premium_thumb.png"
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
        
        thumb_url = data.get("thumbnails", [{}])[-1].get("url", "")
        if thumb_url:
            thumb_url = thumb_url.split("?")[0]
        
        if not thumb_url:
            return YOUTUBE_IMG_URL
            
    except Exception as e:
        print(f"[Premium Thumbnail] Error fetching data: {e}")
        return YOUTUBE_IMG_URL
    
    # ========== DOWNLOAD ASSETS ==========
    thumb_file = os.path.join(CACHE_DIR, f"{videoid}_raw.jpg")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url, timeout=10) as resp:
                if resp.status != 200:
                    return YOUTUBE_IMG_URL
                    
                async with aiofiles.open(thumb_file, "wb") as f:
                    await f.write(await resp.read())
    except Exception as e:
        print(f"[Premium Thumbnail] Error downloading cover: {e}")
        return YOUTUBE_IMG_URL
    
    # ========== CREATE MASTERPIECE CANVAS ==========
    try:
        cover_img = Image.open(thumb_file).convert("RGBA")
        
        # Create cinematic gradient background
        bg = create_dynamic_gradient_background(
            CANVAS_SIZE[0], CANVAS_SIZE[1],
            MIDNIGHT_PURPLE, DEEP_PURPLE
        )
        
        canvas = Image.new("RGBA", CANVAS_SIZE)
        canvas.paste(bg, (0, 0))
        
        # ===== PREMIUM BACKGROUND EFFECTS =====
        
        # Cinematic glow (center-right for balance)
        cinematic = create_cinematic_glow(
            CANVAS_SIZE, NEON_PURPLE,
            center=(CANVAS_SIZE[0]//2 + 150, CANVAS_SIZE[1]//2),
            intensity=0.18
        )
        canvas = Image.alpha_composite(canvas, cinematic)
        
        # Premium particles
        particles = create_premium_particles(CANVAS_SIZE, NEON_PURPLE_LIGHT, NEON_VIOLET, 200)
        canvas = Image.alpha_composite(canvas, particles)
        
        # ===== PROCESS COVER ART WITH PREMIUM EFFECTS =====
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        cover = ImageEnhance.Contrast(cover).enhance(1.3)
        cover = ImageEnhance.Color(cover).enhance(1.2)
        cover = ImageEnhance.Sharpness(cover).enhance(1.5)
        cover = ImageEnhance.Brightness(cover).enhance(1.05)
        
        # Premium shadow with multiple layers
        shadow1 = create_shadow_enhanced((COVER_SIZE, COVER_SIZE), 30, (10, 10), 40)
        shadow2 = create_shadow_enhanced((COVER_SIZE, COVER_SIZE), 50, (5, 5), 30)
        canvas.alpha_composite(shadow2, (COVER_X - 25, COVER_Y - 25))
        canvas.alpha_composite(shadow1, (COVER_X - 15, COVER_Y - 15))
        
        # Glow border
        glow_border = create_luxury_border(
            (COVER_SIZE + 30, COVER_SIZE + 30), NEON_PURPLE, 3
        )
        canvas.alpha_composite(glow_border, (COVER_X - 15, COVER_Y - 15))
        
        # Glass morphism overlay on cover
        glass_cover = create_glass_morphism_panel(
            (COVER_SIZE, COVER_SIZE), NEON_VIOLET, 20, 8
        )
        
        # Rounded corners for cover
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle(
            (0, 0, COVER_SIZE, COVER_SIZE), radius=22, fill=255
        )
        
        cover_rgba = Image.new("RGBA", (COVER_SIZE, COVER_SIZE), (0, 0, 0, 0))
        cover_rgba.paste(cover, (0, 0), cover_mask)
        cover_rgba = Image.alpha_composite(cover_rgba, glass_cover)
        
        canvas.alpha_composite(cover_rgba, (COVER_X, COVER_Y))
        
        # ===== LOAD FONTS =====
        font_paths = [
            "AnonXMusic/assets/font2.ttf",
            "AnonXMusic/assets/font.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        
        now_playing_font = title_font = artist_font = small_font = None
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    if now_playing_font is None:
                        now_playing_font = ImageFont.truetype(font_path, 20)
                    if title_font is None:
                        title_font = ImageFont.truetype(font_path, 52)
                    if artist_font is None:
                        artist_font = ImageFont.truetype(font_path, 30)
                    if small_font is None:
                        small_font = ImageFont.truetype(font_path, 17)
            except:
                continue
        
        if not title_font:
            title_font = artist_font = now_playing_font = small_font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(canvas)
        
        # ===== DOWNLOAD USER PROFILE PICTURE =====
        profile_pic = None
        if user_id:
            try:
                profile_pic = await download_profile_pic(user_id, 64)
            except:
                pass
        
        # ===== "NOW PLAYING" WITH PROFILE BADGE =====
        if profile_pic and user_id:
            # Create profile badge
            profile_badge = create_profile_badge(profile_pic, 64, NEON_PURPLE_LIGHT)
            canvas.alpha_composite(profile_badge, (RIGHT_START_X - 5, NOW_PLAYING_Y - 50))
            
            # Now playing text shifted right for badge
            now_playing_x = RIGHT_START_X + 75
        else:
            now_playing_x = RIGHT_START_X
        
        now_playing_text = "◈ NOW PLAYING"
        
        # Glowing now playing text
        for offset in range(4, 0, -1):
            glow_alpha = 40 - offset * 8
            draw.text(
                (now_playing_x - offset, NOW_PLAYING_Y - offset),
                now_playing_text,
                font=now_playing_font,
                fill=(*NEON_PURPLE_LIGHT, glow_alpha)
            )
        
        draw.text(
            (now_playing_x, NOW_PLAYING_Y),
            now_playing_text,
            font=now_playing_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SONG TITLE (PREMIUM STYLING) =====
        title_text = trim_text(title, title_font, RIGHT_WIDTH)
        
        # Multi-layer glow for title
        for offset in range(5, 0, -1):
            glow_alpha = 35 - offset * 6
            draw.text(
                (RIGHT_START_X - offset, TITLE_Y - offset),
                title_text,
                font=title_font,
                fill=(*NEON_PURPLE_BRIGHT, glow_alpha)
            )
        
        # Title with gradient effect
        title_gradient = Image.new("RGBA", (RIGHT_WIDTH + 10, 70), (0, 0, 0, 0))
        title_grad_draw = ImageDraw.Draw(title_gradient)
        
        for x in range(RIGHT_WIDTH):
            ratio = x / RIGHT_WIDTH
            r = int(255 * (1 - ratio) + NEON_PURPLE_LIGHT[0] * ratio)
            g = int(255 * (1 - ratio) + NEON_PURPLE_LIGHT[1] * ratio)
            b = int(255 * (1 - ratio) + NEON_PURPLE_LIGHT[2] * ratio)
            title_grad_draw.text(
                (x, 0), title_text,
                font=title_font,
                fill=(r, g, b, min(255, 200 + int(ratio*55)))
            )
        
        draw.text(
            (RIGHT_START_X, TITLE_Y),
            title_text,
            font=title_font,
            fill=PLATINUM
        )
        
        # ===== ARTIST NAME =====
        artist_text = trim_text(f"🎙️ {artist}", artist_font, RIGHT_WIDTH - 20)
        
        draw.text(
            (RIGHT_START_X, ARTIST_Y),
            artist_text,
            font=artist_font,
            fill=LIGHT_GRAY
        )
        
        # ===== PREMIUM PROGRESS BAR =====
        progress_section = create_premium_progress_bar(
            RIGHT_WIDTH, 10, 0.55, NEON_PURPLE, NEON_MAGENTA
        )
        canvas.alpha_composite(progress_section, (RIGHT_START_X, PROGRESS_Y))
        
        # Duration label
        duration_text = str(duration) if duration else "0:00"
        try:
            dur_bbox = draw.textbbox((0, 0), duration_text, font=small_font)
            dur_width = dur_bbox[2] - dur_bbox[0]
        except:
            dur_width = len(duration_text) * 10
        
        draw.text(
            (RIGHT_START_X + RIGHT_WIDTH - dur_width, PROGRESS_Y + 25),
            duration_text,
            font=small_font,
            fill=(255, 255, 255, 200)
        )
        
        # ===== PREMIUM PLAY CONTROLS FROM ASSETS =====
        icons_asset = load_play_icons()
        
        controls, controls_width = create_premium_controls(icons_asset, {
            'btn_size': 52,
            'play_size': 72,
            'spacing': 40,
            'color': NEON_PURPLE
        })
        
        controls_x = RIGHT_START_X + (RIGHT_WIDTH - controls_width) // 2
        controls_y = CONTROLS_Y
        canvas.alpha_composite(controls, (controls_x, controls_y))
        
        # ===== BOT NAME WITH STATUS DOT =====
        bot_name = getattr(app, 'name', 'RaspberryRhythm')
        
        # Green status dot
        dot_x = RIGHT_START_X + (RIGHT_WIDTH - len(bot_name) * 9) // 2 - 20
        dot_y = controls_y + 95
        draw.ellipse((dot_x, dot_y, dot_x + 8, dot_y + 8), fill=(0, 255, 100, 230))
        
        # Online text
        draw.text(
            (dot_x + 14, dot_y - 3),
            f"⚡ {bot_name}",
            font=small_font,
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== PREMIUM SIGNATURE =====
        signature = "✦ Made with 🤍 by @DivineDemonn ✦"
        try:
            sig_bbox = draw.textbbox((0, 0), signature, font=small_font)
            sig_width = sig_bbox[2] - sig_bbox[0]
        except:
            sig_width = len(signature) * 9
        
        sig_x = (CANVAS_SIZE[0] - sig_width) // 2
        sig_y = CANVAS_SIZE[1] - 50
        
        # Signature glow
        for offset in range(3, 0, -1):
            draw.text(
                (sig_x - offset, sig_y - offset),
                signature,
                font=small_font,
                fill=(220, 220, 240, 25 - offset * 8)
            )
        
        draw.text(
            (sig_x, sig_y),
            signature,
            font=small_font,
            fill=PLATINUM
        )
        
        # ===== TOP DECORATIVE LINE =====
        for i in range(3):
            alpha = 60 - i * 15
            draw.line(
                [(30, 20 + i*2), (CANVAS_SIZE[0] - 30, 20 + i*2)],
                fill=(*NEON_PURPLE_LIGHT, alpha),
                width=1
            )
        
        # ===== SAVE =====
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
        
        # Cache management
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
        print(f"[Premium Thumbnail] Error: {e}")
        traceback.print_exc()
        
        try:
            os.remove(thumb_file)
        except:
            pass
        
        return YOUTUBE_IMG_URL


# Enhanced shadow function
def create_shadow_enhanced(image_size, shadow_size, offset, alpha):
    """Create enhanced multi-layer shadow"""
    shadow = Image.new("RGBA", 
                       (image_size[0] + shadow_size, image_size[1] + shadow_size),
                       (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    
    draw.rounded_rectangle(
        (offset[0], offset[1], image_size[0] + offset[0], image_size[1] + offset[1]),
        radius=22,
        fill=(0, 0, 0, alpha)
    )
    
    return shadow.filter(ImageFilter.GaussianBlur(30))
