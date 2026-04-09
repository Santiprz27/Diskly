# -*- coding: utf-8 -*-
"""Quick smoke-test: run the MFT scanner and report key metrics.
Run this script as Administrator to exercise the fast path.
"""
import sys
import io
import time
import logging

# Force UTF-8 output on Windows console to avoid cp1252 issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# Make sure the project root is on sys.path
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.elevation import is_admin
from scanner.mft_scanner import scan_drive
from scanner.dir_trie import DirNode


def test_scan(drive: str = "C") -> None:
    admin = is_admin()
    print(f"\n{'='*60}")
    print(f"  Diskly MFT Scanner — smoke test")
    print(f"  Drive  : {drive}:\\")
    print(f"  Admin  : {admin}")
    print(f"{'='*60}\n")

    if not admin:
        print("[!] NOT running as Administrator -- fast path will not be used!")
        print("    Re-run this script with 'Run as Administrator'.\n")

    root    = DirNode(name=f"{drive}:\\")
    count   = 0
    files   = 0
    dirs    = 0
    t0      = time.perf_counter()

    def on_progress(n: int) -> None:
        elapsed = time.perf_counter() - t0
        print(f"  … {n:>8,} entries  |  {elapsed:5.1f}s elapsed", end="\r")

    for i, (parts, size, is_dir) in enumerate(
        scan_drive(drive, admin=admin, progress_cb=on_progress)
    ):
        if i < 5:
            print(f"  [{i}] {'DIR ' if is_dir else 'FILE'} {'/'.join(parts)!r:60s} {size:>12,} B")
        if parts:
            root.insert(parts, size, is_dir)
        count += 1
        if is_dir:
            dirs += 1
        else:
            files += 1

    elapsed = time.perf_counter() - t0
    root.accumulate()

    print(f"\n\n{'─'*60}")
    print(f"  Total entries : {count:>10,}")
    print(f"  Files         : {files:>10,}")
    print(f"  Dirs          : {dirs:>10,}")
    print(f"  Root size     : {root.total_size / (1024**3):>10.2f} GB")
    print(f"  Root children : {len(root.children):>10,}")
    print(f"  Elapsed       : {elapsed:>10.2f} s")
    print(f"{'─'*60}\n")

    if count == 0:
        print("[FAIL] No entries returned! Check logs above for errors.")
    elif root.total_size == 0:
        print("[FAIL] Tree built but total_size is 0! Size lookup failed.")
    else:
        print("[PASS] Scan looks correct.")


if __name__ == "__main__":
    drive = sys.argv[1].upper().rstrip(":\\") if len(sys.argv) > 1 else "C"
    test_scan(drive)
