#!/usr/bin/env python3
"""
🐾 DovahScribe Desktop App (PyWebView Desktop Launcher)
Настольное приложение для CAT-локализации модов Skyrim без необходимости веб-сервера.
Использует нативный системный WebView2 и предоставляет двусторонний мост Python <-> JavaScript.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import webview

# Базовые директории
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "dovahscribe_app.log"
WEB_DIR = BASE_DIR / "web"
DATA_DIR = BASE_DIR / "data"
REVIEW_DIR = DATA_DIR / "review"
OPS_DIR = DATA_DIR / "ops"
REVIEW_DIR.mkdir(parents=True, exist_ok=True)
OPS_DIR.mkdir(parents=True, exist_ok=True)

# Настройка UTF-8 для консоли Windows
if sys.platform == "win32":
    try:
        if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass


# Настройка подробного логирования DovahScribe
handlers: list[logging.Handler] = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
if sys.stdout is not None:
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=handlers,
)
logger = logging.getLogger("DovahScribeApp")

# Подавляем COM-ошибки инспектора pywebview (фоновый поток WinForms)
logging.getLogger("pywebview").setLevel(logging.CRITICAL)


# Глобальный перехватчик необработанных исключений для записи в dovahscribe_app.log
def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Неперехваченное исключение (Uncaught Exception):", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_uncaught_exception

# Настройки pywebview
webview.settings["ALLOW_DOWNLOADS"] = True


class DovahScribeAPI:
    """
    Python-мост для вызова нативных операций из JavaScript интерфейса.
    ВАЖНО: Все ссылки на системные объекты окна хранятся с префиксом '_',
    чтобы инспектор pywebview не обходил COM-дерево контроллера WebView2.
    """

    _serializable = False

    def __init__(self, window: webview.Window | None = None):
        self._window: webview.Window | None = window

    def set_window(self, window: webview.Window) -> None:
        self._window = window

    def ping(self) -> dict[str, Any]:
        """Проверка соединения с Python-бэкендом."""
        return {"status": "ok", "message": "🐾 DovahScribe Native Bridge активен!"}

    def save_review_file(self, filename: str, content_json: str) -> dict[str, Any]:
        """Прямое сохранение файла ревью на диск без диалогов браузера."""
        try:
            logger.info("Получен запрос на сохранение Review JSON: %s (размер: %d байт)", filename, len(content_json))
            target_path = REVIEW_DIR / filename
            target_path.write_text(content_json, encoding="utf-8")
            logger.info("Успешно сохранено: %s", target_path)
            return {
                "success": True,
                "path": str(target_path),
                "message": f"✨ Успешно сохранено на диск: {target_path.name}",
            }
        except Exception as e:
            logger.exception("Ошибка при сохранении Review JSON:")
            return {"success": False, "error": str(e)}

    def save_ops_manifest(self, filename: str, content_json: str) -> dict[str, Any]:
        """Прямое сохранение Ops манифеста на диск."""
        try:
            logger.info("Получен запрос на сохранение Ops Manifest: %s (размер: %d байт)", filename, len(content_json))
            target_path = OPS_DIR / filename
            target_path.write_text(content_json, encoding="utf-8")
            logger.info("Ops манифест сохранен: %s", target_path)
            return {
                "success": True,
                "path": str(target_path),
                "message": f"⚡ Ops манифест сохранен: {target_path.name}",
            }
        except Exception as e:
            logger.exception("Ошибка при сохранении Ops Manifest:")
            return {"success": False, "error": str(e)}

    def open_file_dialog(self) -> dict[str, Any]:
        """Открытие нативного диалога выбора файла ревью через Windows API."""
        if not self._window:
            return {"success": False, "error": "Окно не инициализировано"}

        file_types = ("Review JSON Files (*_review.json;*.json)", "All Files (*.*)")
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            directory=str(REVIEW_DIR if REVIEW_DIR.exists() else DATA_DIR),
            allow_multiple=False,
            file_types=file_types,
        )
        if result and len(result) > 0:
            selected_path = Path(result[0])
            try:
                content = selected_path.read_text(encoding="utf-8")
                return {
                    "success": True,
                    "filename": selected_path.name,
                    "filepath": str(selected_path),
                    "data": json.loads(content),
                }
            except (OSError, ValueError, json.JSONDecodeError) as e:
                logger.warning("Ошибка чтения выбранного файла %s: %s", selected_path, e)
                return {"success": False, "error": f"Ошибка чтения файла: {e}"}
        return {"success": False, "cancelled": True}

    def toggle_maximize(self) -> dict[str, Any]:
        """Переключение между развернутым на весь экран окном и оконным режимом."""
        if not self._window:
            return {"success": False, "error": "Окно не инициализировано"}
        try:
            is_max = getattr(self._window, "maximized", False)
            if is_max:
                self._window.restore()
                return {"success": True, "maximized": False}
            self._window.maximize()
            return {"success": True, "maximized": True}
        except (AttributeError, RuntimeError, OSError) as e:
            logger.warning("Ошибка toggle_maximize: %s", e)
            return {"success": False, "error": str(e)}

    def toggle_fullscreen(self) -> dict[str, Any]:
        """Переключение полноэкранного режима F11."""
        if not self._window:
            return {"success": False, "error": "Окно не инициализировано"}
        try:
            self._window.toggle_fullscreen()
            return {"success": True}
        except (AttributeError, RuntimeError, OSError) as e:
            logger.warning("Ошибка toggle_fullscreen: %s", e)
            return {"success": False, "error": str(e)}



def launch_app(mod_name: str | None = None, width: int = 1440, height: int = 920, debug: bool = False):
    """
    Запуск десктопного окна DovahScribe с логированием, масштабированием и поддержкой полноэкранного режима.
    """
    display_title = mod_name if mod_name else "Workspace"
    logger.info("Запуск DovahScribe Desktop для мода: %s (debug=%s)", display_title, debug)
    api = DovahScribeAPI()

    target_dashboard = WEB_DIR / f"{mod_name}_dashboard.html" if mod_name else WEB_DIR / "cat_dashboard.html"
    if not target_dashboard.exists():
        target_dashboard = WEB_DIR / "cat_dashboard.html"

    if not target_dashboard.exists():
        logger.error("Файл разметки не найден: %s", target_dashboard)
        if sys.stdout is not None:
            print(f"❌ Ошибка: Файл разметки не найден: {target_dashboard}")
        return

    file_url = target_dashboard.resolve().as_uri()

    try:
        window = webview.create_window(
            title=f"🐾 DovahScribe — AI Localization Suite for Skyrim [{display_title}]",
            url=file_url,
            js_api=api,
            width=width,
            height=height,
            resizable=True,
            zoomable=True,
            min_size=(960, 580),
            background_color="#0b0f19",
            text_select=True,
        )
        api.set_window(window)

        logger.info("Инициализация окна WebView2...")
        if sys.stdout is not None:
            print(f"🐉 Запуск нативного окна DovahScribe: {file_url}")

        # Запуск с поддержкой DevTools при флаге debug
        webview.start(debug=debug)
        logger.info("Приложение DovahScribe штатно завершило работу.")
    except Exception as e:
        logger.exception("Критическая ошибка работы окна DovahScribe:")
        if sys.stdout is not None:
            print(f"❌ Ошибка: {e}")


def parse_arguments() -> tuple[str | None, bool]:
    """Разбор аргументов командной строки."""
    args = sys.argv[1:]
    is_debug = "--debug" in args or "-d" in args
    clean_args = [a for a in args if not a.startswith("-")]
    mod_name = clean_args[0] if clean_args else None
    return mod_name, is_debug


if __name__ == "__main__":
    mod, is_dbg = parse_arguments()
    launch_app(mod, debug=is_dbg)

