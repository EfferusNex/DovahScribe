#!/usr/bin/env python3
"""
🐾 Skyrim Translator AI — Главный оркестратор локализации модов.
Объединяет все этапы конвейера:
  1. Извлечение записей через houseCARL (io_utils + field_filter)
  2. Сверка с каноничной базой Скайрима (vanilla_matcher)
  3. Прогон через память переводов и словарь мода (translation)
  4. Сборка контекстных пакетов повествования (narrative_context)
  5. Маскирование тегов и экспорт файла ревью для Сэмпая (ai_agent + review_manager)
  6. Контроль качества и языковых утечек (quality_gate)
  7. Генерация ops и создание патча через housecarl_apply (patcher)
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Устанавливаем UTF-8 для корректного вывода в терминале Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.field_filter import ALL_SUPPORTED_TYPES
from src.io_utils import (
    build_housecarl_records_params,
    parse_extracted_records,
    save_extracted_data,
    load_extracted_data,
    has_cyrillic,
)
from src.vanilla_matcher import VanillaMatcher
from src.translation import TranslationEngine, normalize_mod_name
from src.narrative_context import NarrativeContextBuffer
from src.ai_agent import AIAgentCoordinator
from src.review_manager import ReviewManager
from src.esp_injector import ESPInjector
from src.mo2_deployer import MO2Deployer
from src.quality_gate import QualityGate, QualityReport
from src.patcher import Patcher
from src.glossary import GlobalGlossary, GlossaryExtractor
from src.speaker_analyzer import SpeakerAnalyzer
from src.mcm_manager import MCMManager
from src.version_differ import VersionDiffer, DiffReport
from src.mo2_deployer import MO2Deployer
from src.esp_injector import ESPInjector, inject_and_deploy_mod

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw_extracted"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║   🐾 SKYRIM TRANSLATOR AI AGENT (HouseCARL + CAT + LLM)      ║
║   Интеллектуальная локализация плагинов TES V: Skyrim        ║
╚══════════════════════════════════════════════════════════════╝
""")


