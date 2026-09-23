#!/usr/bin/env python3
"""
🐾 DovahScribe Desktop App (PyWebView Desktop Launcher)
Настольное приложение для CAT-локализации модов Skyrim без необходимости веб-сервера.
Использует нативный системный WebView2 и предоставляет двусторонний мост Python <-> JavaScript.
"""

import sys
import os
import json
import webview
import logging
from pathlib import Path
from typing import Dict, Any

# Базовые директории
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "dovahscribe_app.log"

# Настройка подробного логирования DovahScribe
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DovahScribeApp")

# Отключаем спам внутренних COM-ошибок pywebview (он инспектирует свойства окна из фонового потока)
logging.getLogger("pywebview").setLevel(logging.CRITICAL)

# Настройка UTF-8 для консоли Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Базовые директории
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"
REVIEW_DIR = DATA_DIR / "review"
OPS_DIR = DATA_DIR / "ops"
REVIEW_DIR.mkdir(parents=True, exist_ok=True)
OPS_DIR.mkdir(parents=True, exist_ok=True)


# Настройки pywebview
webview.settings['ALLOW_DOWNLOADS'] = True

class DovahScribeAPI:
    """
    Python-мост для вызова нативных операций из JavaScript интерфейса.
    """
    def __init__(self, window=None):
        self.window = window

    def set_window(self, window):
        self.window = window

    def ping(self) -> Dict[str, Any]:
        """Проверка соединения с Python-бэкендом."""
        return {"status": "ok", "message": "🐾 DovahScribe Native Bridge активен!"}

    def save_review_file(self, filename: str, content_json: str) -> Dict[str, Any]:
        """
        Прямое сохранение файла ревью на диск без диалогов браузера.
        """
        try:
            logger.info("Получен запрос на сохранение Review JSON: %s (размер: %d байт)", filename, len(content_json))
            target_path = REVIEW_DIR / filename
            target_path.write_text(content_json, encoding="utf-8")
            logger.info("Успешно сохранено: %s", target_path)
            return {
                "success": True,
                "path": str(target_path),
                "message": f"✨ Успешно сохранено на диск: {target_path.name}"
            }
        except Exception as e:
            logger.exception("Ошибка при сохранении Review JSON: %s", e)
            return {"success": False, "error": str(e)}

    def save_ops_manifest(self, filename: str, content_json: str) -> Dict[str, Any]:
        """
        Прямое сохранение Ops манифеста на диск.
        """
        try:
            logger.info("Получен запрос на сохранение Ops Manifest: %s (размер: %d байт)", filename, len(content_json))
            target_path = OPS_DIR / filename
            target_path.write_text(content_json, encoding="utf-8")
            logger.info("Ops манифест сохранен: %s", target_path)
            return {
                "success": True,
                "path": str(target_path),
                "message": f"⚡ Ops манифест сохранен: {target_path.name}"
            }
        except Exception as e:
            logger.exception("Ошибка при сохранении Ops Manifest: %s", e)
            return {"success": False, "error": str(e)}

    def open_file_dialog(self) -> Dict[str, Any]:
        """
        Открытие нативного диалога выбора файла ревью через Windows API.
        """
        if not self.window:
            return {"success": False, "error": "Окно не инициализировано"}

        file_types = ('Review JSON Files (*_review.json;*.json)', 'All Files (*.*)')
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            directory=str(REVIEW_DIR if REVIEW_DIR.exists() else DATA_DIR),
            allow_multiple=False,
            file_types=file_types
        )
        if result and len(result) > 0:
            selected_path = Path(result[0])
            try:
                content = selected_path.read_text(encoding="utf-8")
                return {
                    "success": True,
                    "filename": selected_path.name,
                    "filepath": str(selected_path),
                    "data": json.loads(content)
                }
            except Exception as e:
                return {"success": False, "error": f"Ошибка чтения файла: {e}"}
        return {"success": False, "cancelled": True}


def launch_app(mod_name: str = "SexLabDefeat", width: int = 1380, height: int = 900, debug: bool = False):
    """
    Запуск десктопного окна DovahScribe с логированием.
    """
    logger.info("Запуск DovahScribe Desktop для мода: %s", mod_name)
    api = DovahScribeAPI()

    target_dashboard = WEB_DIR / f"{mod_name}_dashboard.html"
    if not target_dashboard.exists():
        target_dashboard = WEB_DIR / "cat_dashboard.html"

    if not target_dashboard.exists():
        logger.error("Файл разметки не найден: %s", target_dashboard)
        print(f"❌ Ошибка: Файл разметки не найден: {target_dashboard}")
        return

    file_url = target_dashboard.resolve().as_uri()

    try:
        window = webview.create_window(
            title=f"🐾 DovahScribe — AI Localization Suite for Skyrim [{mod_name}]",
            url=file_url,
            js_api=api,
            width=width,
            height=height,
            min_size=(900, 600),
            background_color='#0b0f19',
            text_select=True
        )
        api.set_window(window)

        logger.info("Инициализация окна WebView2...")
        print(f"🐉 Запуск нативного окна DovahScribe: {file_url}")
        
        # Запуск с авто-выбором бэкенда и перехватом логов
        webview.start(debug=debug)
        logger.info("Приложение DovahScribe штатно завершило работу.")
    except Exception as e:
        logger.exception("Критическая ошибка работы окна DovahScribe: %s", e)
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    mod = sys.argv[1] if len(sys.argv) > 1 else "SexLabDefeat"
    is_debug = "--debug" in sys.argv or "-d" in sys.argv
    launch_app(mod, debug=is_debug)
