"""Human-readable byte size formatter."""


def format_bytes(n: int) -> str:
    """Convert a byte count to a human-readable string (e.g. '4.2 GB')."""
    if n < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024.0:
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} EB"


def format_count(n: int) -> str:
    """Format a file/folder count with thousand separators."""
    return f"{n:,}"
