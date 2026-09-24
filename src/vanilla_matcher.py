import struct
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
STRINGS_DIR = BASE_DIR / "data" / "Strings"
VANILLA_CACHE_FILE = BASE_DIR / "data" / "vanilla_dictionary.json"


class VanillaMatcher:
    """
    Модуль сопоставления с официальной русской локализацией Skyrim (Base Game + DLC).
    Парсит бинарные файлы .STRINGS, .DLSTRINGS, .ILSTRINGS и строит быстрый индекс
    для мгновенного применения официальных каноничных терминов (0 токенов).
    """

    def __init__(self, strings_dir: Optional[Path] = None):
        self.strings_dir = Path(strings_dir) if strings_dir else STRINGS_DIR
        # Словарь { string_id: russian_text }
        self.id_to_text: Dict[int, str] = {}
        # Словарь каноничных переводов { english_text: russian_text }
        self.dictionary: Dict[str, str] = {}
        self._load_vanilla_data()

    def _parse_strings_file(self, file_path: Path) -> Dict[int, str]:
        """Парсит один бинарный .STRINGS / .DLSTRINGS / .ILSTRINGS файл Bethesda."""
        results: Dict[int, str] = {}
        if not file_path.exists():
            return results

        try:
            with open(file_path, "rb") as f:
                header = f.read(8)
                if len(header) < 8:
                    return results
                num_entries, data_size = struct.unpack("<II", header)

                directory_bytes = f.read(num_entries * 8)
                if len(directory_bytes) < num_entries * 8:
                    return results

                entries: List[Tuple[int, int]] = []
                for i in range(num_entries):
                    sid, offset = struct.unpack_from("<II", directory_bytes, i * 8)
                    entries.append((sid, offset))

                data_start = 8 + num_entries * 8
                is_length_prefixed = file_path.suffix.lower() in [".dlstrings", ".ilstrings"]

                for sid, offset in entries:
                    f.seek(data_start + offset)
                    if is_length_prefixed:
                        len_bytes = f.read(4)
                        if len(len_bytes) == 4:
                            str_len = struct.unpack("<I", len_bytes)[0]
                            raw_bytes = f.read(str_len).rstrip(b"\x00")
                        else:
                            raw_bytes = b""
                    else:
                        chars = []
                        while True:
                            ch = f.read(1)
                            if not ch or ch == b"\x00":
                                break
                            chars.append(ch)
                        raw_bytes = b"".join(chars)

                    if "russian" in file_path.name.lower():
                        try:
                            decoded = raw_bytes.decode("cp1251")
                        except Exception:
                            decoded = raw_bytes.decode("utf-8", errors="replace")
                    else:
                        try:
                            decoded = raw_bytes.decode("utf-8")
                        except UnicodeDecodeError:
                            decoded = raw_bytes.decode("cp1251", errors="replace")

                    if decoded:
                        results[sid] = decoded
        except Exception as e:
            print(f"⚠️ Ошибка при парсинге {file_path.name}: {e}")

        return results

    def _load_vanilla_data(self):
        """Загружает все официальные strings-файлы и кэш словаря."""
        if VANILLA_CACHE_FILE.exists():
            try:
                with open(VANILLA_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.dictionary = json.load(f)
            except Exception:
                self.dictionary = {}

        # Загружаем официальные файлы русской локализации
        files = list(self.strings_dir.glob("*_Russian.*"))
        for p in files:
            file_strings = self._parse_strings_file(p)
            self.id_to_text.update(file_strings)

    def match(self, text: str) -> Optional[str]:
        """
        Проверяет наличие каноничного перевода для английской строки.
        Возвращает официальный русский перевод или None.
        """
        if not text:
            return None
        clean = text.strip()
        return self.dictionary.get(clean)

    def add_canonical_pair(self, english: str, russian: str):
        """Добавляет проверенную каноничную пару терминов в ванильный словарь."""
        if english and russian:
            self.dictionary[english.strip()] = russian.strip()

    def save_dictionary(self):
        """Сохраняет ванильный словарь соответствий на диск."""
        with open(VANILLA_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.dictionary, f, ensure_ascii=False, indent=2)
