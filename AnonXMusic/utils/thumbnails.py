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
DEEP_BG = (6, 3, 16)
DARK_BG = (12, 8, 28)
NEON_PURPLE = (147, 51, 234)
NEON_PURPLE_LIGHT = (168, 85, 247)
NEON_PURPLE_BRIGHT = (180, 105, 252)
NEON_MAGENTA = (217, 70, 239)
NEON_VIOLET = (139, 92, 246)
WHITE = (255, 255, 255)
CLEAN_WHITE = (245, 245, 255)
LIGHT_GRAY = (200, 195, 215)
DARK_GRAY = (100, 90, 115)
PLATINUM = (235, 230, 245)

# ================= LAYOUT POSITIONS =================
COVER_SIZE = 400
COVER_X = 50
COVER_Y = (CANVAS_SIZE[1] - COVER_SIZE) // 2

RIGHT_START_X = COVER_X + COVER_SIZE + 45
RIGHT_WIDTH = CANVAS_SIZE[0] - RIGHT_START_X - 50

# ================= TEXT POSITIONS =================
NOW_PLAYING_Y = 100
TITLE_Y = 170
ARTIST_Y = 240
PROGRESS_Y = 320
CONTROLS_Y = 420
BOT_NAME_Y = 540
SIGNATURE_Y = 670

# ================= HELPER FUNCTIONS =================

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def trim_text(text, font, max_width):
    try:
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return text
        while True:
            text = text[:-1]
            bbox = font.getbbox(text + "…")
            if (bbox[2] - bbox[0]) <= max_width:
                return text + "…"
    except:
        return text[:25] + "..." if len(text) > 25 else text

def create_circular_image(image, size):
    """Create a clean circular cropped image"""
    image = image.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result

# ================= BACKGROUND EFFECTS =================

