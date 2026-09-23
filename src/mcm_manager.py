"""
🐾 SkyUI MCM Translation Manager (Менеджер переводов меню настроек SkyUI).
Обрабатывает текстовые файлы переводов Interface/Translations/<ModName>_ENGLISH.txt:
  1. Поиск файлов переводов (в открытом виде Interface/Translations или внутри BSA архивов).
  2. Парсинг пар '$KEY \t Value' в кодировке UTF-16 LE with BOM / UTF-8.
  3. Экспорт готового перевода в Interface/Translations/<ModName>_RUSSIAN.txt в строгой кодировке UTF-16 LE with BOM.
"""

import os
import re
import codecs
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MCM_EXPORT_DIR = DATA_DIR / "mcm_output"
MCM_EXPORT_DIR.mkdir(parents=True, exist_ok=True)


class MCMEntry:
    """Запись одной строки из файла перевода MCM."""

    def __init__(self, key: str, text: str, translated: str = "", line_num: int = 0):
        self.key = key.strip()
        self.text = text
        self.translated = translated
        self.line_num = line_num

    def to_item_dict(self, mod_name: str, item_id: int) -> Dict[str, Any]:
        return {
            "id": item_id,
            "formid": f"MCM:{self.key}",
            "type": "MCM",
            "editorid": self.key,
            "path": self.key,
            "text": self.text,
            "translated": self.translated,
            "source": "mcm",
            "speaker_context": {
                "role": "system",
                "speaker_name": "SkyUI MCM",
                "gender": "neutral",
                "addressing": "",
                "target_gender": "unknown",
                "source_formid": f"MCM:{self.key}",
                "badge": f"⚙️ {self.key}"
            },
            "parent_context": {
                "topic_name": "SkyUI MCM Menu",
                "topic_id": mod_name
            }
        }


