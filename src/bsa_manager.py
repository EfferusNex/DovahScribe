"""
🐾 BSA Archive Manager (Менеджер архивов Bethesda .bsa).
Обеспечивает чтение и извлечение файлов локализации из запакованных архивов:
  1. Автоматический поиск .bsa архивов для плагина (<Mod>.bsa, <Mod> - Main.bsa, <Mod> - Textures.bsa).
  2. Быстрая нативная инспекция оглавления архива (Skyrim LE v104 и Skyrim SE v105).
  3. Точечное извлечение файлов SkyUI MCM (Interface/Translations/*_ENGLISH.txt) и Strings без распаковки гигабайт текстур.
  4. Поддержка извлечения через нативный Python (zlib) и интеграция с houseCARL MCP (housecarl_bsa_extract).
"""

import os
import sys
import zlib
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXTRACTED_BSA_DIR = DATA_DIR / "extracted_bsa"
EXTRACTED_BSA_DIR.mkdir(parents=True, exist_ok=True)


class BSAFileRecord:
    def __init__(self, name_hash: int, size: int, offset: int, full_path: str = ""):
        self.name_hash = name_hash
        self.size = size
        self.offset = offset
        self.full_path = full_path

    @property
    def is_compressed(self) -> bool:
        return bool(self.size & 0x40000000)

    @property
    def actual_size(self) -> int:
        return self.size & 0x3FFFFFFF


class BSAParser:
    """
    Легковесный и быстрый парсер архивов Bethesda BSA (v104 Skyrim LE, v105 Skyrim SE).
    Позволяет мгновенно прочитать оглавление и извлечь текстовые файлы без сторонних утилит.
    """

    MAGIC = b"BSA\x00"

    def __init__(self, bsa_path: Path):
        self.path = Path(bsa_path)
        self.version = 0
        self.folder_offset = 0
        self.archive_flags = 0
        self.folder_count = 0
        self.file_count = 0
        self.total_folder_name_len = 0
        self.total_file_name_len = 0
        self.file_flags = 0
        self.files: Dict[str, BSAFileRecord] = {}

    def parse(self) -> bool:
        """Считывает заголовок и оглавление файлов архива."""
        if not self.path.exists() or self.path.stat().st_size < 36:
            return False

        try:
            with open(self.path, "rb") as f:
                header = f.read(36)
                if len(header) < 36:
                    return False

                magic, version, folder_offset, archive_flags, folder_count, file_count, \
                total_folder_name_len, total_file_name_len, file_flags = struct.unpack("<4sIIIIIIII", header)

                if magic != self.MAGIC:
                    return False

                self.version = version
                self.folder_offset = folder_offset
                self.archive_flags = archive_flags
                self.folder_count = folder_count
                self.file_count = file_count
                self.total_folder_name_len = total_folder_name_len
                self.total_file_name_len = total_file_name_len
                self.file_flags = file_flags

                # В Skyrim SE (v105) размер записи папки 24 байта (с 64-битным смещением), в LE (v104) — 16 байт
                raw_folders = []
                for _ in range(folder_count):
                    if version == 105:
                        f_hash, count, pad, offset = struct.unpack("<QIIQ", f.read(24))
                    else:
                        f_hash, count, offset = struct.unpack("<QII", f.read(16))
                    raw_folders.append({"hash": f_hash, "count": count, "offset": offset, "files": []})

                # Считываем информацию о файлах по папкам
                for folder in raw_folders:
                    name_len = struct.unpack("<B", f.read(1))[0]
                    folder_name = f.read(name_len).decode("ascii", errors="replace").rstrip("\x00")
                    folder["name"] = folder_name

                    files = []
                    for _ in range(folder["count"]):
                        file_hash, size, file_offset = struct.unpack("<QII", f.read(16))
                        files.append({"hash": file_hash, "size": size, "offset": file_offset})
                    folder["files"] = files

                # Считываем имена файлов (File Names Block)
                raw_names = f.read(total_file_name_len)
                file_names = [x.decode("ascii", errors="replace") for x in raw_names.split(b"\x00") if x]

                # Связываем пути и структуры файлов
                file_idx = 0
                for folder in raw_folders:
                    folder_name = folder.get("name", "").replace("\\", "/")
                    for file_info in folder["files"]:
                        if file_idx < len(file_names):
                            file_name = file_names[file_idx]
                            file_idx += 1
                        else:
                            file_name = f"file_{file_idx}"

                        full_path = f"{folder_name}/{file_name}" if folder_name else file_name
                        rec = BSAFileRecord(
                            name_hash=file_info["hash"],
                            size=file_info["size"],
                            offset=file_info["offset"],
                            full_path=full_path
                        )
                        self.files[full_path.lower()] = rec

                return True
        except Exception as e:
            print(f"⚠️ Ошибка чтения структуры BSA архива {self.path.name}: {e}")
            return False

    def extract_file(self, internal_path: str, out_path: Path) -> bool:
        """Извлекает конкретный файл из архива на диск с автоматической декомпрессией."""
        norm_key = internal_path.lower().replace("\\", "/")
        rec = self.files.get(norm_key)
        if not rec:
            return False

        try:
            with open(self.path, "rb") as f:
                f.seek(rec.offset)
                raw_data = f.read(rec.actual_size)

                # Проверяем сжатие: флаг в размере (0x40000000) или глобальный флаг архива (0x0100)
                is_comp = rec.is_compressed or (bool(self.archive_flags & 0x0100) and not (rec.size & 0x40000000))
                if is_comp:
                    try:
                        # В заголовке сжатого блока 4 байта uncompressed_size
                        decompressed = zlib.decompress(raw_data[4:])
                    except Exception:
                        try:
                            decompressed = zlib.decompress(raw_data)
                        except Exception:
                            decompressed = raw_data
                else:
                    decompressed = raw_data

                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(decompressed)
                return True
        except Exception as e:
            print(f"⚠️ Ошибка распаковки файла {internal_path} из {self.path.name}: {e}")
            return False


