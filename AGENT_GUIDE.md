# 🐉 DovahScribe — Руководство для AI-Агентов (Agent Guide)

Этот документ предназначен для любых сторонних ИИ-агентов (Gemini, Claude Code, Cursor, Cline, Windsurf, Antigravity), работающих с репозиторием **DovahScribe**.

---

## 🧭 Назначение и архитектура

**DovahScribe** — интеллектуальный комплекс CAT-локализации плагинов The Elder Scrolls V: Skyrim.

### Основной пайплайн:
```
[ESP/ESM/ESL] ──► 1. Extract ──► 2. Match (Vanilla/TM) ──► 3. Review JSON ──► 4. AI Translate (Context Window) ──► 5. Quality Gate ──► 6. Patch & Deploy
```

---

## 🛠️ Команды управления CLI (`translate.py`)

Агент может запускать отдельные стадии или полный цикл:

```bash
# 1. Извлечение строк и контекста диалогов из мода
python translate.py --step extract --plugin <ModName.esp>

# 2. Быстрое сопоставление с ванильной базой (68 000 строк, 0 токенов)
python translate.py --step match --plugin <ModName.esp>

# 3. Аудит качества и поиск языковых утечек
python translate.py --step audit --plugin <ModName.esp>

# 4. Сборка патча изменений (housecarl_apply)
python translate.py --step patch --plugin <ModName.esp>

# 5. Деплой мода в Mod Organizer 2 (<ModName> [RU])
python translate.py --step deploy --plugin <ModName.esp>

# 6. Запуск десктопного CAT-интерфейса
python app.py <ModName>
```

---

## 📄 Структура рабочего файла `data/review/{mod}_review.json`

Все стадии обмениваются данными через стандартизированный файл ревью:

```json
{
  "metadata": {
    "mod_name": "SexLabDefeat",
    "exported_at": "2026-09-23T00:00:00Z",
    "total_strings": 1420,
    "ready_count": 1420
  },
  "entries": [
    {
      "id": 1,
      "formid": "00134BA7:SexLabDefeat.esp",
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
