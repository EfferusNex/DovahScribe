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

## 🏰 HouseCARL MCP Server (Prerequisites & Setup)

DovahScribe relies on the **houseCARL MCP Server** for low-level interaction with Bethesda plugins (`.esp`, `.esm`, `.esl`), record parsing, and binary patching.

### 1. Verify HouseCARL MCP Availability:
- The agent should check if `housecarl_*` tools (e.g. `housecarl_records`, `housecarl_apply`, `housecarl_load_order_status`) are present in its active MCP tool list.
- **If available:** Proceed directly with the workflow. The MCP server automatically detects the user's active Mod Organizer 2 profile and Skyrim installation — **no manual path configuration is required**.
- **If NOT available:** 
  - Install and register the HouseCARL MCP server in your AI client environment (Antigravity, Gemini, Claude Desktop, Cursor, Cline, Windsurf).
  - Refer to `mcp_config.example.json` in the root of this repository.
  - Official Repository: [Avick3110/houseCARL (GitHub)](https://github.com/Avick3110/houseCARL).

### 2. Autonomous Load Order Discovery:
- When the user asks for available mods, run `housecarl_load_order_status` to fetch active plugins from MO2 and display a friendly list for the user to select from.

---

## 📋 MANDATORY TRANSLATION LIFECYCLE & WORKFLOW MODES

Depending on user intent, select the appropriate execution path:

### 🌟 Mode A: End-to-End Autonomous Translation (Default: *"Translate / Локализуй мод <ModName>"*)
Follow the complete 7-step lifecycle. **Do NOT stop at Step 2 (Match)**: the AI agent MUST translate all pending strings in Step 4 before launching the review preview in Step 5.

### 🔍 Mode B: Inspection / Manual CAT Mode (*"Dump strings / Open review for <ModName>"*)
Execute Steps 1–2 (Extract & Match), then immediately launch `app.py` in Step 5, reporting how many strings are ready vs pending for manual user translation.

---

### Step 1. Raw Extraction (`.jsonl` & PEX/VMAD)
- Query plugin records using `housecarl_records` (always specify `"source": "SampleMod.esp"` to disable load-order winner overrides) or execute `python translate.py --step extract --plugin SampleMod.esp`.
- Save the complete raw dump to `data/raw_extracted/SampleMod_raw.jsonl`.
- Extract SkyUI MCM translation files (`Interface/Translations/SampleMod_ENGLISH.txt`) if present.
- **MCM & Script Properties (VMAD / PEX):** Many mods (e.g. Apocalypse, Ordinator, Sacrosanct) store their entire MCM menu configuration in `VMAD` script properties on Quest records rather than `Interface/Translations/`. Always run `PexSafetyEngine.extract_vmad_strings(esp_path)` and inspect `.pex` scripts in BSA/loose files during extraction to capture all UI text.

### Step 2. Vanilla Skyrim Base Matching (0 Tokens)
- Run `python translate.py --step match --plugin SampleMod.esp` (or internal `VanillaMatcher`).
- Instantly matches against the official 72,600+ entry canonical Russian Skyrim dictionary (`Skyrim`, `Update`, `Dawnguard`, `Hearthfires`, `Dragonborn`) with zero token consumption.
- Ingests Cyrillic master overrides directly as `vanilla_russian`.
- Generates the initial review manifest `data/review/SampleMod_review.json` with matched strings marked as `vanilla_strings` / `tm_cache` / `vanilla_russian` and new strings (including safe `VMAD` script properties) marked as `pending`.

### Step 3. Translation Memory Lookup (Mod Translation Memory)
- Automatically integrated into Step 2 (`TranslationEngine`). Pulls verified translations from `data/mod_translations/SampleMod.json`.

### Step 4. Contextual AI Translation (Pending Strings Execution)
> **CRITICAL FOR AI AGENTS IN MODE A:** `translate.py` does not contain an internal LLM API call. The AI Agent operating in the IDE/CLI performs this translation directly!
1. **Read Manifest:** Load `data/review/SampleMod_review.json`.
2. **Identify Pending Entries:** Find all items where `"source": "pending"` or `"translated"` is empty.
3. **Translate Contextually:** Translate the pending English strings into lore-accurate, canonical Russian:
   - Respect `speaker_context.gender` (female grammatical inflections when `female`).
   - Preserve all engine tags (`<ALIAS=...>`, `<font color=...>`, `%s`, `[pagebreak]`).
   - Obey the Elder Scrolls Lore Glossary (Staff -> Посох, Chest -> Сундук, Race -> Раса).
4. **Update Manifest:** Put translated Russian text into `"translated"`, set `"source": "ai_agent"`.
5. **Save Review File:** Write the updated JSON back to `data/review/SampleMod_review.json`.
6. **Audit Quality:** Run `python translate.py --step audit --plugin SampleMod.esp` to verify zero language leaks or broken tags.

### Step 5. Launch Interactive Preview & ENTER STANDBY MODE
- Provide the generated standalone HTML dashboard link (`web/SampleMod_dashboard.html`) and/or launch the native desktop CAT dashboard in a non-blocking Windows process:
  ```powershell
  Start-Process -FilePath "python" -ArgumentList "app.py SampleMod"
  # or via compiled binary:
  Start-Process -FilePath ".\DovahScribe.exe" -ArgumentList "SampleMod"
  ```
- **CRITICAL (Standby Requirement):** Notify the user that the review file and dashboard are ready, summarize stats (e.g. `120 translated, 0 pending, 0 leaks`), and **PAUSE execution**. Do NOT proceed to patching or deployment until the user confirms review.
- Example message to user:
  > *"DovahScribe Review & Dashboard are ready for `SampleMod`! You can inspect and edit translations in the CAT interface (Ctrl+S to save) or dashboard. When you are satisfied, let me know with 'Ready' or 'Deploy' to package and deploy the patch to MO2!"*

### Step 6. Binary Patch Packaging
- After the user confirms review completion, execute:
  ```powershell
  python translate.py --step patch --plugin SampleMod.esp
  ```
- Builds the operation manifest `data/patches/SampleMod_ops.json` and patches the binary via `ESPInjector` / `housecarl_apply`.

### Step 7. Automated MO2 Deployment & Load Order Priority
- Deploy the localized mod into Mod Organizer 2:
  ```powershell
  python translate.py --step deploy --plugin SampleMod.esp
  ```
- The deployment script automatically creates a **single self-contained package** in `mods/<ModName> [RU]/` with all translated assets bundled together:
  ```text
  mods/<ModName> [RU]/
  ├── <ModName>.esp / .esm / .esl         # Direct patched binary (ESPInjector)
  ├── meta.ini                            # MO2 metadata (category: Translations)
  ├── seq/                                # Quest start-enabled sequence (.seq) if original had one
  │   └── *.seq
  ├── scripts/                            # ONLY translated/modified binary scripts (.pex)
  │   └── *.pex
  ├── Source/Scripts/                     # ONLY translated/modified Papyrus script sources (.psc)
  │   └── *.psc
  └── Interface/Translations/             # SkyUI MCM UTF-16 LE translation files
      └── <ModName>_RUSSIAN.txt
  ```
  *(Note: If scripts were NOT modified/translated, do NOT copy them into `[RU]` — let the original mod supply its original unedited files cleanly!)*
- **Inserts `+<ModName> [RU]` into MO2 `modlist.txt` directly above the original mod**, guaranteeing higher priority and clean asset overrides in MO2 VFS without touching original files.

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

# 4. Build binary patch / Direct ESP injection
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

## 📜 Papyrus PEX & VMAD Script Safety Engine (`src/pex_safety.py`)

Many Skyrim mods (including Apocalypse, Ordinator, Sacrosanct, UI mods) configure their MCM menus, HUD displays, notifications, and spell formatters inside **VMAD script properties** on Quest records or compiled **`.pex` scripts**.

### 1. Safety Classification (xTranslator-Style Protection):
- 🔒 **`locked` (`auth: false`):** Script/class names, property names, state names, local variables, and arguments passed to blacklisted Papyrus engine calls (148 built-in functions from `pexNoTransProc.txt`, e.g. `RegisterForUpdate`, `SendStoryEvent`, `PlayAnimation`). **AI Agents and users MUST NOT modify or translate locked entries.**
- ⚠️ **`warning` (`warn: true`):** Strings used in conditional branch comparisons (`==`, `!=`, `<`, `>`). Inspect with care to avoid breaking state-machine comparisons.
- 🟢 **`safe` (`auth: true`):** Player-facing text: `Debug.Notification`, `Debug.MessageBox`, `SetInfoText`, `VMAD` script string properties (MCM titles, option labels, descriptions, and format strings).

### 2. Autonomous Agent Rule:
When translating a mod in Mode A, always extract VMAD properties via `PexSafetyEngine.extract_vmad_strings(esp_path)` and include them in the batch translation step alongside regular plugin records.

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
