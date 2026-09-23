# 🐉 DovahScribe — Руководство для AI-Агентов (Agent Guide)

Этот документ предназначен для любых сторонних ИИ-агентов (Gemini, Claude Code, Cursor, Cline, Windsurf, Antigravity), работающих с репозиторием **DovahScribe**.

---

## 🧭 Назначение и архитектура

**DovahScribe** — интеллектуальный комплекс CAT-локализации плагинов The Elder Scrolls V: Skyrim.

### ⚠️ КРИТИЧЕСКИЙ ПРОТОКОЛ ДЛЯ ИИ-АГЕНТА:
1. **Никогда не начинай автоматическое извлечение или перевод реальных плагинов из Mod Organizer 2 без прямого указания пользователя!**
2. Если пользователь говорит «давай обкатаем», «проверь как работает» или «запусти пайплайн» без названия мода — **сначала спроси пользователя**, какой конкретно плагин он хочет локализовать, либо предложи запустить проверку системы через `python -m unittest discover -s tests -v`.
3. Запрещено произвольно перебирать моды из активного лоад-ордера MO2.

### 🏰 Взаимодействие с HouseCARL MCP:
- MCP-сервер `housecarl` автоматически связан с активным профилем Mod Organizer 2 и экземпляром Skyrim.
- Агенту **не нужно** вручную конфигурировать или прописывать пути к директории игры или папкам MO2 — HouseCARL определяет их автоматически.
- Если пользователю требуется помощь с выбором установленного мода, агент может вызвать `housecarl_load_order_status` и вежливо предложить список активных плагинов на выбор.

### 📋 ОБЯЗАТЕЛЬНЫЙ РЕГЛАМЕНТ РАБОТЫ АГЕНТА (5-STEP WORKFLOW):
Когда пользователь даёт команду перевести конкретный мод (например, `CustomMod.esp`), агент обязан строго последовательно выполнить следующие шаги:

1. **Шаг 1. Дамп в `.jsonl` (Extraction):**
   - Вызвать `housecarl_records` (или `python translate.py --step extract --plugin CustomMod.esp`).
   - Сохранить дамп в `data/raw_extracted/CustomMod_raw.jsonl`.
2. **Шаг 2. Сопоставление по ванильной базе Скайрима (Vanilla Matcher):**
   - Запустить `python translate.py --step match --plugin CustomMod.esp` (или внутренний `VanillaMatcher`).
   - Моментально и бесплатно (0 токенов) сопоставить все строки по 68 000 оригинальным строкам официального Skyrim (Skyrim, Update, Dawnguard, Hearthfires, Dragonborn).
3. **Шаг 3. Проверка локального словаря мода (Translation Memory):**
   - Проверить наличие `data/mod_translations/CustomMod.json` (словарь от прошлых версий перевода).
   - Если мод обновлялся, автоматически подтянуть уже переведенные строки прошлых версий.
4. **Шаг 4. AI-Перевод оставшихся непереведённых строк:**
   - Сформировать пакеты контекста с учётом диалоговых веток, пола спикера (`speaker_context.gender`) и лора TES.
   - Перевести только оставшиеся строки со статусом `pending`.
   - Записать готовый файл ревью в `data/review/CustomMod_review.json`.
5. **Шаг 5. Открытие интерактивного превью:**
   - Запустить десктопное приложение `DovahScribe.exe` (или `python app.py CustomMod`), чтобы пользователь мог визуально просмотреть и отредактировать строки в красивом CAT-дашборде.

---

## 🛠️ Команды управления CLI (`translate.py`)

Агент может запускать отдельные стадии или полный цикл:

```bash
# 1. Извлечение строк и контекста диалогов из мода
python translate.py --step extract --plugin <ModName.esp>

# 2. Быстрое сопоставление с ванильной базой (68 000 строк, 0 токенов) и TM
python translate.py --step match --plugin <ModName.esp>

# 3. Аудит качества и поиск языковых утечек
python translate.py --step audit --plugin <ModName.esp>

# 4. Сборка патча изменений (housecarl_apply)
python translate.py --step patch --plugin <ModName.esp>

# 5. Деплой мода в Mod Organizer 2 (<ModName> [RU])
python translate.py --step deploy --plugin <ModName.esp>

# 6. Запуск десктопного CAT-интерфейса / превью
python app.py <ModName>
# или запуск скомпилированного DovahScribe.exe
```

---

## 📄 Структура рабочего файла `data/review/{mod}_review.json`