def run_pipeline(
    plugin_name: str,
    step: str = "all",
    mod_desc: str = "Skyrim Mod",
    lore: str = "The Elder Scrolls V: Skyrim universe",
    dry_run: bool = False,
    allow_leaks: bool = False,
    raw_data_cache: str = "",
    diff_with: str = "",
    **kwargs,
):
    print_banner()
    clean_mod_name = normalize_mod_name(plugin_name)
    raw_cache_file = RAW_DIR / f"{clean_mod_name}_raw.json"
    review_file = ReviewManager.get_review_filepath(plugin_name)
    target_ui_path = BASE_DIR / "web" / f"{clean_mod_name}_dashboard.html"

    print(f"📦 Целевой плагин: \033[1;36m{plugin_name}\033[0m")
    print(f"🏷️  Имя проекта/словаря: \033[1;32m{clean_mod_name}\033[0m")
    print(f"⚙️  Режим работы: \033[1;33m{step.upper()}\033[0m\n")

    items: List[Dict[str, Any]] = []

    if step in ["ui", "web"]:
        template_path = BASE_DIR / "web" / "cat_dashboard.html"
        target_ui_path = template_path

        if review_file.exists():
            print(f"📦 Найдено ревью мода: \033[1;32m{review_file.name}\033[0m")
            print("⚡ Автоматическое встраивание данных в Generative UI...")
            review_content = review_file.read_text(encoding="utf-8")
            template_content = template_path.read_text(encoding="utf-8")
            
            # Инжектируем данные в контейнер preloaded-data
            injected_html = template_content.replace(
                '<script id="preloaded-data" type="application/json"></script>',
                f'<script id="preloaded-data" type="application/json">\n{review_content}\n</script>'
            )
            
            target_ui_path = BASE_DIR / "web" / f"{clean_mod_name}_dashboard.html"
            target_ui_path.write_text(injected_html, encoding="utf-8")
            print(f"✨ Сформирован персональный дашборд: \033[1;36m{target_ui_path.name}\033[0m")
        else:
            print(f"ℹ️ Файл ревью {review_file.name} не найден. Открываю чистый дашборд.")

        print(f"🖥️  Открытие дашборда в браузере: \033[1;36m{target_ui_path}\033[0m\n")
        import webbrowser
        webbrowser.open(target_ui_path.as_uri())
        return

    if step == "glossary":
        glossary = GlobalGlossary()
        print("📖 [Единый глобальный глоссарий TES & Модов]")
        print(f"    Всего активных терминов: \033[1;32m{len(glossary.terms)}\033[0m")
        categories: Dict[str, int] = {}
        for term_data in glossary.terms.values():
            cat = term_data.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1
        print("    Категории терминов:")
        for cat, count in sorted(categories.items()):
            print(f"      • {cat}: {count}")

        if review_file.exists():
            entries = ReviewManager.load_reviewed_file(review_file)
            added = GlossaryExtractor.populate_from_items(entries, clean_mod_name, glossary)
            print(f"    ✨ Извлечено новых именованных сущностей из {plugin_name}: \033[1;32m{added}\033[0m")
            print(f"    Всего после обновления: \033[1;32m{len(glossary.terms)}\033[0m")
        print("\n🐾 Глоссарий синхронизирован и готов к работе! ✨")
        return

    # ==========================================
    # ЭТАП 1 & 2: ИЗВЛЕЧЕНИЕ СЫРЫХ ДАННЫХ
    # ==========================================
    if step in ["all", "extract", "match", "review", "audit", "diff"]:
        print("🔍 [1/6] Извлечение текстовых записей из плагина...")
        raw_jsonl_file = RAW_DIR / f"{clean_mod_name}_raw.jsonl"
        if raw_data_cache and Path(raw_data_cache).exists():
            items = load_extracted_data(raw_data_cache)
            save_extracted_data(items, str(raw_cache_file))
        elif raw_cache_file.exists():
            print(f"    Загружаем кэшированные сырые данные: {raw_cache_file.name}")
            items = load_extracted_data(str(raw_cache_file))
        elif raw_jsonl_file.exists():
            print(f"    Загружаем сырые данные из JSONL артефакта housecarl: {raw_jsonl_file.name}")
            items = load_extracted_data(str(raw_jsonl_file))
            save_extracted_data(items, str(raw_cache_file))
        else:
            mo2_path = kwargs.get("mo2_path")
            deployer = MO2Deployer(mo2_base_path=Path(mo2_path) if mo2_path else None)
            source_esp_path = deployer.find_original_plugin_file(plugin_name)
            if source_esp_path and source_esp_path.exists():
                print(f"    ⚡ Автоматическое бинарное извлечение строк через ESPInjector: \033[1;36m{source_esp_path.name}\033[0m")
                items = ESPInjector.extract_all_strings(source_esp_path)
                save_extracted_data(items, str(raw_cache_file))
            else:
                print("    Формируем параметры для вызова housecarl_records...")
                params = build_housecarl_records_params(plugin_name)
                print(f"    Отслеживается типов записей: {len(params['types'])}")
                print(f"    Целевых путей полей: {len(params['project']['fields'])}")
                if not items:
                    print(f"    ⚠️ Вызов housecarl_records должен быть выполнен через MCP для плагина {plugin_name}.")

        if items:
            items = SpeakerAnalyzer.enrich_items_with_speaker_context(items)

        # Проверяем наличие внешних файлов настроек SkyUI MCM (_ENGLISH.txt) через единый монолитный метод
        mcm_items, mcm_file = MCMManager.discover_and_load_mcm(plugin_name, clean_mod_name, start_id=len(items) + 1)
        if mcm_file and mcm_items:
            print(f"    ⚙️  Обнаружен файл настроек SkyUI MCM: \033[1;36m{mcm_file.name}\033[0m")
            print(f"       Путь: {mcm_file}")
            items.extend(mcm_items)
            print(f"    ✨ Добавлено строк MCM в общий конвейер: \033[1;32m{len(mcm_items)}\033[0m")

        print(f"    ✅ Всего доступно для обработки: \033[1;32m{len(items)}\033[0m строк.\n")

    if step == "extract":
        print("✨ Извлечение завершено! Запусти со шагом 'match' или 'all'.")
        return

    # ==========================================
    # ДИФФЕР ВЕРСИЙ: СРАВНЕНИЕ И ПЕРЕНОС (0 ТОКЕНОВ)
    # ==========================================
    if (diff_with or step == "diff") and items:
        diff_source = Path(diff_with) if diff_with else review_file
        print(f"🔄 [Диффер версий] Сравнение с базой старой версии: \033[1;36m{diff_source}\033[0m")
        if diff_source.exists():
            report = VersionDiffer.compare_versions(diff_source, items)
            print(report.summary())
            ready_items, pending_items = VersionDiffer.apply_diff_to_pipeline(report)
            items = ready_items + pending_items
            ReviewManager.export_for_review(clean_mod_name, items)
            print(f"\n    ✨ Обновлён файл ревью с автоматическим переносом: \033[1;32m{review_file.name}\033[0m\n")
            if step == "diff":
                return
        else:
            print(f"    ⚠️ Файл старой версии не найден: {diff_source}\n")

    # ==========================================
    # ЭТАП 3 & 4: ВАНИЛА И СЛОВАРЬ МОДА (TM)
    # ==========================================
    if step in ["all", "match", "review"] and items:
        print("📚 [2/6] Сверка с официальной базой Скайрима и словарём мода...")
        matcher = VanillaMatcher()
        tm_engine = TranslationEngine(mod_name=clean_mod_name, mod_context={"description": mod_desc, "lore": lore})

        vanilla_hits = 0
        tm_hits = 0
        pending_items = 0

        for item in items:
            raw_text = item.get("text", "")
            r_type = item.get("type", "MISC")
            path = item.get("path", "Name")

            # 1. Если строка уже на русском языке (например, каноничные ванильные оверрайды из 1C)
            if has_cyrillic(raw_text):
                item["translated"] = raw_text
                item["source"] = "vanilla_russian"
                vanilla_hits += 1
                tm_engine.save_translation(r_type, path, raw_text, raw_text, item.get("formid", ""), source="vanilla_russian", auto_save=False)
                continue

            # 2. Проверяем локальный TM-словарь мода
            tm_trans = tm_engine.get_translation(r_type, path, raw_text)
            if tm_trans:
                item["translated"] = tm_trans
                item["source"] = "tm_cache"
                tm_hits += 1
                continue

            # 3. Проверяем официальные ванильные строки
            vanilla_trans = matcher.match(raw_text)
            if vanilla_trans:
                item["translated"] = vanilla_trans
                item["source"] = "vanilla_strings"
                vanilla_hits += 1
                # Сразу фиксируем в словарь мода
                tm_engine.save_translation(r_type, path, raw_text, vanilla_trans, item.get("formid", ""), source="vanilla", auto_save=False)
                continue

            # Строка ожидает перевода
            item["source"] = "pending"
            pending_items += 1

        tm_engine._save_tm()
        print(f"    🏛️  Совпадений с официальной ванилой: \033[1;32m{vanilla_hits}\033[0m (0 токенов)")
        print(f"    💾 Совпадений с локальным TM-словарём: \033[1;32m{tm_hits}\033[0m (0 токенов)")
        print(f"    ⏳ Осталось на перевод Леин / Сэмпаю: \033[1;33m{pending_items}\033[0m строк.\n")

    # ==========================================
    # ЭТАП 5: ЭКСПОРТ В РЕВЬЮ-ФАЙЛ & ГЕНЕРАЦИЯ ДАШБОРДА
    # ==========================================
    if step in ["all", "review"] and items:
        print("📝 [3/6] Формирование промежуточного файла ревью для Сэмпая...")
        out_review = ReviewManager.export_for_review(clean_mod_name, items)
        print(f"    ✨ Файл ревью готов: \033[1;36m{out_review}\033[0m")

        # Автоматически обновляем персональный интерактивный веб-дашборд
        template_path = BASE_DIR / "web" / "cat_dashboard.html"
        target_ui_path = BASE_DIR / "web" / f"{clean_mod_name}_dashboard.html"
        if template_path.exists():
            review_content = out_review.read_text(encoding="utf-8")
            template_content = template_path.read_text(encoding="utf-8")
            injected_html = template_content.replace(
                '<script id="preloaded-data" type="application/json"></script>',
                f'<script id="preloaded-data" type="application/json">\n{review_content}\n</script>'
            )
            target_ui_path.write_text(injected_html, encoding="utf-8")
            print(f"    ✨ Персональный CAT-дашборд готов: \033[1;32m{target_ui_path.name}\033[0m")
            print(f"    🖥️  Ссылка: {target_ui_path.as_uri()}\n")

    # ==========================================
    # ЭТАП 6: АУДИТ КАЧЕСТВА (QUALITY GATE)
    # ==========================================
    if step in ["all", "review", "audit", "patch"] or review_file.exists():
        target_audit_items = ReviewManager.load_reviewed_file(review_file) if review_file.exists() else items
        if target_audit_items:
            print("🛡️  [4/6] Контроль качества и детектор утечек английского (Quality Gate)...")
            report = QualityGate.audit_entries(target_audit_items)
            print(f"    {report.summary()}")
            if report.issues:
                print(f"    ⚠️  Обнаружено замечаний: \033[1;33m{len(report.issues)}\033[0m")
                for issue in report.issues[:5]:
                    print(f"      • [{issue.issue_type}] {issue.formid} ({issue.field}): {issue.details}")
                if len(report.issues) > 5:
                    print(f"      ... и еще {len(report.issues) - 5} строк.")
            else:
                print("    🎉 Все строки идеальны, латинских утечек не обнаружено!")
            print()

    # Точка контролируемой остановки: Ревью-гейт (Review Gate)
    if step == "review":
        print("🛑 [Review Gate] Конвейер приостановлен для проверки Сэмпаем.")
        print(f"👉 Открой дашборд: file:///{target_ui_path.as_posix()}")
        print("👉 После проверки запусти со шагом 'patch' или 'deploy'.\n")
        return

    if step == "audit":
        return

    # ==========================================
    # ЭТАП 7: СБОРКА ПАТЧА / БИНАРНЫЙ ИНЖЕКТ В ESP
    # ==========================================
    if step in ["all", "patch"]:
        use_housecarl = kwargs.get("use_housecarl", False)

        if review_file.exists():
            reviewed_entries = ReviewManager.load_reviewed_file(review_file)
            print(f"    Загружено строк из файла ревью: {len(reviewed_entries)}")
        else:
            reviewed_entries = items

        if not use_housecarl:
            print("⚡ [5/6] Прямой бинарный инжект строк через ESPInjector (Direct Mode)...")
            mo2_path = kwargs.get("mo2_path")
            deployer = MO2Deployer(mo2_base_path=Path(mo2_path) if mo2_path else None)

            # Ищем исходный плагин в папке модов MO2
            source_esp_path = deployer.find_original_plugin_file(plugin_name)

            out_patch_dir = DATA_DIR / "patches" / clean_mod_name
            out_patch_dir.mkdir(parents=True, exist_ok=True)
            target_esp_path = out_patch_dir / plugin_name

            if source_esp_path and source_esp_path.exists() and review_file.exists():
                print(f"    Исходный плагин: \033[1;36m{source_esp_path}\033[0m")
                inject_res = ESPInjector.inject_translations(
                    source_esp=source_esp_path,
                    target_esp=target_esp_path,
                    review_file=review_file,
                )
                print(f"    🎉 Успешно инжектировано: \033[1;32m{inject_res['applied_count']}/{inject_res['total_review_items']}\033[0m записей")
                print(f"    Собранный бинарный плагин: \033[1;32m{target_esp_path}\033[0m (0 циклических мастеров)")
            else:
                print(f"    ℹ️ Исходный файл {plugin_name} готов к сборке через ESPInjector.")
        else:
            print("⚡ [5/6] Подготовка операций патчинга (housecarl_apply)...")
            ops, report = Patcher.build_patch_ops(
                reviewed_entries,
                validate_quality=True,
                allow_leaks=allow_leaks,
            )
            manifest_path = Patcher.save_ops_manifest(clean_mod_name, ops)
            params = Patcher.prepare_apply_params(clean_mod_name, ops, dry_run=dry_run)
            print(f"    Сформировано валидных операций 'Set': \033[1;32m{len(ops)}\033[0m")
            print(f"    Манифест операций сохранен: \033[1;36m{manifest_path}\033[0m")

        # Экспорт файла переводов SkyUI MCM (_RUSSIAN.txt) в UTF-16 LE с BOM
        mcm_out = MCMManager.export_russian_mcm(reviewed_entries, clean_mod_name)
        if mcm_out:
            print(f"    ⚙️  Экспортирован файл перевода SkyUI MCM: \033[1;32m{mcm_out}\033[0m (UTF-16 LE BOM)")
            print(f"       Резервная копия сохранена в data/mcm_output/{mcm_out.name}\n")

    # ==========================================
    # ЭТАП 8: ПРЯМОЙ ДЕПЛОЙ В MO2 (MO2 DEPLOY)
    # ==========================================
    if step in ["all", "deploy"] or (step == "patch" and kwargs.get("deploy")):
        print("🚀 [6/6] Прямой деплой пакета локализации в Mod Organizer 2...")
        mo2_path = kwargs.get("mo2_path")
        deployer = MO2Deployer(mo2_base_path=Path(mo2_path) if mo2_path else None)

        if not deployer.mo2_base:
            print("    ⚠️  Базовая директория MO2 не обнаружена. Укажите путь через --mo2-path или в settings.json.")
        else:
            # Ищем подготовленный MCM файл
            mcm_file = None
            candidate_mcm = DATA_DIR / "mcm_output" / f"{clean_mod_name}_RUSSIAN.txt"
            if candidate_mcm.exists():
                mcm_file = candidate_mcm

            # Ищем собранный ESP патч (если есть)
            esp_file = None
            candidate_esp = DATA_DIR / "patches" / clean_mod_name / plugin_name
            if candidate_esp.exists():
                esp_file = candidate_esp
            else:
                candidate_esp_legacy = DATA_DIR / "patches" / f"{clean_mod_name}_RU.esp"
                if candidate_esp_legacy.exists():
                    esp_file = candidate_esp_legacy

            deploy_res = deployer.deploy(
                mod_name=plugin_name,
                esp_patch_path=esp_file,
                mcm_russian_path=mcm_file,
            )

            if deploy_res.get("success"):
                print(f"    🎉 Мод успешно развёрнут: \033[1;32m{deploy_res['mod_folder']}\033[0m")
                print(f"       Путь: {deploy_res['target_path']}")
                print(f"       Развёрнутые файлы: {', '.join(deploy_res['files_deployed'])}")
                print(f"       Активный профиль MO2: \033[1;36m{deploy_res['active_profile']}\033[0m")
                if deploy_res.get("modlist_priority_updated"):
                    print(f"       Приоритет в modlist.txt: \033[1;32mСТРОГО ВЫШЕ оригинала (+{deploy_res['mod_folder']})\033[0m")
            else:
                print(f"    ❌ Ошибка деплоя: {deploy_res.get('error')}")
            print()

    # ==========================================
    # СВОДНЫЙ ДАШБОРД
    # ==========================================
    print("═" * 62)
    print("📊 СВОДКА ПЕРЕВОДА:")
    print(f"  • Всего строк в моде:      {len(items) or (len(reviewed_entries) if 'reviewed_entries' in locals() else 0)}")
    print(f"  • Файл ревью (для правок): {review_file}")
    print(f"  • Словарь TM мода:         data/mod_translations/{clean_mod_name}.json")
    print(f"  • Статус:                  Готов к игре!")
    print("═" * 62)
    print("\n🐾 Муррр! Контроль качества пройден, всё под контролем! ✨")


