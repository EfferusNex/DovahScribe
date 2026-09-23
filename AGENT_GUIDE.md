# 🐉 DovahScribe — AI Agent Operational Guide

This document is designed for AI coding agents (Gemini, Claude Code, Cursor, Cline, Windsurf, Antigravity) operating in the **DovahScribe** repository.

---

## 🧭 Purpose & Architectural Overview

**DovahScribe** is an intelligent Computer-Assisted Translation (CAT) & localization engine for **The Elder Scrolls V: Skyrim** plugins (`.esp`, `.esm`, `.esl`) and SkyUI MCM configs.

---

## ⚠️ CRITICAL OPERATIONAL PROTOCOL

1. **NEVER automatically extract, modify, or translate random plugins from Mod Organizer 2 without explicit user instruction!**
2. If the user says *"let's test"*, *"run the pipeline"*, or *"try translating"* without specifying a target mod name:
   - **Ask the user** which specific plugin they want to translate.
   - Alternatively, offer to run the self-contained test suite via: `python -m unittest discover -s tests -v`.
3. Do not randomly scan or pick plugins from the active MO2 load order without user confirmation.

---

## 🏰 HouseCARL MCP Integration

- The `housecarl` MCP server connects directly to the user's active Mod Organizer 2 instance and Skyrim game directory.
- **Paths are resolved automatically:** The agent does NOT need to manually configure or hardcode game directories or MO2 mod folders.
- If the user needs help picking an installed mod, invoke `housecarl_load_order_status` to list available active plugins and present the list for the user to choose from.

---

## 📋 MANDATORY 7-STEP TRANSLATION LIFECYCLE

When the user specifies a plugin to translate (e.g. `SampleMod.esp`), execute the following steps in sequence:

### Step 1. Raw Extraction (`.jsonl`)
- Query plugin records using `housecarl_records` (or execute `python translate.py --step extract --plugin SampleMod.esp`).
- Save the raw dump to `data/raw_extracted/SampleMod_raw.jsonl`.
- Extract SkyUI MCM translation files (`Interface/Translations/SampleMod_ENGLISH.txt`) if present.

### Step 2. Vanilla Skyrim Base Matching (0 Tokens)
- Run `python translate.py --step match --plugin SampleMod.esp` (or internal `VanillaMatcher`).
- Instantly matches against the official 68,000-entry canonical Russian Skyrim dictionary (`Skyrim`, `Update`, `Dawnguard`, `Hearthfires`, `Dragonborn`) with zero token consumption.

### Step 3. Translation Memory Lookup (Mod Translation Memory)
- Check for existing `data/mod_translations/SampleMod.json`.
- If the mod was previously translated or updated, pull in existing verified translations automatically.

### Step 4. Contextual AI Translation (Pending Strings)
- Assemble contextual packages containing dialogue branches, speaker metadata (`speaker_context.gender`, `speaker_context.role`), and Elder Scrolls lore rules.
- Translate only the remaining `pending` strings into natural, lore-accurate Russian.
- Export the intermediate review manifest to `data/review/SampleMod_review.json`.

### Step 5. Launch Interactive Preview & ENTER STANDBY MODE
- Launch the native desktop CAT dashboard in a non-blocking Windows process:
  ```powershell
  Start-Process -FilePath "python" -ArgumentList "app.py SampleMod"
  # or via compiled binary:
  Start-Process -FilePath ".\DovahScribe.exe" -ArgumentList "SampleMod"
  ```
- **CRITICAL (Standby Requirement):** Notify the user that the editor window is open, and **PAUSE execution**. Do NOT proceed to patching or deployment until the user has reviewed their strings.
- Example message to user:
  > *"DovahScribe Desktop Review Window is now open for `SampleMod`! You can inspect and edit translations in the CAT interface (Ctrl+S to save). When you are satisfied and close the window, let me know with 'Ready' or 'Deploy' to package and deploy the patch to MO2!"*

### Step 6. Binary Patch Packaging
- After the user confirms review completion, execute:
  ```powershell
  python translate.py --step patch --plugin SampleMod.esp
  ```
- Builds the operation manifest `data/patches/SampleMod_ops.json` and patches the binary via `housecarl_apply`.

### Step 7. Automated MO2 Deployment & Load Order Priority
- Deploy the localized mod into Mod Organizer 2:
  ```powershell
  python translate.py --step deploy --plugin SampleMod.esp
  ```
- The deployment script automatically:
  1. Creates an isolated mod folder in Mod Organizer 2: `mods/SampleMod [RU]/`.
  2. Places patched binaries and Russian MCM translation files into the directory.
  3. **Appends the mod to MO2 `modlist.txt` with highest priority AFTER the original plugin**, guaranteeing the translation wins all asset conflicts.

---

## 🛠️ CLI Management Commands (`translate.py`)

Individual pipeline stages can be invoked directly:

```bash
# 1. Extract strings and dialogue context
python translate.py --step extract --plugin <ModName.esp>

# 2. Match against official vanilla dictionary (68k strings) & Translation Memory
python translate.py --step match --plugin <ModName.esp>

# 3. Audit translation quality & check for English leaks
python translate.py --step audit --plugin <ModName.esp>

# 4. Build binary patch via housecarl_apply
python translate.py --step patch --plugin <ModName.esp>

# 5. Deploy localized mod to Mod Organizer 2 (<ModName> [RU])
python translate.py --step deploy --plugin <ModName.esp>

# 6. Launch Desktop CAT Dashboard / Preview Window
python app.py <ModName>
```

---

## 📄 Review File Schema (`data/review/{mod}_review.json`)

All stages communicate through standardized JSON review files:

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

## 🛡️ Localization Quality Rules for AI Agents

1. **Speaker Grammatical Gender:** Always check `speaker_context.gender`. When `female`, past-tense verbs and participles in first-person speech must use feminine grammatical inflections (*«Я нашла»*, *«Я готова»*).
2. **Tag Parity & Preservation:** Never alter or strip engine placeholder tags: `<ALIAS=...>`, `<Global=...>`, `<font color=...>`, `[pagebreak]`, or formatting specifiers `%s`, `%d`, `%f`.
3. **Canonical TES Lore:** Adhere to the official Russian localization terminology (Daedric Princes, Divines, Magic Schools, Races, Holds, Cities).
4. **Anti-Trap Glossary Enforcement:**
   - `Race` ➔ `Раса` (never *«гонка»*)
   - `Staff` ➔ `Посох` (never *«персонал»*)
   - `Follower` ➔ `Спутник` (never *«подписчик»*)
   - `Cast` ➔ `Сотворение / Каст` (never *«гипс»*)
   - `Chest` ➔ `Сундук` (never *«грудь»*)
   - `Hostile` ➔ `Враждебный` (never *«хостел»*)

---

## 📦 Verification & Test Execution

Run the internal unit test suite to verify system integrity before or after any modifications:

```powershell
python -m unittest discover -s tests -v
python tests/test_current_state.py
```