Все стадии обмениваются данными через стандартизированный файл ревью:

```json
{
  "metadata": {
    "mod_name": "SampleMod",
    "exported_at": "2026-09-23T00:00:00Z",
    "total_strings": 1420,
    "ready_count": 1420
  },
  "entries": [
    {
      "id": 1,
      "formid": "00134BA7:SampleMod.esp",
      "type": "DialogTopic",
      "field": "Name",
      "speaker": "🗣️ ♀ Lydia",
      "topic": "DialogueTopicPrompt",
      "speaker_context": {
        "gender": "female",
        "speaker_name": "Lydia",
        "role": "npc",
        "dialect_type": "standard",
        "badge": "🗣️ ♀ Lydia"
      },
      "original": "I am sworn to carry your burdens.",
      "translated": "Я поклялась нести твою ношу.",
      "source": "ai_agent",
      "quality_status": "ok",
      "quality_issue": null
    }
  ]
}
```

---

## 🛡️ Правила локализации для ИИ-Агента (Quality Rules)

1. **Грамматический род спикера:** Всегда проверяйте `speaker_context.gender`. Если `female` — все глаголы прошедшего времени и причастия должны быть в женском роде (*«Я нашла»*, *«Я готова»*).
2. **Защита тегов (Tag Parity):** Запрещено удалять или переводить теги `<ALIAS=...>`, `<Global=...>`, `<font color=...>`, `[pagebreak]`, спецификаторы `%s`, `%d`, `%f`.
3. **Каноничный лор TES:** Соблюдайте официальный словарь терминов (Даэдрические Принцы, 9 Божеств, школы магии, расы, города).
4. **Anti-Trap правила:**
   - `Race` ➔ `Раса` (никогда не *«гонка»*)
   - `Staff` ➔ `Посох` (никогда не *«персонал»*)
   - `Follower` ➔ `Спутник` (никогда не *«подписчик»*)
   - `Cast` ➔ `Сотворение / Каст` (никогда не *«гипс»*)
   - `Chest` ➔ `Сундук` (никогда не *«грудь»*)
   - `Hostile` ➔ `Враждебный` (никогда не *«хостел»*)

---

## 📦 Развертывание и зависимости

- Python 3.11+ (рекомендуется Python 3.12/3.13)
- Установка зависимостей: `pip install -r requirements.txt`
- Конфигурация путей: скопировать `.env.example` ➔ `.env`

---

## 🏰 Интеграция с Housecarl MCP (Для AI-Агентов)

Для полного цикла низкоуровневой работы с бинарными плагинами Bethesda (`.esp`/`.esm`/`.esl`) и компиляции Papyrus-скриптов используется MCP-сервер **houseCARL**:
- **Официальный репозиторий:** [Avick3110/houseCARL (GitHub)](https://github.com/Avick3110/houseCARL)
- **Лицензия:** GPL-3.0-only.
- **Модель взаимодействия:** DovahScribe является независимым клиентом и взаимодействует с Housecarl исключительно через стандартизированный протокол Model Context Protocol (MCP) по JSON-RPC (`stdio`), не включая бинарники и код Housecarl в свой состав.

Если ваш агент поддерживает протокол MCP (Model Context Protocol), подключите сервер Housecarl (пример конфигурации в [`mcp_config.example.json`](file:///H:/Ai/Lain_Ai/Skyrim_translator/mcp_config.example.json)):

### Ключевые MCP-инструменты конвейера:
1. **`housecarl_records` (Выгрузка данных из ESP/ESM/ESL):**
   - Вызывается для получения сырого дампа плагина.
   - Скрипт `src/io_utils.py` генерирует оптимизированный запрос:
     ```json
     {
       "plugin": "SampleMod.esp",
       "types": ["ARMO", "WEAP", "BOOK", "INFO", "DIAL", "QUST", "NPC_", "SPEL", "MGEF"],
       "to_file": "data/raw_extracted/SampleMod_raw.json"
     }
     ```
2. **`housecarl_apply` (Бинарная сборка патча):**
   - Модуль `src/patcher.py` формирует проверенный манифест `data/patches/{mod}_ops.json`.
   - Агент вызывает инструмент:
     ```json
     {
       "plugin": "SampleMod.esp",
       "patch_manifest": "data/patches/SampleMod_ops.json"
     }
     ```

3. **`housecarl_decompile_script` / `housecarl_compile_script` (Скрипты Papyrus):**
   - Используются для декомпиляции, извлечения строковых литералов и обратной компиляции бинарных `.pex` файлов.


