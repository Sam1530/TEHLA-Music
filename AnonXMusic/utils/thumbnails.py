import os
import re
import aiofiles
import aiohttp
from PIL import (
    Image, ImageDraw, ImageEnhance,
    ImageFilter, ImageFont, ImageOps
)
from ytSearch import VideosSearch
import math
import random

from config import YOUTUBE_IMG_URL
from AnonXMusic.core.dir import CACHE_DIR

# ================= BASIC =================
os.makedirs(CACHE_DIR, exist_ok=True)
CANVAS_SIZE = (1280, 720)

# ================= MODERN SPOTIFY LAYOUT =================
# Album cover (left side)
COVER_SIZE = 420
COVER_X = 80
COVER_Y = (720 - COVER_SIZE) // 2

# Right side content
RIGHT_START_X = COVER_X + COVER_SIZE + 60
RIGHT_WIDTH = 640

# Text positions
NOW_PLAYING_Y = 220
TITLE_Y = NOW_PLAYING_Y + 50
ARTIST_Y = TITLE_Y + 70
WAVELINE_Y = ARTIST_Y + 45
CONTROLS_Y = WAVELINE_Y + 80

# ================= CONTROL ICONS POSITIONING (FIXED) =================
CONTROLS_CENTER_X = RIGHT_START_X + (RIGHT_WIDTH // 2) - 20
PLAY_BTN_SIZE = 80
SMALL_ICON_SIZE = 36
ICON_SPACING = 70

# Calculate precise icon positions
SHUFFLE_X = CONTROLS_CENTER_X - (ICON_SPACING * 2) - (PLAY_BTN_SIZE // 2)
PREV_X = CONTROLS_CENTER_X - ICON_SPACING - (PLAY_BTN_SIZE // 2)
PLAY_X = CONTROLS_CENTER_X - (PLAY_BTN_SIZE // 2)
NEXT_X = CONTROLS_CENTER_X + ICON_SPACING - (SMALL_ICON_SIZE // 2)
REPEAT_X = CONTROLS_CENTER_X + (ICON_SPACING * 2) - (SMALL_ICON_SIZE // 2)

# Icon vertical alignment (center all icons)
ICON_CENTER_Y = CONTROLS_Y + (PLAY_BTN_SIZE // 2) - (SMALL_ICON_SIZE // 2)

# ================= NEON PINK COLOR SCHEME =================
DARK_BG = (10, 5, 15)           # Dark purple-black background
NEON_PINK = (255, 20, 147)      # #FF1493 - Deep Pink
NEON_PINK_LIGHT = (255, 110, 180)  # Lighter pink for gradients
NEON_PINK_GLOW = (255, 20, 147, 100)  # Glow effect pink
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (80, 80, 80)
SOFT_PINK = (255, 182, 193)      # #FFB6C1 - Light pink for accents

# ================= MODERN EFFECTS =================
def create_vignette(size, intensity=150):
    """Create soft vignette effect"""
    vignette = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    
    for i in range(intensity):
        alpha = int(100 * (1 - i/intensity))
        draw.rectangle(
            [i, i, size[0]-i, size[1]-i],
            outline=(0, 0, 0, alpha)
        )
    
    return vignette.filter(ImageFilter.GaussianBlur(20))

def create_glow_effect(size, color, radius=50, intensity=30):
    """Create soft glow effect"""
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    
    center_x, center_y = size[0]//2, size[1]//2
    for i in range(radius, 0, -5):
        alpha = intensity * (i/radius)
        draw.ellipse(
            (center_x-i, center_y-i, center_x+i, center_y+i),
            fill=(color[0], color[1], color[2], int(alpha))
        )
    
    return glow.filter(ImageFilter.GaussianBlur(20))

def create_sound_wave(width, height, color=NEON_PINK):
    """Create stylish glowing sound wave line"""
    wave = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wave)
    
    # Create wave pattern with more dynamic movement
    points = []
    for x in range(0, width, 3):
        y = height//2 + int(20 * math.sin(x * 0.03)) + int(10 * math.sin(x * 0.01))
        points.append((x, y))
    
    # Draw main wave line with gradient
    if len(points) > 1:
        # Main line
        draw.line(points, fill=color, width=4)
        
        # Add glow effects
        for offset in [2, 4, 6, 8]:
            glow_points = [(x, y + offset) for x, y in points]
            draw.line(glow_points, fill=(color[0], color[1], color[2], 60 - offset*5), width=3)
            glow_points = [(x, y - offset) for x, y in points]
            draw.line(glow_points, fill=(color[0], color[1], color[2], 60 - offset*5), width=3)
    
    return wave

def create_equalizer_bars(size, color=NEON_PINK):
    """Create animated-style equalizer bars"""
    eq = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(eq)
    
    bar_width = 8
    spacing = 6
    x_start = 0
    
    # Create dynamic bar heights
    heights = [18, 32, 24, 38, 28, 20, 35, 25, 30, 22]
    
    for i, h in enumerate(heights):
        x = x_start + i * (bar_width + spacing)
        y = size[1] - h
        
        # Draw bar with gradient effect
        for j in range(bar_width):
            alpha = 220 - j * 15
            draw.rectangle(
                [x + j, y, x + j + 1, size[1]],
                fill=(color[0], color[1], color[2], alpha)
            )
        
        # Add glow
        draw.rectangle(
            [x-2, y-2, x+bar_width+2, size[1]+2],
            fill=(color[0], color[1], color[2], 15),
            outline=None
        )
    
    return eq

def create_floating_notes(size):
    """Create floating music notes decoration"""
    notes = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(notes)
    
    note_symbols = ["♪", "♫", "♬", "♩", "♭", "♮"]
    positions = [
        (200, 100), (950, 150), (150, 600), (1100, 500),
        (300, 650), (800, 80), (500, 120), (1000, 650),
        (50, 300), (1200, 200), (400, 400), (700, 550)
    ]
    
    try:
        font = ImageFont.truetype("AnonXMusic/assets/Montserrat-Light.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    for i, (x, y) in enumerate(positions):
        symbol = note_symbols[i % len(note_symbols)]
        alpha = random.randint(10, 30)
        draw.text(
            (x, y),
            symbol,
            font=font,
            fill=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], alpha)
        )
    
    return notes

def create_glossy_overlay(size, radius=30):
    """Create glossy finish overlay for album art"""
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Create glossy highlight
    for i in range(size[0]):
        gradient = int(50 * (1 - i/size[0]))
        draw.line(
            [(i, 0), (i, size[1]//3)],
            fill=(255, 255, 255, gradient//3)
        )
    
    return overlay.filter(ImageFilter.GaussianBlur(5))

def create_glassmorphism_panel(size, radius=20):
    """Create glass morphism effect panel"""
    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(panel)
    
    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius,
        fill=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], 5)
    )
    
    # Add border
    draw.rounded_rectangle(
        (0, 0, size[0], size[1]),
        radius,
        outline=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], 20),
        width=1
    )
    
    return panel

def trim_text(text, font, max_width):
    if font.getlength(text) <= max_width:
        return text
    while font.getlength(text + "…") > max_width:
        text = text[:-1]
    return text + "…"

def apply_rounded_corners(image, radius):
    """Apply rounded corners to image"""
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, image.size[0], image.size[1]),
        radius,
        fill=255
    )
    
    result = Image.new("RGBA", image.size, (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result

def create_control_icon(icon_type, size, active=False, is_play=False):
    """Create modern control icons with neon pink theme"""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    
    if is_play:
        # Play button with neon pink circle
        center = size // 2
        radius = size // 3
        
        # Outer glow layers
        for i in range(20, 0, -4):
            glow_radius = radius + i
            alpha = 40 - i
            draw.ellipse(
                (center - glow_radius, center - glow_radius,
                 center + glow_radius, center + glow_radius),
                fill=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], alpha)
            )
        
        # Main circle
        draw.ellipse(
            (center - radius, center - radius,
             center + radius, center + radius),
            fill=NEON_PINK
        )
        
        # Inner glow
        draw.ellipse(
            (center - radius + 2, center - radius + 2,
             center + radius - 2, center + radius - 2),
            outline=(255, 255, 255, 100),
            width=2
        )
        
        # Play triangle (perfectly centered)
        triangle_size = radius - 5
        points = [
            (center - triangle_size//2, center - triangle_size//2),
            (center - triangle_size//2, center + triangle_size//2),
            (center + triangle_size//2 + 3, center)
        ]
        draw.polygon(points, fill=WHITE)
        
    else:
        color = NEON_PINK if active else DARK_GRAY
        center = size // 2
        small = size // 4
        
        if icon_type == "shuffle":
            # Shuffle icon
            draw.line((small, size-small, size-small, small), fill=color, width=3)
            draw.ellipse((0, 0, small*2, small*2), outline=color, width=3)
            draw.ellipse((size-small*2, size-small*2, size, size), outline=color, width=3)
        
        elif icon_type == "previous":
            # Previous icon
            draw.polygon(
                [(small, center), (size-small, small), (size-small, size-small)],
                fill=color
            )
            draw.rectangle((small-6, small, small-3, size-small), fill=color)
        
        elif icon_type == "next":
            # Next icon
            draw.polygon(
                [(size-small, center), (small, small), (small, size-small)],
                fill=color
            )
            draw.rectangle((size-small+3, small, size-small+6, size-small), fill=color)
        
        elif icon_type == "repeat":
            # Repeat icon
            draw.arc((small, small, size-small, size-small), 0, 360, fill=color, width=3)
            draw.polygon([(size-small*2, small), (size, small), (size-small, size//3)], 
                        fill=color)
    
    return icon

# ================= MAIN FUNCTION =================
async def get_thumb(videoid: str) -> str:
    cache = os.path.join(CACHE_DIR, f"{videoid}_modern.png")
    if os.path.exists(cache):
        return cache

    # ---------- FETCH YOUTUBE DATA ----------
    try:
        vs = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
        data = (await vs.next())["result"][0]

        title = re.sub(r"\s+", " ", data["title"]).strip()
        artist = data["channel"]["name"]
        duration = data.get("duration") or "LIVE"
        thumb_url = data["thumbnails"][-1]["url"].split("?")[0]
    except Exception:
        return YOUTUBE_IMG_URL

    # ---------- DOWNLOAD THUMBNAIL ----------
    thumb_file = os.path.join(CACHE_DIR, f"{videoid}.jpg")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(thumb_url, timeout=6) as r:
                async with aiofiles.open(thumb_file, "wb") as f:
                    await f.write(await r.read())
    except Exception:
        return YOUTUBE_IMG_URL

    # Load album art
    album_art = Image.open(thumb_file).convert("RGBA")
    
    # ---------- CREATE GRADIENT BACKGROUND ----------
    background = Image.new("RGBA", CANVAS_SIZE, DARK_BG)
    draw_bg = ImageDraw.Draw(background)
    
    # Create smooth neon pink gradient
    for y in range(CANVAS_SIZE[1]):
        ratio = y / CANVAS_SIZE[1]
        r = int(DARK_BG[0] * (1 - ratio) + NEON_PINK[0] * ratio * 0.3)
        g = int(DARK_BG[1] * (1 - ratio) + NEON_PINK[1] * ratio * 0.3)
        b = int(DARK_BG[2] * (1 - ratio) + NEON_PINK[2] * ratio * 0.3)
        draw_bg.line([(0, y), (CANVAS_SIZE[0], y)], fill=(r, g, b, 255))
    
    # Add vignette
    vignette = create_vignette(CANVAS_SIZE)
    background = Image.alpha_composite(background, vignette)
    
    # Add subtle pink glow
    glow = create_glow_effect(CANVAS_SIZE, NEON_PINK, 300, 20)
    background = Image.alpha_composite(background, glow)
    
    canvas = Image.new("RGBA", CANVAS_SIZE)
    canvas.paste(background, (0, 0))
    
    # ---------- ALBUM COVER (LEFT SIDE) ----------
    # Resize and enhance album art
    cover = album_art.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
    
    # Enhance contrast and color
    enhancer = ImageEnhance.Contrast(cover)
    cover = enhancer.enhance(1.2)
    enhancer = ImageEnhance.Color(cover)
    cover = enhancer.enhance(1.15)
    
    # Apply rounded corners
    cover = apply_rounded_corners(cover, 30)
    
    # Add glossy overlay
    glossy = create_glossy_overlay((COVER_SIZE, COVER_SIZE))
    cover = Image.alpha_composite(cover, glossy)
    
    # Add drop shadow
    shadow = Image.new("RGBA", (COVER_SIZE + 20, COVER_SIZE + 20), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (10, 10, COVER_SIZE + 10, COVER_SIZE + 10),
        40,
        fill=(0, 0, 0, 150)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    canvas.alpha_composite(shadow, (COVER_X - 10, COVER_Y - 10))
    
    # Place album cover
    canvas.alpha_composite(cover, (COVER_X, COVER_Y))
    
    # Add neon pink glow behind album
    cover_glow = create_glow_effect((COVER_SIZE + 60, COVER_SIZE + 60), NEON_PINK, 70, 15)
    canvas.alpha_composite(cover_glow, (COVER_X - 30, COVER_Y - 30))
    
    # ---------- LOAD FONTS ----------
    try:
        now_playing_font = ImageFont.truetype("AnonXMusic/assets/Montserrat-Light.ttf", 24)
        title_font = ImageFont.truetype("AnonXMusic/assets/Montserrat-Bold.ttf", 58)
        artist_font = ImageFont.truetype("AnonXMusic/assets/Montserrat-Medium.ttf", 32)
        small_font = ImageFont.truetype("AnonXMusic/assets/Montserrat-Light.ttf", 18)
    except:
        try:
            now_playing_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 24)
            title_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 58)
            artist_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 32)
            small_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 18)
        except:
            now_playing_font = title_font = artist_font = small_font = ImageFont.load_default()
    
    draw = ImageDraw.Draw(canvas)
    
    # ---------- "NOW PLAYING" TEXT ----------
    now_playing = "NOW PLAYING"
    x_pos = RIGHT_START_X
    letter_spacing = 3
    
    for char in now_playing:
        # Add glow effect
        for offset in [1, 2, 3]:
            draw.text((x_pos, NOW_PLAYING_Y - offset), char, font=now_playing_font, 
                     fill=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], 50))
        draw.text((x_pos, NOW_PLAYING_Y), char, font=now_playing_font, fill=NEON_PINK)
        char_bbox = draw.textbbox((0, 0), char, font=now_playing_font)
        char_width = char_bbox[2] - char_bbox[0]
        x_pos += char_width + letter_spacing
    
    # ---------- SONG TITLE (UPDATED - NORMAL TEXT FORMAT) ----------
    title_text = trim_text(title, title_font, RIGHT_WIDTH - 40)
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = RIGHT_START_X + (RIGHT_WIDTH - title_width) // 2
    
    # Draw title as normal white text without 3D glow effect
    draw.text(
        (title_x, TITLE_Y),
        title_text,
        font=title_font,
        fill=WHITE
    )
    
    # ---------- ARTIST NAME ----------
    artist_text = trim_text(artist, artist_font, RIGHT_WIDTH - 40)
    artist_bbox = draw.textbbox((0, 0), artist_text, font=artist_font)
    artist_width = artist_bbox[2] - artist_bbox[0]
    artist_x = RIGHT_START_X + (RIGHT_WIDTH - artist_width) // 2
    draw.text(
        (artist_x, ARTIST_Y),
        artist_text,
        font=artist_font,
        fill=LIGHT_GRAY
    )
    
    # ---------- SOUND WAVE LINE ----------
    wave = create_sound_wave(RIGHT_WIDTH - 40, 40)
    canvas.alpha_composite(wave, (RIGHT_START_X + 20, WAVELINE_Y))
    
    # ---------- CONTROL ICONS (FIXED POSITIONS) ----------
    # Shuffle (inactive)
    shuffle = create_control_icon("shuffle", SMALL_ICON_SIZE, False)
    canvas.alpha_composite(shuffle, (int(SHUFFLE_X), int(ICON_CENTER_Y)))
    
    # Previous (active)
    previous = create_control_icon("previous", SMALL_ICON_SIZE, True)
    canvas.alpha_composite(previous, (int(PREV_X), int(ICON_CENTER_Y)))
    
    # Play button (with neon pink glow)
    play_btn = create_control_icon("play", PLAY_BTN_SIZE, False, True)
    canvas.alpha_composite(play_btn, (int(PLAY_X), int(CONTROLS_Y)))
    
    # Next (active)
    next_icon = create_control_icon("next", SMALL_ICON_SIZE, True)
    canvas.alpha_composite(next_icon, (int(NEXT_X), int(ICON_CENTER_Y)))
    
    # Repeat (inactive)
    repeat = create_control_icon("repeat", SMALL_ICON_SIZE, False)
    canvas.alpha_composite(repeat, (int(REPEAT_X), int(ICON_CENTER_Y)))
    
    # Add small connecting line under controls
    line_y = CONTROLS_Y + PLAY_BTN_SIZE + 10
    line_start = SHUFFLE_X - 10
    line_end = REPEAT_X + SMALL_ICON_SIZE + 10
    draw.line(
        [(line_start, line_y), (line_end, line_y)],
        fill=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], 30),
        width=1
    )
    
    # ---------- EQUALIZER BARS ----------
    eq = create_equalizer_bars((120, 50))
    canvas.alpha_composite(eq, (1100, 650))
    
    # ---------- FLOATING MUSIC NOTES ----------
    notes = create_floating_notes(CANVAS_SIZE)
    canvas.alpha_composite(notes, (0, 0))
    
    # ---------- ADD GLASSMORPHISM PANEL ----------
    glass_panel = create_glassmorphism_panel((RIGHT_WIDTH + 40, 320))
    canvas.alpha_composite(glass_panel, (RIGHT_START_X - 20, NOW_PLAYING_Y - 20))
    
    # ---------- ADD CINEMATIC LIGHTING ----------
    # Add radial light effect
    radial_light = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw_radial = ImageDraw.Draw(radial_light)
    center_x, center_y = CANVAS_SIZE[0]//2, CANVAS_SIZE[1]//2
    
    for i in range(400, 0, -40):
        alpha = 8
        draw_radial.ellipse(
            (center_x-i, center_y-i, center_x+i, center_y+i),
            outline=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], alpha),
            width=1
        )
    
    canvas = Image.alpha_composite(canvas, radial_light)
    
    # ---------- ADD FINE DETAILS ----------
    # Add subtle grain
    grain = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw_grain = ImageDraw.Draw(grain)
    for _ in range(3000):
        x = random.randint(0, CANVAS_SIZE[0])
        y = random.randint(0, CANVAS_SIZE[1])
        alpha = random.randint(0, 2)
        draw_grain.point((x, y), fill=(255, 255, 255, alpha))
    canvas = Image.alpha_composite(canvas, grain)
    
    # Add small sparkling effect
    sparkle = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw_sparkle = ImageDraw.Draw(sparkle)
    for _ in range(50):
        x = random.randint(0, CANVAS_SIZE[0])
        y = random.randint(0, CANVAS_SIZE[1])
        size = random.randint(1, 3)
        alpha = random.randint(30, 70)
        draw_sparkle.ellipse(
            (x, y, x+size, y+size),
            fill=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], alpha)
        )
    canvas = Image.alpha_composite(canvas, sparkle)
    
    # ---------- SIGNATURE ----------
    try:
        sig_font = ImageFont.truetype("AnonXMusic/assets/Montserrat-Light.ttf", 14)
    except:
        sig_font = ImageFont.load_default()
    
    draw.text(
        (40, 690),
        "Dev: @DivineDemonn • Neon Pink Edition",
        font=sig_font,
        fill=(NEON_PINK[0], NEON_PINK[1], NEON_PINK[2], 180)
    )
    
    # ---------- SAVE ----------
    canvas.save(cache, quality=100, optimize=False, dpi=(300, 300))
    
    # ---------- CLEANUP ----------
    album_art.close()
    background.close()
    canvas.close()
    
    try:
        os.remove(thumb_file)
    except:
        pass
    
    # ---------- CACHE LIMIT ----------
    files = sorted(
        [os.path.join(CACHE_DIR, f) for f in os.listdir(CACHE_DIR)],
        key=os.path.getmtime
    )
    for f in files[:-15]:
        try:
            os.remove(f)
        except:
            pass
    
    return cache
