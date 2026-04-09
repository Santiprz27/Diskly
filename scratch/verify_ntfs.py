import struct
import win32file
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("NTFS_Verify")

def verify_ntfs(drive_letter):
    drive_letter = drive_letter.upper().rstrip(":\\")
    vol_path = f"\\\\.\\{drive_letter}:"
    
    try:
        h = win32file.CreateFile(
            vol_path,
            0x80000000, # GENERIC_READ
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
    except Exception as exc:
        print(f"FAILED to open volume: {exc}")
        return

    # FSCTL_GET_NTFS_VOLUME_DATA
    FSCTL_GET_NTFS_VOLUME_DATA = 0x90064
    try:
        # Buffer of 256 bytes to be safe
        result = win32file.DeviceIoControl(h, FSCTL_GET_NTFS_VOLUME_DATA, None, 256)
        
        print(f"\n--- NTFS VOLUME DATA ({drive_letter}:) ---")
        print(f"Buffer size returned: {len(result)} bytes")
        
        # Reference offsets from MS docs
        bytes_per_sector = struct.unpack_from("<I", result, 40)[0]
        bytes_per_cluster = struct.unpack_from("<I", result, 44)[0]
        record_size = struct.unpack_from("<I", result, 48)[0]
        mft_start_lcn = struct.unpack_from("<Q", result, 64)[0]
        mft_2_lcn = struct.unpack_from("<Q", result, 72)[0]
        
        print(f"Bytes Per Sector : {bytes_per_sector}")
        print(f"Bytes Per Cluster: {bytes_per_cluster}")
        print(f"Record Size      : {record_size} (Should be 1024)")
        print(f"MFT Start LCN    : {mft_start_lcn}")
        print(f"MFT 2 LCN        : {mft_2_lcn}")
        
        # Calculate MFT Offset
        mft_offset = mft_start_lcn * bytes_per_cluster
        print(f"MFT Byte Offset  : {mft_offset}")
        
        # Try to read the first 4 bytes of MFT
        win32file.SetFilePointer(h, mft_offset, win32file.FILE_BEGIN)
        hr, data = win32file.ReadFile(h, 4)
        print(f"MFT Header Sig   : {data} (Should be b'FILE')")
        
    except Exception as exc:
        print(f"FAILED to get NTFS data or read MFT: {exc}")
    finally:
        win32file.CloseHandle(h)

if __name__ == "__main__":
    verify_ntfs("C")