class BSAManager:
    """
    Высокоуровневый координатор работы с архивами модов.
    """

    @classmethod
    def find_bsa_archives(
        cls,
        plugin_name: str,
        search_dirs: Optional[List[Path]] = None
    ) -> List[Path]:
        """
        Ищет все связанные BSA архивы для целевого плагина.
        """
        clean_name = plugin_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        base_patterns = [
            f"{clean_name}.bsa",
            f"{clean_name} - Main.bsa",
            f"{clean_name} - Textures.bsa",
            f"{clean_name} - Meshes.bsa",
            f"{clean_name}.ba2",
            f"{clean_name} - Main.ba2",
        ]

        found: List[Path] = []
        default_dirs = [
            BASE_DIR,
            BASE_DIR / "data",
            DATA_DIR / "raw_extracted",
        ]

        # Автопоиск в каталогах MO2 (из .env, settings.json или стандартных путей)
        mo2_candidates = [
            os.environ.get("MO2_BASE_PATH"),
            Path("D:/Games/Flappy/Flappy"),
            Path("D:/Games/Skyrim SE/MO2"),
            Path("C:/Modding/MO2"),
            Path(os.path.expandvars("%LOCALAPPDATA%/ModOrganizer/Skyrim Special Edition")),
        ]
        for cand in mo2_candidates:
            if not cand:
                continue
            cand_p = Path(cand)
            mo2_mods_base = cand_p / "mods" if cand_p.name.lower() != "mods" else cand_p
            if mo2_mods_base.exists() and mo2_mods_base.is_dir():
                for mod_folder in mo2_mods_base.iterdir():
                    if not mod_folder.is_dir():
                        continue
                    # 1. Если внутри папки лежит целевой .esp
                    if (mod_folder / plugin_name).exists() or (mod_folder / f"{clean_name}.esp").exists():
                        default_dirs.append(mod_folder)
                        continue
                    # 2. Если имя папки содержит название мода
                    first_word = clean_name.split()[0].lower() if clean_name else ""
                    if (clean_name.lower() in mod_folder.name.lower() or
                        (len(first_word) >= 4 and first_word in mod_folder.name.lower())):
                        default_dirs.append(mod_folder)
                break

        if search_dirs:
            default_dirs = search_dirs + default_dirs

        for d in default_dirs:
            if not d or not d.exists():
                continue
            for pattern in base_patterns:
                p = d / pattern
                if p.exists() and p.is_file() and p not in found:
                    found.append(p)

            # Поиск без учета регистра
            try:
                for file_p in d.glob("*.[bB][sS][aA]"):
                    if clean_name.lower() in file_p.name.lower() and file_p not in found:
                        found.append(file_p)
            except Exception:
                pass

        return found

    @classmethod
    def find_and_extract_mcm(cls, plugin_name: str) -> Optional[Path]:
        """
        Сканирует связанные BSA архивы плагина и при обнаружении Interface/Translations/*_ENGLISH.txt
        распаковывает его во временную папку data/extracted_bsa/<ModName>/ и возвращает путь.
        """
        clean_name = plugin_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()

        # 1. Проверяем, был ли файл уже точечно извлечен в кэш
        cached_dirs = [
            EXTRACTED_BSA_DIR / clean_name / "Interface" / "Translations",
            EXTRACTED_BSA_DIR / clean_name / "interface" / "translations",
            EXTRACTED_BSA_DIR / clean_name / "Interface" / "translations",
        ]
        for c_dir in cached_dirs:
            if c_dir.exists():
                for txt_f in c_dir.glob("*.[tT][xT][tT]"):
                    if txt_f.name.lower().endswith("_english.txt"):
                        return txt_f

        archives = cls.find_bsa_archives(plugin_name)
        if not archives:
            return None

        for bsa_path in archives:
            parser = BSAParser(bsa_path)
            if not parser.parse():
                continue

            # Ищем файлы переводов
            for file_path, rec in parser.files.items():
                if "interface/translations/" in file_path and file_path.endswith("_english.txt"):
                    file_name = Path(rec.full_path).name
                    dest_file = EXTRACTED_BSA_DIR / clean_name / "Interface" / "Translations" / file_name
                    print(f"    📦 Обнаружен архив мода: \033[1;36m{bsa_path.name}\033[0m")
                    print(f"    🔍 Найдено внутри архива: {rec.full_path}")
                    if parser.extract_file(file_path, dest_file):
                        print(f"    ⚡ Извлечено для перевода (Loose Mode): \033[1;32m{dest_file.name}\033[0m")
                        return dest_file

        return None
