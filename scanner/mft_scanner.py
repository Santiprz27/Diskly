"""MFT Scanner — high-performance NTFS disk indexer.

Primary mode   : USN Journal enumeration (FSCTL_ENUM_USN_DATA) for structure,
                 then os.stat for file sizes during path resolution.
                 Same enumeration technique as WizTree — extremely fast.
Fallback mode  : os.scandir recursive walk (any filesystem, no Admin needed)

Yields (path_parts: list[str], size: int, is_dir: bool) tuples.

Performance notes:
  - USN mode enumerates all file metadata in one pass (~100 ms for 500 K files)
  - FRNs are masked to 48 bits (lower 6 bytes) for consistent parent lookups
  - Path resolution uses iterative parent-chain (no recursion limit issues)
  - os.stat is called once per file after path is resolved (cached by OS)
"""

from __future__ import annotations

import os
import sys
import struct
import stat
import logging
from typing import Generator, Callable

log = logging.getLogger(__name__)

ScanEntry = tuple[list[str], int, bool]

# ─────────────────────────────────────────────────────────────────────────────
# Windows IOCTL constants
# ─────────────────────────────────────────────────────────────────────────────
_FSCTL_ENUM_USN_DATA      = 0x900B3
_FILE_ATTRIBUTE_DIRECTORY = 0x10
_FILE_ATTRIBUTE_REPARSE   = 0x400

# Mask to strip the 16-bit sequence number from an NTFS File Reference Number,
# leaving only the 48-bit MFT record number.
_FRN_MASK = 0x0000_FFFF_FFFF_FFFF


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — USN Journal enumeration
# Builds:  frn_map[masked_frn] = (masked_parent_frn, name, is_dir)
# ─────────────────────────────────────────────────────────────────────────────

