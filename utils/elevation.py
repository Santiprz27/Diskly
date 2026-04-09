"""Windows UAC elevation helpers."""

import ctypes
import sys
import os


def is_admin() -> bool:
    """Return True if the current process has Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_elevation() -> None:
    """Re-launch this script with Administrator privileges via UAC prompt.
    
    The current process exits immediately after requesting elevation.
    """
    executable = sys.executable
    script = os.path.abspath(sys.argv[0])
    params = " ".join([f'"{a}"' for a in sys.argv[1:]])
    # ShellExecuteW with "runas" triggers the UAC prompt
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, f'"{script}" {params}', None, 1
    )
    # ret <= 32 indicates failure
    if ret <= 32:
        # User declined or error – fall back silently
        pass
    sys.exit(0)
