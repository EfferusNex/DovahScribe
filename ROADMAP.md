# 🗺️ DovahScribe — Strategic Roadmap & Backlog

This document tracks active engineering milestones, completed architectural features, and future backlog items for the **DovahScribe** Skyrim AI Localization Suite.

---

## 🚀 Completed Milestones (v0.7.0)

- [x] **Direct Binary ESP String Injector & Subrecord Parser (`src/esp_injector.py`)**:
  - Standalone binary replacement of localized subrecords (`FULL`, `DESC`, `DNAM`, `RNAM`, `NAM1`, `SHRT`, `NNAM`, `CNAM`, `ITXT`, `CELL`).
  - Native zlib decompression and recompression with dynamic record size updating and GRUP container recalculation.
- [x] **Autonomous Subrecord Synthesis**:
  - Automatically synthesizes and injects missing `FULL`, `SHRT`, `DESC`, and `DNAM` string subrecords into override records (NPCs, containers, items) directly behind `EDID`.
- [x] **Papyrus PEX & VMAD Script Safety Engine (`src/pex_safety.py`)**:
  - Bytecode-level classification (`locked`, `warning`, `safe`) using 148 built-in Bethesda engine functions.
  - Safe extraction and translation of VMAD script string properties and player-facing notifications.
  - Strict script cleanliness policy (unmodified scripts are never copied to `[RU]`).
- [x] **BSA Archive Extraction & Asset Management (`src/bsa_manager.py`)**:
  - Native `BSAManager` for inspecting and extracting Bethesda `.bsa` archives.
- [x] **Comprehensive 1C Canonical Database & Bethesda String Sets**:
  - Integrated official 72,612-entry Russian Skyrim strings database (`vanilla_dictionary.json`).
  - Extracted and indexed 8 official Bethesda string sets (`.strings`, `.dlstrings`, `.ilstrings`).
- [x] **Quality Gate & Leak Prevention Hardening**:
  - Lore rune font preservation pattern (`$FalmerFont`, `$DwemerFont`, `$DaedricFont`, `$MageScriptFont`, `$DragonFont`).
  - Advanced Russian adjective and noun stemmer for case-insensitive glossary audits.
- [x] **Drop-In MO2 VFS Deployment**:
  - Clean deployment to `mods/<ModName> [RU]/` with automated `modlist.txt` priority elevation above original mod.
  - Automatic `.seq` sequence copying and `meta.ini` generation.
- [x] **Standalone Generative HTML Dashboard (`web/cat_dashboard.html`)**:
  - Per-mod interactive CAT dashboard with embedded JSON data, search, filters, and keyboard shortcuts.

---

## 🔮 Mid-Term Milestones (v0.8.x)

- [ ] **Automated Dialogue Tree Visualizer**:
  - Interactive web branch visualization showing parent quest dialogue flow (`QUST` -> `DIAL` -> `INFO` -> Responses).
- [ ] **Batch Multi-Mod Orchestrator**:
  - Automated translation queue processing for multi-plugin mod suites and patches.
- [ ] **BSA Asset Audio Matcher**:
  - Automated check for localized voice lines / `.fuz` / `.xwm` assets matching dialogue response lengths.

---

## ⏳ Long-Term / Backlog Milestones (Дальний этап)

### 📦 1. Standalone Native ESP/ESM/ESL Extractor (`src/esp_extractor.py`)
> **Rationale & Scope:** Transition from external HouseCARL MCP extraction to an internal, zero-dependency binary record extractor built directly into DovahScribe in pure Python.
>
> - **Core Objective:** Complete standalone autonomy (run `python translate.py --plugin Mod.esp` without requiring .NET Runtime or HouseCARL MCP server).
> - **Key Capabilities:**
>   - Direct physical file parsing (`open('Mod.esp', 'rb')`), guaranteeing 100% isolation from MO2 load-order overrides.
>   - Native extraction of all 38+ supported record types (`NPC_`, `WEAP`, `ARMO`, `BOOK`, `CONT`, `DIAL`, `INFO`, `QUST`, `MESG`, etc.).
>   - Subrecord hierarchy tracking for dialogue parent topics (`*parent.EditorID`, `*parent.Name`).
>   - Multi-encoding string table support (`.STRINGS`, `.ILSTRINGS`, `.DLSTRINGS` for localized plugins with flag `0x80`).
> - **Deployment Strategy:** Hybrid fallback mode — standalone binary extractor by default, HouseCARL MCP retained as optional world-graph analyzer.