class MCMManager:
    """Менеджер поиска, чтения и экспорта файлов SkyUI MCM."""

    @classmethod
    def find_mcm_file(
        cls,
        plugin_name: str,
        search_dirs: Optional[List[Path]] = None,
    ) -> Optional[Path]:
        """
        Монолитный многоуровневый поиск файла перевода SkyUI MCM (_ENGLISH.txt):
          1. Прямой поиск в папке мода в MO2, где физически лежит плагин (.esp/.esm/.esl).
          2. Поиск по токенам и нечеткому совпадению имени папки в mods/.
          3. Глобальный скан всех папок Interface/Translations в MO2 mods.
          4. Поиск в локальных путях проекта и search_dirs.
          5. Распаковка из BSA архивов через BSAManager.
          6. Fallback: поиск любого единственного *_english.txt в папке мода.
        """
        clean_name = plugin_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        clean_lower = clean_name.lower()
        candidates = [
            f"{clean_name}_ENGLISH.txt",
            f"{clean_name}_english.txt",
            f"{plugin_name}_ENGLISH.txt",
            f"{plugin_name}_english.txt",
        ]

        trans_subdirs = [
            "Interface/Translations",
            "Interface/translations",
            "interface/translations",
            "interface/Translations",
            "Interface",
            "interface",
            "Translations",
            "translations"
        ]

        # Базовые локальные каталоги
        search_paths: List[Path] = []
        if search_dirs:
            search_paths.extend([p for p in search_dirs if p and p.exists()])

        search_paths.extend([
            BASE_DIR / "Interface" / "Translations",
            BASE_DIR / "Interface" / "translations",
            BASE_DIR / "data" / "mcm",
            DATA_DIR / "raw_extracted",
            BASE_DIR,
        ])

        # ==========================================================
        # УРОВЕНЬ 1, 2, 3: ИНТЕГРАЦИЯ С MO2 (mods directory)
        # ==========================================================
        try:
            from src.mo2_deployer import MO2Deployer
            deployer = MO2Deployer()
            if deployer.mods_dir and deployer.mods_dir.exists():
                # 1. Точная папка мода, где лежит .esp
                orig_folder_name = deployer.find_original_mod_folder(plugin_name)
                if orig_folder_name:
                    mod_folder = deployer.mods_dir / orig_folder_name
                    for sub in trans_subdirs:
                        t_dir = mod_folder / sub
                        if t_dir.exists() and t_dir not in search_paths:
                            search_paths.insert(0, t_dir)

                # 2. Сканируем все папки модов в MO2
                for mod_folder in deployer.mods_dir.iterdir():
                    if not mod_folder.is_dir() or mod_folder.name.startswith("."):
                        continue
                    
                    folder_lower = mod_folder.name.lower()
                    # Если папка содержит имя плагина или плагин лежит внутри
                    has_plugin = (mod_folder / plugin_name).exists() or (mod_folder / f"{clean_name}.esp").exists()
                    has_name = clean_lower in folder_lower or any(tok in folder_lower for tok in clean_lower.split("_") if len(tok) >= 3)
                    
                    if has_plugin or has_name:
                        for sub in trans_subdirs:
                            t_dir = mod_folder / sub
                            if t_dir.exists() and t_dir not in search_paths:
                                search_paths.insert(0, t_dir)
        except Exception:
            pass

        # Проверяем все собранные пути на наличие точного совпадения кандидатов
        for directory in search_paths:
            if not directory or not directory.exists():
                continue

            for candidate in candidates:
                cand_path = directory / candidate
                if cand_path.exists() and cand_path.is_file():
                    return cand_path

            # Регистронезависимый поиск
            try:
                for file_p in directory.glob("*.[tT][xT][tT]"):
                    if any(c.lower() == file_p.name.lower() for c in candidates):
                        return file_p
                    # Если имя файла содержит clean_name и заканчивается на english.txt
                    f_name_lower = file_p.name.lower()
                    if clean_lower in f_name_lower and "english" in f_name_lower:
                        return file_p
            except Exception:
                pass

        # ==========================================================
        # УРОВЕНЬ 4: ГЛОБАЛЬНЫЙ СКАН ВСЕХ Interface/Translations В MO2
        # ==========================================================
        try:
            from src.mo2_deployer import MO2Deployer
            deployer = MO2Deployer()
            if deployer.mods_dir and deployer.mods_dir.exists():
                for mod_folder in deployer.mods_dir.iterdir():
                    if not mod_folder.is_dir():
                        continue
                    for sub in trans_subdirs[:4]:
                        t_dir = mod_folder / sub
                        if t_dir.exists():
                            for file_p in t_dir.glob("*.[tT][xT][tT]"):
                                f_lower = file_p.name.lower()
                                if ("english" in f_lower) and (clean_lower in f_lower or f_lower.replace("_english.txt", "") in clean_lower):
                                    return file_p
        except Exception:
            pass

        # ==========================================================
        # УРОВЕНЬ 5: РАСПАКОВКА ИЗ BSA АРХИВОВ
        # ==========================================================
        try:
            from src.bsa_manager import BSAManager
            bsa_extracted = BSAManager.find_and_extract_mcm(plugin_name)
            if bsa_extracted and bsa_extracted.exists():
                return bsa_extracted
        except Exception as e:
            print(f"⚠️ Ошибка проверки BSA архивов: {e}")

        # ==========================================================
        # УРОВЕНЬ 6: FALLBACK — ЕДИНСТВЕННЫЙ MCM В ПАПКЕ МОДА
        # ==========================================================
        try:
            from src.mo2_deployer import MO2Deployer
            deployer = MO2Deployer()
            if deployer.mods_dir and deployer.mods_dir.exists():
                orig_folder_name = deployer.find_original_mod_folder(plugin_name)
                if orig_folder_name:
                    mod_folder = deployer.mods_dir / orig_folder_name
                    for sub in trans_subdirs:
                        t_dir = mod_folder / sub
                        if t_dir.exists():
                            txt_files = [f for f in t_dir.glob("*.[tT][xT][tT]") if "english" in f.name.lower()]
                            if len(txt_files) == 1:
                                return txt_files[0]
        except Exception:
            pass

        return None

    @classmethod
    def discover_and_load_mcm(
        cls,
        plugin_name: str,
        clean_mod_name: str,
        start_id: int = 1000,
        search_dirs: Optional[List[Path]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Path]]:
        """
        Единый монолитный метод: обнаружение, логирование, разбор и авто-подтягивание русского перевода.
        Возвращает кортеж: (список записей для конвейера, путь к обнаруженному файлу).
        """
        mcm_file = cls.find_mcm_file(plugin_name, search_dirs=search_dirs)
        if not mcm_file:
            return [], None

        items = cls.parse_mcm_file(mcm_file, clean_mod_name, start_id=start_id)
        return items, mcm_file

    @classmethod
    def read_mcm_lines(cls, file_path: Path) -> Tuple[List[MCMEntry], str]:
        """
        Читает MCM файл с автоматическим определением кодировки (UTF-16 LE с BOM, UTF-8 с BOM, UTF-8).
        Возвращает список записей (MCMEntry) и обнаруженную кодировку.
        """
        raw_bytes = file_path.read_bytes()
        encoding = "utf-16"

        # Детекция кодировки по BOM
        if raw_bytes.startswith(codecs.BOM_UTF16_LE) or raw_bytes.startswith(codecs.BOM_UTF16_BE):
            encoding = "utf-16"
        elif raw_bytes.startswith(codecs.BOM_UTF8):
            encoding = "utf-8-sig"
        else:
            # Пробуем декодировать как utf-16, при ошибке — utf-8
            try:
                raw_bytes.decode("utf-16")
                encoding = "utf-16"
            except UnicodeDecodeError:
                encoding = "utf-8"

        content = raw_bytes.decode(encoding, errors="replace")
        lines = content.splitlines()

        entries: List[MCMEntry] = []
        for idx, line in enumerate(lines, 1):
            if not line or not line.strip():
                continue
            # Формат строки MCM: $KEY \t Text
            if "\t" in line:
                parts = line.split("\t", 1)
                key = parts[0].strip()
                val = parts[1]
                entries.append(MCMEntry(key=key, text=val, line_num=idx))
            elif line.startswith("$"):
                # Если разделитель — пробелы
                parts = re.split(r'\s+', line, maxsplit=1)
                key = parts[0].strip()
                val = parts[1] if len(parts) > 1 else ""
                entries.append(MCMEntry(key=key, text=val, line_num=idx))

        return entries, encoding

    @classmethod
    def parse_mcm_file(cls, file_path: Path, mod_name: str, start_id: int = 1000) -> List[Dict[str, Any]]:
        """
        Парсит MCM файл и возвращает унифицированный список элементов для переводчика.
        Если рядом найден _RUSSIAN.txt, автоматически подтягивает существующий русский перевод!
        """
        entries, _ = cls.read_mcm_lines(file_path)
        items: List[Dict[str, Any]] = []

        # Проверяем, есть ли рядом файл с существующим русским переводом
        ru_candidates = [
            file_path.parent / file_path.name.replace("_ENGLISH.txt", "_RUSSIAN.txt").replace("_english.txt", "_russian.txt"),
            file_path.parent / f"{mod_name}_RUSSIAN.txt",
            file_path.parent / f"{mod_name}_russian.txt",
        ]
        existing_ru_map: Dict[str, str] = {}
        for ru_cand in ru_candidates:
            if ru_cand.exists() and ru_cand.is_file():
                ru_entries, _ = cls.read_mcm_lines(ru_cand)
                for r in ru_entries:
                    if r.text and r.text.strip():
                        existing_ru_map[r.key.lower()] = r.text
                break

        for idx, entry in enumerate(entries, start_id):
            item = entry.to_item_dict(mod_name=mod_name, item_id=idx)
            # Если для ключа найден существующий перевод в _RUSSIAN.txt
            if entry.key.lower() in existing_ru_map:
                raw_ru = existing_ru_map[entry.key.lower()]
                # Санитизация от грубых машинных ляпов (гонка -> раса, персонал -> посох и т.д.)
                try:
                    from src.quality_gate import QualityGate
                    raw_ru = QualityGate.sanitize_false_friends(entry.text, raw_ru)
                except Exception:
                    pass
                item["translated"] = raw_ru
                item["source"] = "mcm_existing"
            items.append(item)

        return items

    @classmethod
    def export_russian_mcm(
        cls,
        entries: List[Dict[str, Any]],
        plugin_name: str,
        out_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Экспортирует переведенные MCM строки в файл <PluginName>_RUSSIAN.txt
        в строгой кодировке UTF-16 LE с BOM (\ufeff).
        """
        clean_name = plugin_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        target_dir = out_dir or (BASE_DIR / "Interface" / "Translations")
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{clean_name}_RUSSIAN.txt"

        mcm_entries = [
            e for e in entries
            if e.get("type") == "MCM" or str(e.get("formid", "")).startswith("MCM:")
        ]

        if not mcm_entries:
            return None

        lines_to_write = []
        for item in mcm_entries:
            key = item.get("path") or item.get("editorid") or str(item.get("formid", "")).replace("MCM:", "")
            if not key.startswith("$"):
                key = f"${key}"

            # Берем translated, если есть, иначе fallback на text/original
            trans_text = item.get("translated") or item.get("text") or item.get("original") or ""
            orig_text = item.get("text") or item.get("original") or ""
            
            # Финальная санитизация от ложных друзей перед экспортом
            try:
                from src.quality_gate import QualityGate
                trans_text = QualityGate.sanitize_false_friends(orig_text, trans_text)
            except Exception:
                pass

            lines_to_write.append(f"{key}\t{trans_text}")

        # Формируем контент с Windows CRLF переводами строк и записываем с BOM UTF-16 LE
        file_content = "\r\n".join(lines_to_write) + "\r\n"
        with open(out_path, "w", encoding="utf-16", newline="") as f:
            f.write(file_content)

        # Также сохраняем резервную копию в data/mcm_output
        backup_path = MCM_EXPORT_DIR / f"{clean_name}_RUSSIAN.txt"
        with open(backup_path, "w", encoding="utf-16", newline="") as f:
            f.write(file_content)

        return out_path
