"""Color Map logic for the Treemap rendering.

Maps file extensions and types to specific QColor objects.
Colors are based on the Space Black / Neon Coral theme.
"""

from PyQt6.QtGui import QColor

# ── Base Tokens ──
BG_PRIMARY = QColor("#121313")
DIR_COLOR = QColor("#222425")          # Darker grey for pure directories
DIR_BORDER = QColor("#3a3c3c")
TEXT_PRIMARY = QColor("#e8e8e8")
TEXT_MUTED = QColor("#a0a0a0")

# ── Extension Colors ──
# We use a curated palette that matches the dark theme

_EXT_MAP = {
    # Video (Neon Coral variations)
    ".mp4": QColor("#ff6044"),
    ".mkv": QColor("#ff7a5c"),
    ".avi": QColor("#e84d33"),
    ".mov": QColor("#cc4e36"),
    ".wmv": QColor("#ff9070"),
    ".flv": QColor("#d44433"),
    ".webm": QColor("#ff5038"),
    
    # Audio (Amber / Peach)
    ".mp3": QColor("#e0a96d"),
    ".wav": QColor("#cba37b"),
    ".flac": QColor("#d29e64"),
    ".m4a": QColor("#bea88d"),
    ".ogg": QColor("#daaf85"),
    
    # Images (Cyan / Teal)
    ".jpg": QColor("#4db8ff"),
    ".jpeg": QColor("#4db8ff"),
    ".png": QColor("#74c0fc"),
    ".gif": QColor("#339af0"),
    ".webp": QColor("#a5d8ff"),
    ".svg": QColor("#228be6"),
    ".bmp": QColor("#1c7ed6"),
    
    # Archives (Purple / Violet)
    ".zip": QColor("#9775fa"),
    ".rar": QColor("#845ef7"),
    ".7z": QColor("#7950f2"),
    ".tar": QColor("#b197fc"),
    ".gz": QColor("#6741d9"),
    ".pkg": QColor("#5f3dc4"),
    
    # Documents / Code (Green / Mint)
    ".pdf": QColor("#ff8787"),
    ".doc": QColor("#38d9a9"),
    ".docx": QColor("#20c997"),
    ".xls": QColor("#12b886"),
    ".xlsx": QColor("#0ca678"),
    ".txt": QColor("#c3fae8"),
    ".py": QColor("#ffd43b"),
    ".js": QColor("#fcc419"),
    ".json": QColor("#fab005"),
    ".html": QColor("#ff922b"),
    
    # System / Binaries (Cool Greys)
    ".exe": QColor("#5c5f61"),
    ".sys": QColor("#3f4040"),
    ".dll": QColor("#484a4a"),
    ".tmp": QColor("#2a2b2b"),
    ".pak": QColor("#6c7072"),
    ".bin": QColor("#555859"),
    ".msi": QColor("#6e7375"),
    ".iso": QColor("#3b3d3d"),
}

# Default color for unknown files (no extension)
FILE_DEFAULT = QColor("#464d52")

# Vibrant palette for unknown extensions so they never look dull
_VIBRANT_PALETTE = [
    "#ff6044", "#38d9a9", "#4db8ff", "#9775fa", 
    "#fcc419", "#ff8787", "#20c997", "#339af0",
    "#845ef7", "#fab005", "#ff922b", "#228be6",
    "#12b886", "#f06595", "#cc5de8", "#fd7e14"
]

import hashlib

def get_color_for_file(filename: str, is_dir: bool, depth: int = 0) -> QColor:
    """Return the QColor for a given filename."""
    if is_dir:
        # Base dir color, lighten slightly recursively based on depth
        c = QColor("#1e2022")
        factor = 100 + min(depth * 10, 80)
        return c.lighter(factor)
    
    ext_idx = filename.rfind(".")
    if ext_idx == -1:
        return FILE_DEFAULT
        
    ext = filename[ext_idx:].lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]
        
    # Hash the extension to consistently pick a vibrant color
    h = int(hashlib.md5(ext.encode()).hexdigest(), 16)
    idx = h % len(_VIBRANT_PALETTE)
    return QColor(_VIBRANT_PALETTE[idx])
