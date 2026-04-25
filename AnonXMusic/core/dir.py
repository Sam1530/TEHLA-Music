import os

from ..logging import LOGGER

# ✅ Define constants (IMPORTANT)
DOWNLOADS_DIR = "downloads"
CACHE_DIR = "cache"


def dirr():
    # Clean old images
    for file in os.listdir():
        if file.endswith((".jpg", ".jpeg", ".png")):
            try:
                os.remove(file)
            except Exception:
                pass

    # Create folders safely
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    LOGGER(__name__).info("Directories Updated.")