def create_background(width, height):
    """Create clean dark gradient background"""
    bg = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bg)
    
    for y in range(height):
        ratio = y / height
        r = int(DEEP_BG[0] + (DARK_BG[0] - DEEP_BG[0]) * ratio)
        g = int(DEEP_BG[1] + (DARK_BG[1] - DEEP_BG[1]) * ratio)
        b = int(DEEP_BG[2] + (DARK_BG[2] - DEEP_BG[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    return bg

def create_subtle_glow(size):
    """Create subtle purple glow"""
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    cx, cy = size[0] // 2 + 100, size[1] // 2
    
    for r in range(500, 0, -50):
        alpha = int(10 * (r / 500))
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            outline=(*NEON_PURPLE, alpha),
            width=3
        )
    
    return glow.filter(ImageFilter.GaussianBlur(40))

def create_particles(size):
    """Create subtle sparkle particles"""
    particles = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(particles)
    random.seed(42)
    
    for _ in range(100):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        r = random.randint(1, 3)
        alpha = random.randint(15, 40)
        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=(*NEON_PURPLE_LIGHT, alpha)
        )
    
    return particles

# ================= COVER ART EFFECTS =================

def create_cover_shadow():
    """Create shadow for cover art"""
    shadow_size = COVER_SIZE + 40
    shadow = Image.new("RGBA", (shadow_size, shadow_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    
    draw.rounded_rectangle(
        (20, 20, COVER_SIZE + 20, COVER_SIZE + 20),
        radius=25,
        fill=(0, 0, 0, 180)
    )
    
    return shadow.filter(ImageFilter.GaussianBlur(30))

def create_cover_glow_border():
    """Create neon glow border for cover"""
    border_size = COVER_SIZE + 30
    border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(border)
    
    # Outer glow layers
    for i in range(10, 0, -2):
        alpha = int(15 * (i / 10))
        draw.rounded_rectangle(
            (i, i, border_size - i, border_size - i),
            radius=28 + i,
            outline=(*NEON_PURPLE, alpha),
            width=3
        )
    
    # Main border
    draw.rounded_rectangle(
        (3, 3, border_size - 3, border_size - 3),
        radius=26,
        outline=(*NEON_PURPLE_LIGHT, 200),
        width=2
    )
    
    return border

# ================= PROGRESS BAR =================

def create_progress_bar(width, progress, color):
    """Create clean progress bar"""
    bar_h = 8
    total_h = bar_h + 60
    
    bar_img = Image.new("RGBA", (width, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bar_img)
    
    bar_y = 10
    
    # Track background
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_h),
        radius=bar_h // 2,
        fill=(255, 255, 255, 15)
    )
    
    # Track outline
    draw.rounded_rectangle(
        (0, bar_y, width, bar_y + bar_h),
        radius=bar_h // 2,
        outline=(255, 255, 255, 30),
        width=1
    )
    
    # Progress fill
    fill_w = int(width * progress)
    
    if fill_w > 0:
        # Glow behind progress
        for i in range(5, 0, -1):
            alpha = int(15 * (i / 5))
            draw.rounded_rectangle(
                (0 - i, bar_y - i, fill_w + i, bar_y + bar_h + i),
                radius=(bar_h + i) // 2,
                fill=(*color, alpha)
            )
        
        # Main progress
        draw.rounded_rectangle(
            (0, bar_y, fill_w, bar_y + bar_h),
            radius=bar_h // 2,
            fill=color
        )
        
        # Highlight on top
        draw.rounded_rectangle(
            (0, bar_y, fill_w, bar_y + bar_h // 2),
            radius=bar_h // 2,
            fill=(255, 255, 255, 35)
        )
    
    # Thumb
    thumb_x = max(10, fill_w)
    thumb_y = bar_y + bar_h // 2
    
    # Thumb glow
    for i in range(4, 0, -1):
        alpha = int(50 * (i / 4))
        draw.ellipse(
            (thumb_x - 10 - i*2, thumb_y - 10 - i*2,
             thumb_x + 10 + i*2, thumb_y + 10 + i*2),
            fill=(*color, alpha)
        )
    
    # Thumb white circle
    draw.ellipse(
        (thumb_x - 10, thumb_y - 10, thumb_x + 10, thumb_y + 10),
        fill=WHITE
    )
    
    # Thumb colored dot
    draw.ellipse(
        (thumb_x - 4, thumb_y - 4, thumb_x + 4, thumb_y + 4),
        fill=color
    )
    
    return bar_img

# ================= CONTROL BUTTONS =================

def create_play_button(size):
    """Create premium play button using play_icons asset or generate"""
    asset_path = "AnonXMusic/assets/play_icons.png"
    
    # Try to load from asset
    if os.path.exists(asset_path):
        try:
            asset = Image.open(asset_path).convert("RGBA")
            # Extract play button (middle section)
            section_w = asset.width // 3
            play_section = asset.crop((section_w, 0, section_w * 2, asset.height))
            play_section = play_section.resize((size, size), Image.LANCZOS)
            
            # Add glow background
            btn = Image.new("RGBA", (size + 20, size + 20), (0, 0, 0, 0))
            draw = ImageDraw.Draw(btn)
            
            # Glow circle behind
            for i in range(5, 0, -1):
                alpha = int(20 * (i / 5))
                draw.ellipse(
                    (10 - i*3, 10 - i*3, size + 10 + i*3, size + 10 + i*3),
                    fill=(*NEON_PURPLE, alpha)
                )
            
            btn.paste(play_section, (10, 10), play_section)
            return btn
        except:
            pass
    
    # Fallback: generate play button
    btn = Image.new("RGBA", (size + 20, size + 20), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = (size + 20) // 2
    radius = size // 3
    
    # Glow rings
    for i in range(6, 0, -1):
        alpha = int(18 * (i / 6))
        draw.ellipse(
            (center - radius - i*3, center - radius - i*3,
             center + radius + i*3, center + radius + i*3),
            fill=(*NEON_PURPLE, alpha)
        )
    
    # Main circle
    draw.ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        fill=(*NEON_PURPLE, 240)
    )
    
    # Play triangle
    tri = int(radius * 0.7)
    points = [
        (center - tri//3 + 3, center - tri//2),
        (center - tri//3 + 3, center + tri//2),
        (center + tri*2//3 + 3, center)
    ]
    draw.polygon(points, fill=WHITE)
    
    return btn

def create_nav_button(size, direction):
    """Create prev/next navigation buttons from asset or generate"""
    asset_path = "AnonXMusic/assets/play_icons.png"
    
    if os.path.exists(asset_path):
        try:
            asset = Image.open(asset_path).convert("RGBA")
            section_w = asset.width // 3
            
            if direction == "prev":
                icon_section = asset.crop((0, 0, section_w, asset.height))
            else:
                icon_section = asset.crop((section_w * 2, 0, asset.width, asset.height))
            
            icon_section = icon_section.resize((size, size), Image.LANCZOS)
            
            btn = Image.new("RGBA", (size + 10, size + 10), (0, 0, 0, 0))
            btn.paste(icon_section, (5, 5), icon_section)
            return btn
        except:
            pass
    
    # Fallback: generate nav buttons
    btn = Image.new("RGBA", (size + 10, size + 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(btn)
    center = (size + 10) // 2
    r = size // 3
    
    # Glow circle
    draw.ellipse(
        (center - r - 2, center - r - 2, center + r + 2, center + r + 2),
        fill=(*NEON_PURPLE, 30),
        outline=(*NEON_PURPLE_LIGHT, 150),
        width=2
    )
    
    tri_w = size // 7
    tri_h = size // 5
    
    if direction == "prev":
        # Left arrows
        bar_x = center - r + 5
        draw.rectangle((bar_x, center - tri_h, bar_x + 3, center + tri_h), fill=WHITE)
        
        for offset in [0, size // 7]:
            points = [
                (bar_x + 6 + offset, center - tri_h),
                (bar_x + 6 + offset, center + tri_h),
                (bar_x + 6 - tri_w + offset, center)
            ]
            draw.polygon(points, fill=WHITE)
    else:
        # Right arrows
        bar_x = center + r - 8
        draw.rectangle((bar_x, center - tri_h, bar_x + 3, center + tri_h), fill=WHITE)
        
        for offset in [0, -size // 7]:
            points = [
                (bar_x - 6 + offset, center - tri_h),
                (bar_x - 6 + offset, center + tri_h),
                (bar_x - 6 + tri_w + offset, center)
            ]
            draw.polygon(points, fill=WHITE)
    
    return btn

# ================= PADDING & LOADING FONTS =================

def load_fonts():
    """Load all required fonts with fallbacks"""
    fonts = {}
    
    font_map = {
        'now_playing': ('AnonXMusic/assets/font2.ttf', 22),
        'title': ('AnonXMusic/assets/font2.ttf', 50),
        'artist': ('AnonXMusic/assets/font.ttf', 30),
        'small': ('AnonXMusic/assets/font.ttf', 17),
    }
    
    for name, (path, size) in font_map.items():
        try:
            if os.path.exists(path):
                fonts[name] = ImageFont.truetype(path, size)
            else:
                raise Exception("Font not found")
        except:
            try:
                # Try system fonts
                fonts[name] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
            except:
                try:
                    fonts[name] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
                except:
                    fonts[name] = ImageFont.load_default()
    
    return fonts

# ================= PROFILE PICTURE =================

async def get_user_profile_pic(user_id):
    """Get user's Telegram profile picture"""
    if not user_id:
        return None
    
    try:
        photos = await app.get_profile_photos(user_id, limit=1)
        if photos and len(photos) > 0:
            file_path = await app.download_media(photos[0].file_id)
            if file_path and os.path.exists(file_path):
                img = Image.open(file_path).convert("RGBA")
                os.remove(file_path)
                return create_circular_image(img, 70)
    except Exception as e:
        print(f"Profile pic error: {e}")
    
    # Default avatar
    size = 70
    default = Image.new("RGBA", (size, size), (*NEON_PURPLE, 200))
    draw = ImageDraw.Draw(default)
    draw.ellipse((size//4, size//3, size*3//4, size*2//3), outline=WHITE, width=2)
    draw.ellipse((size//4, size//2, size*3//4, size*2//3+5), fill=WHITE)
    
    return create_circular_image(default, size)

def create_profile_badge(profile_pic):
    """Create profile picture with neon ring"""
    badge_size = 100
    badge = Image.new("RGBA", (badge_size, badge_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    center = badge_size // 2
    
    # Neon ring
    for i in range(4, 0, -1):
        alpha = int(30 * (i / 4))
        r = 35 + 2 + i * 2
        draw.ellipse(
            (center - r, center - r, center + r, center + r),
            outline=(*NEON_PURPLE_LIGHT, alpha),
            width=2
        )
    
    # Main ring
    r = 37
    draw.ellipse(
        (center - r, center - r, center + r, center + r),
        outline=(*NEON_PURPLE_LIGHT, 200),
        width=2
    )
    
    # Paste profile pic
    badge.paste(profile_pic, (15, 15), profile_pic)
    
    return badge

# ================= MAIN FUNCTION =================

async def get_thumb(videoid, user_id=None):
    """Generate premium neon purple thumbnail"""
    ensure_cache_dir()
    
    cache_name = f"{videoid}_{user_id}.png" if user_id else f"{videoid}.png"
    cache_path = os.path.join(CACHE_DIR, cache_name)
    
    if os.path.exists(cache_path):
        return cache_path
    
    # ===== FETCH DATA =====
    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        vs = VideosSearch(url, limit=1)
        results = await vs.next()
        data = results["result"][0]
        
        title = re.sub(r"[^\w\s-]", "", data.get("title", "Unknown")).strip()
        title = re.sub(r"\s+", " ", title)
        
        artist = data.get("channel", {}).get("name", "Unknown Artist")
        duration = data.get("duration", "0:00")
        
        thumb_url = data.get("thumbnails", [{}])[-1].get("url", "")
        if thumb_url:
            thumb_url = thumb_url.split("?")[0]
        
        if not thumb_url:
            return YOUTUBE_IMG_URL
    except:
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
    
    # ===== CREATE THUMBNAIL =====
    try:
        cover_img = Image.open(thumb_file).convert("RGBA")
        
        # Background
        bg = create_background(*CANVAS_SIZE)
        canvas = Image.new("RGBA", CANVAS_SIZE)
        canvas.paste(bg, (0, 0))
        
        # Glow effect
        glow = create_subtle_glow(CANVAS_SIZE)
        canvas = Image.alpha_composite(canvas, glow)
        
        # Particles
        particles = create_particles(CANVAS_SIZE)
        canvas = Image.alpha_composite(canvas, particles)
        
        # ===== COVER ART =====
        cover = cover_img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        cover = ImageEnhance.Contrast(cover).enhance(1.2)
        cover = ImageEnhance.Color(cover).enhance(1.1)
        cover = ImageEnhance.Sharpness(cover).enhance(1.3)
        
        # Shadow
        shadow = create_cover_shadow()
        canvas.alpha_composite(shadow, (COVER_X - 20, COVER_Y - 20))
        
        # Glow border
        glow_border = create_cover_glow_border()
        canvas.alpha_composite(glow_border, (COVER_X - 15, COVER_Y - 15))
        
        # Rounded cover
        cover_mask = Image.new("L", (COVER_SIZE, COVER_SIZE), 0)
        ImageDraw.Draw(cover_mask).rounded_rectangle(
            (0, 0, COVER_SIZE, COVER_SIZE), radius=22, fill=255
        )
        cover.putalpha(cover_mask)
        canvas.alpha_composite(cover, (COVER_X, COVER_Y))
        
        # ===== FONTS =====
        fonts = load_fonts()
        draw = ImageDraw.Draw(canvas)
        
        # ===== PROFILE PICTURE =====
        if user_id:
            profile_pic = await get_user_profile_pic(user_id)
            if profile_pic:
                badge = create_profile_badge(profile_pic)
                canvas.alpha_composite(badge, (RIGHT_START_X, NOW_PLAYING_Y - 60))
                now_playing_x = RIGHT_START_X + 110
            else:
                now_playing_x = RIGHT_START_X
        else:
            now_playing_x = RIGHT_START_X
        
        # ===== NOW PLAYING =====
        np_text = "◆ NOW PLAYING"
        
        # Glow
        for offset in range(3, 0, -1):
            draw.text(
                (now_playing_x - offset, NOW_PLAYING_Y - offset),
                np_text,
                font=fonts['now_playing'],
                fill=(*NEON_PURPLE_LIGHT, 40 - offset * 10)
            )
        
        draw.text(
            (now_playing_x, NOW_PLAYING_Y),
            np_text,
            font=fonts['now_playing'],
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SONG TITLE =====
        title_text = trim_text(title, fonts['title'], RIGHT_WIDTH)
        
        for offset in range(4, 0, -1):
            draw.text(
                (RIGHT_START_X - offset, TITLE_Y - offset),
                title_text,
                font=fonts['title'],
                fill=(*NEON_PURPLE, 35 - offset * 7)
            )
        
        draw.text(
            (RIGHT_START_X, TITLE_Y),
            title_text,
            font=fonts['title'],
            fill=WHITE
        )
        
        # ===== ARTIST =====
        artist_text = trim_text(f"🎙 {artist}", fonts['artist'], RIGHT_WIDTH - 20)
        
        draw.text(
            (RIGHT_START_X, ARTIST_Y),
            artist_text,
            font=fonts['artist'],
            fill=LIGHT_GRAY
        )
        
        # ===== PROGRESS BAR =====
        progress = create_progress_bar(RIGHT_WIDTH, 0.55, NEON_PURPLE)
        canvas.alpha_composite(progress, (RIGHT_START_X, PROGRESS_Y))
        
        # Duration
        dur_text = str(duration) if duration else "0:00"
        dur_bbox = fonts['small'].getbbox(dur_text)
        dur_width = dur_bbox[2] - dur_bbox[0]
        
        draw.text(
            (RIGHT_START_X + RIGHT_WIDTH - dur_width, PROGRESS_Y + 18),
            dur_text,
            font=fonts['small'],
            fill=(255, 255, 255, 200)
        )
        
        # ===== PLAY CONTROLS =====
        play_btn = create_play_button(70)
        prev_btn = create_nav_button(50, "prev")
        next_btn = create_nav_button(50, "next")
        
        # Center controls
        controls_width = 50 + 40 + 90 + 40 + 50  # prev + spacing + play + spacing + next
        controls_start_x = RIGHT_START_X + (RIGHT_WIDTH - controls_width) // 2
        
        prev_x = controls_start_x
        play_x = controls_start_x + 50 + 40
        next_x = controls_start_x + 50 + 40 + 90 + 40
        
        # Vertically center all buttons
        max_btn_height = 90
        controls_y_center = CONTROLS_Y
        
        canvas.alpha_composite(prev_btn, (prev_x, controls_y_center + (max_btn_height - 60) // 2))
        canvas.alpha_composite(play_btn, (play_x, controls_y_center + (max_btn_height - 90) // 2))
        canvas.alpha_composite(next_btn, (next_x, controls_y_center + (max_btn_height - 60) // 2))
        
        # ===== BOT NAME =====
        bot_name = getattr(app, 'name', 'RaspberryRhythm')
        
        # Status dot
        dot_y = BOT_NAME_Y
        draw.ellipse(
            (RIGHT_START_X + (RIGHT_WIDTH - len(bot_name) * 10) // 2 - 16, dot_y + 4,
             RIGHT_START_X + (RIGHT_WIDTH - len(bot_name) * 10) // 2 - 6, dot_y + 14),
            fill=(0, 255, 100, 230)
        )
        
        draw.text(
            (RIGHT_START_X + (RIGHT_WIDTH - len(bot_name) * 10) // 2, dot_y),
            f"⚡ {bot_name}",
            font=fonts['small'],
            fill=NEON_PURPLE_LIGHT
        )
        
        # ===== SIGNATURE =====
        signature = "✦ Made with 🤍 by @DivineDemonn ✦"
        sig_bbox = fonts['small'].getbbox(signature)
        sig_width = sig_bbox[2] - sig_bbox[0]
        sig_x = (CANVAS_SIZE[0] - sig_width) // 2
        
        # Clean white text - NO blur
        draw.text(
            (sig_x, SIGNATURE_Y),
            signature,
            font=fonts['small'],
            fill=(245, 245, 255, 230)
        )
        
        # ===== DECORATIVE LINES =====
        # Top line
        draw.line(
            [(30, 15), (CANVAS_SIZE[0] - 30, 15)],
            fill=(*NEON_PURPLE_LIGHT, 50),
            width=1
        )
        
        # Bottom line above signature
        draw.line(
            [(50, SIGNATURE_Y - 10), (CANVAS_SIZE[0] - 50, SIGNATURE_Y - 10)],
            fill=(*NEON_PURPLE, 35),
            width=1
        )
        
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
        
        # Cache management
        try:
            files = sorted(
                [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR) if f.endswith(('.png', '.jpg'))],
                key=os.path.getmtime, reverse=True
            )
            for old in files[15:]:
                os.remove(old)
        except:
            pass
        
        return cache_path
        
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        try:
            os.remove(thumb_file)
        except:
            pass
        return YOUTUBE_IMG_URL


# ================= SHADOW HELPER =================
def create_cover_shadow():
    """Create shadow for cover art"""
    shadow_size = COVER_SIZE + 40
    shadow = Image.new("RGBA", (shadow_size, shadow_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    
    draw.rounded_rectangle(
        (20, 20, COVER_SIZE + 20, COVER_SIZE + 20),
        radius=25,
        fill=(0, 0, 0, 180)
    )
    
    return shadow.filter(ImageFilter.GaussianBlur(30))