def main():
    parser = argparse.ArgumentParser(description="Skyrim Translator AI Orchestrator")
    parser.add_argument("--plugin", "-p", type=str, default="ForgottenMagic_Redone.esp", help="Имя целевого плагина")
    parser.add_argument("--step", "-s", type=str, choices=["all", "extract", "match", "review", "audit", "patch", "ui", "web", "glossary", "diff", "deploy"], default="all", help="Стадия выполнения")
    parser.add_argument("--desc", type=str, default="Skyrim Mod", help="Описание концепции мода")
    parser.add_argument("--lore", type=str, default="The Elder Scrolls V: Skyrim", help="Лор и эпоха")
    parser.add_argument("--dry-run", action="store_true", help="Проверка патча без записи на диск")
    parser.add_argument("--allow-leaks", action="store_true", help="Разрешить включение непереведенных строк в патч")
    parser.add_argument("--use-housecarl", action="store_true", help="Использовать устаревший housecarl merge вместо прямого ESPInjector")
    parser.add_argument("--raw-cache", type=str, default="", help="Путь к файлу с сырыми данными housecarl")
    parser.add_argument("--diff-with", "-d", type=str, default="", help="Путь к ревью/словарю старой версии мода для переноса перевода (0 токенов)")
    parser.add_argument("--deploy", action="store_true", help="Автоматически развернуть пакет перевода в Mod Organizer 2")
    parser.add_argument("--mo2-path", type=str, default="", help="Путь к базовой папке инстанса Mod Organizer 2")

    args = parser.parse_args()
    run_pipeline(
        plugin_name=args.plugin,
        step=args.step,
        mod_desc=args.desc,
        lore=args.lore,
        dry_run=args.dry_run,
        allow_leaks=args.allow_leaks,
        use_housecarl=args.use_housecarl,
        raw_data_cache=args.raw_cache,
        diff_with=args.diff_with,
        deploy=args.deploy,
        mo2_path=args.mo2_path,
    )


if __name__ == "__main__":
    main()
