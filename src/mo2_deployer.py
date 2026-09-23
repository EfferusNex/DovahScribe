"""
🐾 Mod Organizer 2 Direct Deployer (src/mo2_deployer.py).
Обеспечивает:
  1. Авто-обнаружение путей инстанса и активного профиля MO2.
  2. Сборку изолированного пакета локализации `<ModName> [RU]/` (Zero Overwrite).
  3. Генерацию meta.ini для MO2 с категорией переводов и цветовой маркировкой.
  4. Автоматическую вставку в `modlist.txt` строго с более высоким приоритетом (над оригиналом).
  5. Автоматическую регистрацию в `plugins.txt` (если есть отдельный .esp патч).
  6. Безопасность: создание бэкапов modlist.txt.bak и plugins.txt.bak.
"""

import os
import re
import sys
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = BASE_DIR / "settings.json"


class MO2Deployer:
    """
    Модуль прямого деплоя локализаций в Mod Organizer 2.
    """

    # Стандартные пути для авто-поиска MO2
    DEFAULT_CANDIDATE_PATHS = [
        Path("C:/Modding/MO2"),
        Path(os.path.expandvars("%LOCALAPPDATA%/ModOrganizer/Skyrim Special Edition")),
    ]


    def __init__(self, mo2_base_path: Optional[Path] = None):
        self.mo2_base = self._resolve_mo2_base(mo2_base_path)
        self.mods_dir = self.mo2_base / "mods" if self.mo2_base else None
        self.profiles_dir = self.mo2_base / "profiles" if self.mo2_base else None

    def _resolve_mo2_base(self, explicit_path: Optional[Path] = None) -> Optional[Path]:
        """Определяет базовую директорию инстанса MO2."""
        # 1. Явный путь
        if explicit_path and Path(explicit_path).exists():
            p = Path(explicit_path).resolve()
            if (p / "mods").exists() or (p / "profiles").exists():
                self._save_settings({"mo2_path": str(p)})
                return p

        # 2. Из переменной окружения MO2_BASE_PATH (.env)
        env_mo2 = os.environ.get("MO2_BASE_PATH")
        if env_mo2 and Path(env_mo2).exists():
            p = Path(env_mo2).resolve()
            if (p / "mods").exists() or (p / "profiles").exists():
                return p

        # 3. Из файла settings.json
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    saved = cfg.get("mo2_path")
                    if saved and Path(saved).exists():
                        return Path(saved).resolve()
            except Exception:
                pass

        # 4. Кандидаты по умолчанию
        for cand in self.DEFAULT_CANDIDATE_PATHS:
            if cand.exists() and ((cand / "mods").exists() or (cand / "profiles").exists()):
                self._save_settings({"mo2_path": str(cand)})
                return cand.resolve()

        return None

    def _save_settings(self, data: Dict[str, Any]):
        """Сохраняет настройки по умолчанию."""
        cfg = {}
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                pass
        cfg.update(data)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_active_profile_dir(self) -> Optional[Path]:
        """
        Определяет активный профиль MO2 (по последней модификации modlist.txt).
        """
        if not self.profiles_dir or not self.profiles_dir.exists():
            return None

        profiles = [p for p in self.profiles_dir.iterdir() if p.is_dir() and (p / "modlist.txt").exists()]
        if not profiles:
            return None

        # Профиль, чей modlist.txt обновлялся позже всего
        profiles.sort(key=lambda p: (p / "modlist.txt").stat().st_mtime, reverse=True)
        return profiles[0]

    def find_original_mod_folder(self, mod_name: str) -> Optional[str]:
        """
        Ищет точное имя папки оригинального мода в директории mods/.
        """
        if not self.mods_dir or not self.mods_dir.exists():
            return None

        clean_name = mod_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip().lower()

        # 1. Точное совпадение
        for folder in self.mods_dir.iterdir():
            if not folder.is_dir():
                continue
            fname_lower = folder.name.lower()
            # Пропускаем уже созданные переводы
            if "[ru]" in fname_lower or "_russian" in fname_lower:
                continue

            if fname_lower == clean_name or folder.name == mod_name:
                return folder.name
            
            # Проверка наличия плагина внутри
            if (folder / mod_name).exists():
                return folder.name

        # 2. Нестрогое совпадение
        for folder in self.mods_dir.iterdir():
            if not folder.is_dir():
                continue
            fname_lower = folder.name.lower()
            if "[ru]" in fname_lower or "_russian" in fname_lower:
                continue
            if clean_name in fname_lower or fname_lower in clean_name:
                return folder.name

        return None

    def find_original_plugin_file(self, mod_name: str) -> Optional[Path]:
        """
        Ищет физический файл оригинального плагина (.esp/.esm/.esl) в директории mods/.
        """
        if not self.mods_dir or not self.mods_dir.exists():
            return None

        clean_name = mod_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        plugin_filename = mod_name if any(mod_name.lower().endswith(ext) for ext in [".esp", ".esm", ".esl"]) else f"{clean_name}.esp"

        # 1. Поиск в папке оригинального мода
        orig_folder = self.find_original_mod_folder(mod_name)
        if orig_folder:
            folder_path = self.mods_dir / orig_folder
            candidate = folder_path / plugin_filename
            if candidate.exists() and candidate.is_file():
                return candidate
            # Регистронезависимый поиск в папке
            for f in folder_path.iterdir():
                if f.is_file() and f.name.lower() == plugin_filename.lower():
                    return f

        # 2. Глобальный поиск по всем папкам mods/
        for folder in self.mods_dir.iterdir():
            if not folder.is_dir() or "[ru]" in folder.name.lower() or "_russian" in folder.name.lower():
                continue
            cand = folder / plugin_filename
            if cand.exists() and cand.is_file():
                return cand
            for f in folder.iterdir():
                if f.is_file() and f.name.lower() == plugin_filename.lower():
                    return f

        return None

    def generate_meta_ini(self, mod_title: str, version: str = "1.0.0") -> str:
        """
        Генерирует валидный meta.ini для Mod Organizer 2 с подсветкой и категорией.
        """
        now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"""[General]
gameName=SkyrimSE
modid=0
version={version}
newestVersion=
category="29,"
installationFile=
repository=Nexus
ignoredVersion=
comments=Автоматическая локализация от Lain AI (Skyrim Translator)
notes=
nexusDescription=
url=
hasCustomURL=false
lastNexusQuery=
lastNexusUpdate=
nexusLastModified={now_iso}
converted=false
validated=false
color=@Variant(\\0\\0\\0\\x43\\x1\\xff\\xff\\x80\\x80\\xff\\xff\\x80\\x80\\0\\0)
tracked=0
"""

    def insert_mod_priority(self, profile_dir: Path, ru_mod_folder_name: str, original_mod_name: Optional[str] = None) -> bool:
        """
        Вставляет '+<ModName> [RU]' в modlist.txt СТРОГО НАД оригиналом (выше по приоритету).
        В MO2 верхние строки имеют больший приоритет.
        """
        modlist_path = profile_dir / "modlist.txt"
        if not modlist_path.exists():
            return False

        # Читаем modlist.txt
        with open(modlist_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\r\n") for line in f.readlines()]

        # Создаём бэкап
        bak_path = profile_dir / "modlist.txt.bak"
        with open(bak_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Удаляем существующую запись нашего мода (если уже был добавлен)
        target_entry = f"+{ru_mod_folder_name}"
        clean_lines = [l for l in lines if l != target_entry and l != f"-{ru_mod_folder_name}"]

        # Ищем позицию оригинального мода
        insert_idx = 0
        found_orig = False

        if original_mod_name:
            orig_variants = [f"+{original_mod_name}", f"-{original_mod_name}"]
            for idx, l in enumerate(clean_lines):
                if l in orig_variants or (l.startswith("+") and original_mod_name.lower() in l.lower()):
                    insert_idx = idx  # Вставляем прямо ПЕРЕД оригиналом (строка выше = приоритет больше)
                    found_orig = True
                    break

        if not found_orig:
            # Если оригинал не найден, вставляем в начало после заголовка комментариев
            insert_idx = 1 if len(clean_lines) > 0 and clean_lines[0].startswith("#") else 0

        clean_lines.insert(insert_idx, target_entry)

        # Записываем обратно
        with open(modlist_path, "w", encoding="utf-8") as f:
            f.write("\n".join(clean_lines) + "\n")

        return True

    def insert_plugin_load_order(self, profile_dir: Path, ru_plugin_name: str, original_plugin_name: str) -> bool:
        """
        Вставляет '*<Plugin>_RU.esp' в plugins.txt СТРОГО ПОСЛЕ родительского плагина.
        """
        plugins_path = profile_dir / "plugins.txt"
        if not plugins_path.exists():
            return False

        with open(plugins_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\r\n") for line in f.readlines()]

        # Создаём бэкап
        bak_path = profile_dir / "plugins.txt.bak"
        with open(bak_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        target_entry = f"*{ru_plugin_name}"
        clean_lines = [l for l in lines if l != target_entry and l != ru_plugin_name]

        orig_entry = f"*{original_plugin_name.lower()}"
        insert_idx = len(clean_lines)

        for idx, l in enumerate(clean_lines):
            if l.lower() == orig_entry or l.lower() == original_plugin_name.lower():
                insert_idx = idx + 1  # СТРОГО СЛЕДОМ за оригиналом
                break

        clean_lines.insert(insert_idx, target_entry)

        with open(plugins_path, "w", encoding="utf-8") as f:
            f.write("\n".join(clean_lines) + "\n")

        return True

    def deploy(
        self,
        mod_name: str,
        esp_patch_path: Optional[Path] = None,
        mcm_russian_path: Optional[Path] = None,
        extra_files: Optional[List[Tuple[Path, str]]] = None,
        clone_original_esp: bool = True,
    ) -> Dict[str, Any]:
        """
        Выполняет полный цикл изолированного деплоя в Mod Organizer 2:
          1. Создает папку <ModName> [RU] в mods/.
          2. Клонирует/копирует .esp под точным именем оригинала (для перезаписи в MO2 по приоритету).
          3. Копирует файлы перевода MCM (Interface/Translations).
          4. Генерирует meta.ini.
          5. Обновляет modlist.txt с приоритетом над оригиналом.
        """
        if not self.mods_dir or not self.mods_dir.exists():
            return {
                "success": False,
                "error": f"Директория mods не найдена. Укажите путь к MO2 через --mo2-path или в settings.json.",
            }

        # Определяем базовое имя папки мода
        orig_folder_name = self.find_original_mod_folder(mod_name)
        base_title = orig_folder_name or mod_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        ru_folder_name = f"{base_title} [RU]"
        target_mod_dir = self.mods_dir / ru_folder_name

        # Создаем структуру каталогов
        target_mod_dir.mkdir(parents=True, exist_ok=True)

        copied_files = []

        clean_name = mod_name.replace(".esp", "").replace(".esm", "").replace(".esl", "").strip()
        plugin_filename = mod_name if any(mod_name.lower().endswith(ext) for ext in [".esp", ".esm", ".esl"]) else f"{clean_name}.esp"

        # 1. Клонируем / разворачиваем .esp плагин под оригинальным именем
        if esp_patch_path and Path(esp_patch_path).exists():
            # Если передан готовый модифицированный / пропатченный .esp
            dest_esp = target_mod_dir / plugin_filename
            shutil.copy2(esp_patch_path, dest_esp)
            copied_files.append(str(dest_esp.relative_to(target_mod_dir)))
        elif clone_original_esp:
            # Клонируем оригинальный .esp файл для перезаписи через VFS MO2
            orig_esp_file = self.find_original_plugin_file(mod_name)
            if orig_esp_file and orig_esp_file.exists():
                dest_esp = target_mod_dir / orig_esp_file.name
                shutil.copy2(orig_esp_file, dest_esp)
                copied_files.append(str(dest_esp.relative_to(target_mod_dir)))

        # 2. Копируем MCM файл локализации
        if mcm_russian_path and Path(mcm_russian_path).exists():
            dest_mcm_dir = target_mod_dir / "Interface" / "Translations"
            dest_mcm_dir.mkdir(parents=True, exist_ok=True)
            dest_mcm = dest_mcm_dir / Path(mcm_russian_path).name
            shutil.copy2(mcm_russian_path, dest_mcm)
            copied_files.append(str(dest_mcm.relative_to(target_mod_dir)))

        # 3. Копируем дополнительные файлы
        if extra_files:
            for src_file, rel_dest in extra_files:
                if Path(src_file).exists():
                    dest_path = target_mod_dir / rel_dest
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_path)
                    copied_files.append(str(dest_path.relative_to(target_mod_dir)))

        # 4. Создаем meta.ini
        meta_content = self.generate_meta_ini(ru_folder_name)
        with open(target_mod_dir / "meta.ini", "w", encoding="utf-8") as f:
            f.write(meta_content)
        copied_files.append("meta.ini")

        # 5. Обновляем modlist.txt в активном профиле
        active_prof = self.get_active_profile_dir()
        modlist_updated = False
        if active_prof:
            modlist_updated = self.insert_mod_priority(
                profile_dir=active_prof,
                ru_mod_folder_name=ru_folder_name,
                original_mod_name=orig_folder_name,
            )

        return {
            "success": True,
            "mod_folder": ru_folder_name,
            "target_path": str(target_mod_dir),
            "files_deployed": copied_files,
            "active_profile": active_prof.name if active_prof else "Unknown",
            "modlist_priority_updated": modlist_updated,
            "original_mod_matched": orig_folder_name,
        }