def _usn_enumerate(
    h,
    progress_cb: Callable[[int], None] | None,
) -> dict[int, tuple[int, str, bool]]:
    """Enumerate all NTFS entries via USN Journal into a flat FRN map.

    CRITICAL: both the FRN key and parent_frn value are masked to 48 bits
    so that parent-chain lookups are consistent.

    Returns {masked_frn: (masked_parent_frn, name, is_dir)}.
    """
    import win32file

    ROOT_FRN = 5  # MFT record 5 is always the root directory
    # Pre-seed root so resolve() terminates at the root anchor
    frn_map: dict[int, tuple[int, str, bool]] = {
        ROOT_FRN: (0, "", True),
    }

    # MFT_ENUM_DATA_V0: StartFileReferenceNumber=0, LowUsn=0, HighUsn=max
    mft_enum  = struct.pack("<QQQ", 0, 0, 0x7FFF_FFFF_FFFF_FFFF)
    buf_size  = 512 * 1024  # 512 KB buffer per IOCTL call
    count     = 0
    last_prog = 0

    while True:
        try:
            buf = win32file.DeviceIoControl(
                h, _FSCTL_ENUM_USN_DATA, mft_enum, buf_size
            )
        except Exception:
            break

        if len(buf) < 8:
            break

        # First 8 bytes of the output = next StartFileReferenceNumber
        next_start = struct.unpack_from("<Q", buf, 0)[0]
        offset = 8

        while offset + 64 <= len(buf):
            rec_len = struct.unpack_from("<I", buf, offset)[0]
            if rec_len < 64:
                break

            raw_frn, raw_parent_frn, file_attrs, fname_len, fname_off = struct.unpack_from(
                "<QQ28xIHH", buf, offset + 8
            )

            # ── Mask both FRNs to 48 bits (strip sequence number) ──────────
            frn        = raw_frn        & _FRN_MASK
            parent_frn = raw_parent_frn & _FRN_MASK

            # Skip reparse points (junctions / symlinks — avoid traversal loops)
            if not (file_attrs & _FILE_ATTRIBUTE_REPARSE):
                is_dir   = bool(file_attrs & _FILE_ATTRIBUTE_DIRECTORY)
                name_end = offset + fname_off + fname_len

                if name_end <= len(buf):
                    name_bytes = buf[offset + fname_off : name_end]
                    try:
                        name = name_bytes.decode("utf-16-le")
                        # Skip NTFS system metadata files ($MFT, $Bitmap, …)
                        if name and not name.startswith("$") and frn not in frn_map:
                            frn_map[frn] = (parent_frn, name, is_dir)
                            count += 1
                    except Exception:
                        pass

            offset += rec_len

        if progress_cb and count - last_prog >= 50_000:
            progress_cb(count)
            last_prog = count

        # Stop when the journal wraps around to 0
        mft_enum = struct.pack("<QQQ", next_start, 0, 0x7FFF_FFFF_FFFF_FFFF)
        if next_start == 0:
            break

    log.info("USN enumeration complete: %d entries", count)
    return frn_map


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Iterative path resolution + lazy os.stat for sizes
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_and_yield(
    frn_map: dict[int, tuple[int, str, bool]],
    drive: str,
) -> Generator[ScanEntry, None, None]:
    """Resolve FRN parent-chains iteratively and yield ScanEntry tuples.

    Uses an iterative algorithm to avoid Python recursion limits on deep trees.
    File sizes are obtained via os.stat() — one call per file, OS-cached.
    """
    ROOT_FRN = 5
    root_prefix = f"{drive}:\\"

    # Cache: frn → resolved path parts list (None = unresolvable)
    path_cache: dict[int, list[str] | None] = {ROOT_FRN: []}

    def resolve_iterative(start_frn: int) -> list[str] | None:
        """Build path parts for start_frn using an explicit stack."""
        # Walk up the parent chain collecting FRNs until we hit a cached one
        chain: list[int] = []
        frn = start_frn

        while frn not in path_cache:
            entry = frn_map.get(frn)
            if entry is None:
                # Orphan — cannot resolve; cache as None to short-circuit next time
                path_cache[frn] = None
                return None
            chain.append(frn)
            parent_frn, _, _ = entry
            frn = parent_frn

        # frn is now a cached anchor
        base = path_cache[frn]

        # Walk back down the chain, building and caching path parts
        parts = base
        for ancestor_frn in reversed(chain):
            if parts is None:
                path_cache[ancestor_frn] = None
                parts = None
            else:
                _, name, _ = frn_map[ancestor_frn]
                parts = parts + [name]
                path_cache[ancestor_frn] = parts

        return path_cache[start_frn]

    failed_resolve = 0
    failed_stat    = 0

    for frn, (parent_frn, name, is_dir) in frn_map.items():
        if not name or frn == ROOT_FRN:
            continue

        parts = resolve_iterative(frn)
        if parts is None or not parts:
            failed_resolve += 1
            continue

        size = 0
        if not is_dir:
            try:
                full_path = root_prefix + "\\".join(parts)
                size = os.stat(full_path).st_size
            except OSError:
                failed_stat += 1

        yield parts, size, is_dir

    if failed_resolve or failed_stat:
        log.debug(
            "Path resolve: %d unresolvable, %d stat-failed",
            failed_resolve, failed_stat,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Public MFT fast-scan entry point
# ─────────────────────────────────────────────────────────────────────────────

def _mft_scan(
    drive: str,
    progress_cb: Callable[[int], None] | None = None,
) -> Generator[ScanEntry, None, None]:
    """Fast NTFS scan via USN Journal enumeration + path resolution.

    Yields (path_parts, size, is_dir) tuples identical to _scandir_scan.
    Requires Administrator privileges and an NTFS volume.
    """
    import win32file
    import time

    vol_path = f"\\\\.\\{drive}:"
    try:
        h = win32file.CreateFile(
            vol_path,
            0x8000_0000,  # GENERIC_READ
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
    except Exception as exc:
        log.warning("MFT scan: cannot open volume %s — %s", vol_path, exc)
        return

    try:
        t0      = time.perf_counter()
        frn_map = _usn_enumerate(h, progress_cb)
        log.info(
            "Phase 1 (USN enumerate) done in %.2fs — %d entries",
            time.perf_counter() - t0, len(frn_map),
        )
    finally:
        win32file.CloseHandle(h)

    # Phase 2: path resolution + lazy stat (generator — runs on first iteration)
    t1 = time.perf_counter()
    yield from _resolve_and_yield(frn_map, drive)
    log.info("Phase 2 (resolve + stat) done in %.2fs", time.perf_counter() - t1)


# ─────────────────────────────────────────────────────────────────────────────
# os.scandir fallback scanner (optimized)
# ─────────────────────────────────────────────────────────────────────────────

def _scandir_scan(
    root: str,
    progress_cb: Callable[[int], None] | None = None,
) -> Generator[ScanEntry, None, None]:
    """Optimized recursive os.scandir walk — any filesystem, no Admin needed."""
    root = os.path.abspath(root)
    prefix_len = len(root)
    if not root.endswith(os.sep):
        prefix_len += 1

    stack      = [root]
    count      = 0
    last_prog  = 0
    BATCH_SIZE = 5_000

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        st = entry.stat(follow_symlinks=False)
                    except (PermissionError, OSError):
                        continue

                    if stat.S_ISLNK(st.st_mode):
                        continue

                    full     = entry.path
                    relative = full[prefix_len:] if len(full) > prefix_len else entry.name
                    parts    = [p for p in relative.replace("\\", "/").split("/") if p]

                    is_dir = entry.is_dir(follow_symlinks=False)
                    size   = 0 if is_dir else st.st_size

                    if not is_dir and size == 0:
                        count += 1
                        continue

                    yield parts, size, is_dir

                    if is_dir:
                        stack.append(entry.path)

                    count += 1

            if progress_cb and count - last_prog >= BATCH_SIZE:
                progress_cb(count)
                last_prog = count

        except (PermissionError, OSError):
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def scan_drive(
    drive_letter: str,
    admin: bool = False,
    progress_cb: Callable[[int], None] | None = None,
) -> Generator[ScanEntry, None, None]:
    """Scan a drive and yield (path_parts, size, is_dir) tuples.

    Args:
        drive_letter: Single letter like 'C'.
        admin: Whether to attempt fast MFT/USN scan (NTFS + admin required).
        progress_cb: Optional callback receiving the running entry count.
    """
    drive_letter = drive_letter.upper().rstrip(":\\")

    if admin and sys.platform == "win32":
        log.info("Using fast MFT scanner for drive %s:\\", drive_letter)
        try:
            yield from _mft_scan(drive_letter, progress_cb)
            return
        except Exception as exc:
            log.warning("MFT fast scan failed: %s — falling back to scandir", exc)

    log.info("Using os.scandir for drive %s:\\", drive_letter)
    root_path = f"{drive_letter}:\\"
    yield from _scandir_scan(root_path, progress_cb)