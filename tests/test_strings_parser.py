import sys
import struct
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

def inspect_strings_file(file_path: Path):
    with open(file_path, "rb") as f:
        header = f.read(8)
        if len(header) < 8:
            return
        num_entries, data_size = struct.unpack("<II", header)
        print(f"\n--- {file_path.name} --- (Всего записей: {num_entries})")
        
        entries = []
        for _ in range(num_entries):
            entry_data = f.read(8)
            if len(entry_data) < 8:
                break
            sid, offset = struct.unpack("<II", entry_data)
            entries.append((sid, offset))
            
        data_start = 8 + num_entries * 8
        is_dl_or_il = file_path.suffix.lower() in [".dlstrings", ".ilstrings"]
        
        for sid, offset in entries[:5]:
            f.seek(data_start + offset)
            if is_dl_or_il:
                len_bytes = f.read(4)
                if len(len_bytes) == 4:
                    str_len = struct.unpack("<I", len_bytes)[0]
                    raw_str = f.read(str_len).rstrip(b"\x00")
                else:
                    raw_str = b""
            else:
                raw_str = b""
                while True:
                    ch = f.read(1)
                    if not ch or ch == b"\x00":
                        break
                    raw_str += ch
                    
            try:
                decoded = raw_str.decode("utf-8")
            except Exception:
                decoded = raw_str.decode("cp1251", errors="replace")
            print(f"  [ID: {sid:#010x}] {decoded[:60]}")

if __name__ == "__main__":
    for p in Path("data/Strings").glob("Skyrim_Russian.*"):
        inspect_strings_file(p)
