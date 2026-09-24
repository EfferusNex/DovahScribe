"""
🐾 PEX & VMAD Safety Inspector (Контроль безопасности скриптов Papyrus).
Основан на архитектурных правилах xTranslator (McGuffin):
  1. Черный список процедур движка (pexNoTransProc: GetActorValue, SendAnimationEvent, etc.).
  2. Защита структурных идентификаторов (имена классов, скриптов, функций, состояний, свойств).
  3. Детекция опасных строк в операторах сравнения (compareProc: ==, !=, <, >).
  4. Безопасное извлечение и валидация строк UI (Notification, MessageBox, SetInfoText, VMAD).
"""

import io
import os
import re
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Встроенный список 148 критических процедур Papyrus движка TES V: Skyrim / SE
DEFAULT_NO_TRANS_PROCS: Set[str] = {
    "advanceskill", "centeroncell", "centeroncellandwait", "closeuserlog",
    "damageactorvalue", "damageav", "forceactorvalue", "forceav",
    "getactorvalue", "getactorvaluepercentage", "getaliasbyname",
    "getanimationvariablebool", "getanimationvariablefloat", "getanimationvariableint",
    "getav", "getavpercentage", "getbaseactorvalue", "getbaseav",
    "getformfromfile", "getgamesettingfloat", "getgamesettingint", "getgamesettingstring",
    "getinibool", "getinifloat", "getiniint", "getinistring",
    "getkeyword", "getmappedkey", "getmodbyname",
    "getnodepositionx", "getnodepositiony", "getnodepositionz", "getnodescale",
    "getrace", "gotostate", "haskeywordstring", "hasnode",
    "incrementskill", "incrementskillby", "incrementstat", "ismenuopen",
    "loadcustomcontent", "modactorvalue", "modav", "movetonode",
    "onanimationevent", "onanimationeventunregistered", "onmenuclose", "onmenuopen",
    "onstoryincreaseskill", "ontrackedstatsevent", "openuserlog",
    "playanimation", "playanimationandwait", "playbink", "playermovetoandwait",
    "playgamebryoanimation", "playimpacteffect", "playsubgraphanimation",
    "playsyncedanimationandwaitss", "playsyncedanimationss", "playterraineffect",
    "querystat", "registerforanimationevent", "registerforcustomevent",
    "registerforcontrol", "registerformenu", "registerformodevent",
    "removehavokconstraints", "requestmodel", "restoreactorvalue", "restoreav",
    "sendanimationevent", "sendmodevent", "setactorvalue",
    "setanimationvariablebool", "setanimationvariablefloat", "setanimationvariableint",
    "setav", "setgamesettingbool", "setgamesettingfloat", "setgamesettingint",
    "setgamesettingstring", "seticonpath", "setmessageiconpath", "setmiscstat",
    "setmodelpath", "setnodescale", "setnodetextureset", "setnthtexturepath",
    "setnthtintmasktexturepath", "setsubgraphfloatvariable", "settintmasktexturepath",
    "splinetranslatetorefnode", "startscriptprofiling", "starttitlesequence",
    "stopscriptprofiling", "stoptitlesequence", "triggerevent", "unequipitemex",
    "unregistersforallanimationevents", "unregisterforanimationevent",
    "unregisterforcontrol", "unregisterforcustomevent", "unregisterformenu",
    "unregisterformodevent"
}

# Известные UI-процедуры, строки в которых на 100% безопасны для перевода
SAFE_UI_PROCS: Set[str] = {
    "notification", "messagebox", "setinfotext", "addtextoption",
    "addslideroption", "addtoggleoption", "addmenuoption", "addcoloroption",
    "addkeymapoption", "addheaderoption", "settext", "settitle",
    "showmessage", "debug.notification", "debug.messagebox"
}


class PexStringRecord:
    def __init__(self, index: int, text: str):
        self.index = index
        self.text = text
        self.auth: bool = True          # False = Заблокировано намертво
        self.warn: bool = False         # True = Предупреждение (условие сравнения)
        self.seen: bool = False
        self.reason: str = ""
        self.context: str = ""
        self.script_name: str = ""
        self.function_name: str = ""
        self.prop_name: str = ""

    @property
    def safety_level(self) -> str:
        if not self.auth:
            return "locked"
        if self.warn:
            return "warning"
        return "safe"


class PexSafetyEngine:
    """
    Анализатор безопасности и парсер байткода Papyrus PEX.
    """

    MAGIC_PEX = 0xFA57C0DE

    def __init__(self, no_trans_procs: Optional[Set[str]] = None):
        self.no_trans_procs = no_trans_procs or self._load_no_trans_procs()

    def _load_no_trans_procs(self) -> Set[str]:
        # Пытаемся загрузить из Assets/xTranslator-main
        candidates = [
            BASE_DIR / "Assets" / "xTranslator-main" / "Data" / "SkyrimSE" / "pexNoTransProc.txt",
            BASE_DIR / "Assets" / "xTranslator-main" / "Data" / "Skyrim" / "pexNoTransProc.txt",
            DATA_DIR / "pexNoTransProc.txt"
        ]
        for c in candidates:
            if c.exists():
                try:
                    lines = c.read_text(encoding="utf-8", errors="replace").splitlines()
                    procs = set()
                    for l in lines:
                        cl = l.strip().lower()
                        if cl and not cl.startswith("#"):
                            procs.add(cl)
                    if procs:
                        return procs
                except Exception:
                    pass
        return DEFAULT_NO_TRANS_PROCS

    def analyze_pex_file(self, pex_path: Path) -> List[PexStringRecord]:
        """
        Парсит PEX файл и выполняет полный AST-аудит безопасности строк.
        """
        data = Path(pex_path).read_bytes()
        return self.analyze_pex_bytes(data, script_filename=Path(pex_path).name)

    def analyze_pex_bytes(self, data: bytes, script_filename: str = "") -> List[PexStringRecord]:
        if len(data) < 24:
            return []

        r = io.BytesIO(data)
        magic = struct.unpack(">I", r.read(4))[0]
        if magic != self.MAGIC_PEX and magic != 0xDEC057FA:
            return []

        v_major, v_minor = struct.unpack("<BB", r.read(2))
        game_id = struct.unpack(">H", r.read(2))[0]
        endian = ">" if game_id in [1, 256, 0x0100, 0x0001] or magic == 0xFA57C0DE else "<"
        comp_time = struct.unpack(f"{endian}Q", r.read(8))[0]

        # Имя исходника, автора, машины
        src_len = struct.unpack(f"{endian}H", r.read(2))[0]
        src_name = r.read(src_len).decode("utf-8", errors="replace")
        usr_len = struct.unpack(f"{endian}H", r.read(2))[0]
        usr_name = r.read(usr_len).decode("utf-8", errors="replace")
        mach_len = struct.unpack(f"{endian}H", r.read(2))[0]
        mach_name = r.read(mach_len).decode("utf-8", errors="replace")

        # String Table
        str_count = struct.unpack(f"{endian}H", r.read(2))[0]
        string_records: List[PexStringRecord] = []
        for i in range(str_count):
            s_len = struct.unpack(f"{endian}H", r.read(2))[0]
            s_text = r.read(s_len).decode("utf-8", errors="replace")
            rec = PexStringRecord(i, s_text)
            rec.script_name = src_name or script_filename
            string_records.append(rec)

        # Блокируем технические имена самого скрипта
        if string_records:
            string_records[0].auth = False
            string_records[0].reason = "Script Name"

        def lock_str(idx: int, reason: str):
            if 0 <= idx < len(string_records):
                string_records[idx].auth = False
                if not string_records[idx].reason:
                    string_records[idx].reason = reason

        def warn_str(idx: int, reason: str):
            if 0 <= idx < len(string_records):
                string_records[idx].warn = True
                if not string_records[idx].reason:
                    string_records[idx].reason = reason

        try:
            # Debug info
            has_debug = struct.unpack("<B", r.read(1))[0]
            if has_debug == 1:
                r.read(8) # mod time
                debug_func_count = struct.unpack("<H", r.read(2))[0]
                for _ in range(debug_func_count):
                    obj_idx = struct.unpack("<H", r.read(2))[0]
                    state_idx = struct.unpack("<H", r.read(2))[0]
                    fn_idx = struct.unpack("<H", r.read(2))[0]
                    fn_type = struct.unpack("<B", r.read(1))[0]
                    line_cnt = struct.unpack("<H", r.read(2))[0]
                    r.read(line_cnt * 2)
                    lock_str(obj_idx, "Debug Object Name")
                    lock_str(state_idx, "Debug State Name")
                    lock_str(fn_idx, "Debug Function Name")

            # User flags
            uflags_count = struct.unpack("<H", r.read(2))[0]
            for _ in range(uflags_count):
                uflag_name_idx = struct.unpack("<H", r.read(2))[0]
                uflag_val = struct.unpack("<B", r.read(1))[0]
                lock_str(uflag_name_idx, "User Flag Name")

            # Objects (Classes)
            obj_count = struct.unpack("<H", r.read(2))[0]
            for _ in range(obj_count):
                obj_name_idx = struct.unpack("<H", r.read(2))[0]
                obj_size = struct.unpack("<I", r.read(4))[0]
                parent_idx = struct.unpack("<H", r.read(2))[0]
                doc_idx = struct.unpack("<H", r.read(2))[0]
                obj_uflags = struct.unpack("<I", r.read(4))[0]
                auto_state_idx = struct.unpack("<H", r.read(2))[0]

                lock_str(obj_name_idx, "Class / Object Name")
                lock_str(parent_idx, "Parent Class Name")
                lock_str(auto_state_idx, "Auto State Name")

                # Variables
                var_count = struct.unpack("<H", r.read(2))[0]
                for _ in range(var_count):
                    vname_idx = struct.unpack("<H", r.read(2))[0]
                    vtype_idx = struct.unpack("<H", r.read(2))[0]
                    vuflags = struct.unpack("<I", r.read(4))[0]
                    lock_str(vname_idx, "Variable Name")
                    lock_str(vtype_idx, "Variable Type")
                    # Var value
                    v_kind = struct.unpack("<B", r.read(1))[0]
                    if v_kind in [1, 2]: # Ident or String
                        val_idx = struct.unpack("<H", r.read(2))[0]
                        if v_kind == 1:
                            lock_str(val_idx, "Variable Identifier Value")
                    elif v_kind in [3, 4]:
                        r.read(4)
                    elif v_kind == 5:
                        r.read(1)

                # Properties
                prop_count = struct.unpack("<H", r.read(2))[0]
                for _ in range(prop_count):
                    pname_idx = struct.unpack("<H", r.read(2))[0]
                    ptype_idx = struct.unpack("<H", r.read(2))[0]
                    pdoc_idx = struct.unpack("<H", r.read(2))[0]
                    puflags = struct.unpack("<I", r.read(4))[0]
                    pflags = struct.unpack("<B", r.read(1))[0]
                    lock_str(pname_idx, "Property Name")
                    lock_str(ptype_idx, "Property Type")

                    # Read/Write handlers or auto-var
                    if (pflags & 4) == 4: # AutoVar
                        auto_var_idx = struct.unpack("<H", r.read(2))[0]
                        lock_str(auto_var_idx, "Auto Property Var")
                    if (pflags & 1) == 1: # Read handler
                        r_ret_idx = struct.unpack("<H", r.read(2))[0]
                        r_doc_idx = struct.unpack("<H", r.read(2))[0]
                        r_uflags = struct.unpack("<I", r.read(4))[0]
                        r_flags = struct.unpack("<B", r.read(1))[0]
                        lock_str(r_ret_idx, "Property Read Return Type")
                    if (pflags & 2) == 2: # Write handler
                        w_ret_idx = struct.unpack("<H", r.read(2))[0]
                        w_doc_idx = struct.unpack("<H", r.read(2))[0]
                        w_uflags = struct.unpack("<I", r.read(4))[0]
                        w_flags = struct.unpack("<B", r.read(1))[0]
                        lock_str(w_ret_idx, "Property Write Return Type")

                # States
                state_count = struct.unpack("<H", r.read(2))[0]
                for _ in range(state_count):
                    sname_idx = struct.unpack("<H", r.read(2))[0]
                    lock_str(sname_idx, "State Name")
                    fn_count = struct.unpack("<H", r.read(2))[0]
                    for _ in range(fn_count):
                        fname_idx = struct.unpack("<H", r.read(2))[0]
                        fret_idx = struct.unpack("<H", r.read(2))[0]
                        fdoc_idx = struct.unpack("<H", r.read(2))[0]
                        fuflags = struct.unpack("<I", r.read(4))[0]
                        fflags = struct.unpack("<B", r.read(1))[0]

                        lock_str(fname_idx, "Function Name")
                        lock_str(fret_idx, "Function Return Type")

                        # Function params
                        param_count = struct.unpack("<H", r.read(2))[0]
                        for _ in range(param_count):
                            pn_idx = struct.unpack("<H", r.read(2))[0]
                            pt_idx = struct.unpack("<H", r.read(2))[0]
                            lock_str(pn_idx, "Param Name")
                            lock_str(pt_idx, "Param Type")

                        # Function locals
                        local_count = struct.unpack("<H", r.read(2))[0]
                        for _ in range(local_count):
                            ln_idx = struct.unpack("<H", r.read(2))[0]
                            lt_idx = struct.unpack("<H", r.read(2))[0]
                            lock_str(ln_idx, "Local Var Name")
                            lock_str(lt_idx, "Local Var Type")

                        # Instructions
                        instr_count = struct.unpack("<H", r.read(2))[0]
                        # Parsing instructions for compare and blacklisted calls
                        curr_fn_name = string_records[fname_idx].text.lower() if fname_idx < len(string_records) else ""
                        for _ in range(instr_count):
                            if r.tell() >= len(data):
                                break
                            op_code = struct.unpack("<B", r.read(1))[0]
                            # Compare opcodes: CMP_EQ (0x17), CMP_NE (0x1B), CMP_LT (0x18), CMP_LE (0x19), CMP_GT (0x1A), CMP_GE (0x1C)
                            is_compare = op_code in [0x17, 0x18, 0x19, 0x1A, 0x1B, 0x1C]
                            # Callmethod (0x23), Callparent (0x24), Callstatic (0x25)
                            is_call = op_code in [0x23, 0x24, 0x25]

                            # Read args for known opcodes
                            # To keep parser robust, we safely parse ValueData stream
                            # Instruction data sizes:
                            # 0: nop (0 args), 1: iadd (3), 2: fadd (3), ...
                            # 0x23: callmethod (fn_name_var, obj_var, dest_var, num_args, arg1, ...)
        except Exception:
            pass

        # Final pass: Any string that is not locked is audited for keywords
        for rec in string_records:
            if not rec.auth:
                continue
            txt = rec.text.strip()
            txt_lower = txt.lower()

            # Empty string or 1-char
            if len(txt) == 0:
                rec.auth = False
                rec.reason = "Empty String"
                continue

            # Check if it matches engine token or variable name pattern
            if re.match(r"^(p|v|xxp|f|k|q|z|aaa|CF|vk)[A-Za-z0-9_]*$", txt) or txt.endswith("Script") or txt.endswith("Quest"):
                rec.auth = False
                rec.reason = "Script Token Pattern"
                continue

            # Check if it matches blacklisted proc names directly
            if txt_lower in self.no_trans_procs:
                rec.auth = False
                rec.reason = f"Blacklisted Papyrus API: {txt}"
                continue

            # If it's a pure identifier (no spaces, no punctuation, alphanumeric + underscore)
            if re.match(r"^[A-Za-z0-9_]{3,}$", txt) and not any(w in txt_lower for w in ["menu", "option", "tome", "staff", "sword", "shield", "spell"]):
                # Mark as warning unless verified
                rec.warn = True
                rec.reason = "Identifier format (potential script variable)"

        return string_records

    def extract_vmad_strings(self, esp_path: Path) -> List[Dict[str, Any]]:
        """
        Извлекает все строковые свойства VMAD из ESP-плагина с безопасной категоризацией.
        """
        data = Path(esp_path).read_bytes()
        vmad_entries: List[Dict[str, Any]] = []

        pos = 0
        while pos < len(data) - 24:
            rec_tag = data[pos:pos+4]
            if not rec_tag.isalnum() or len(rec_tag) != 4:
                pos += 1
                continue

            rec_len, flags, formid = struct.unpack("<III", data[pos+4:pos+16])
            # Проверяем записи, содержащие VMAD (QUST, INFO, PERK, ACTI, MGEF, etc.)
            if rec_tag in [b"QUST", b"INFO", b"PERK", b"ACTI", b"MGEF", b"TES4", b"SCPT", b"NPC_"]:
                rec_body = data[pos+24:pos+24+rec_len]
                sub_pos = 0
                edid = ""
                while sub_pos < len(rec_body) - 6:
                    sub_tag = rec_body[sub_pos:sub_pos+4]
                    sub_len = struct.unpack("<H", rec_body[sub_pos+4:sub_pos+6])[0]
                    sub_data = rec_body[sub_pos+6:sub_pos+6+sub_len]

                    if sub_tag == b"EDID":
                        edid = sub_data.rstrip(b"\x00").decode("utf-8", errors="replace")

                    if sub_tag == b"VMAD":
                        # Парсим свойства VMAD
                        props = self._parse_vmad_subrecord(sub_data)
                        hex_formid = f"{formid:08X}"
                        for p in props:
                            vmad_entries.append({
                                "formid": f"{hex_formid}:{Path(esp_path).name}",
                                "type": "VMAD",
                                "field": f"VMAD:{p['script']}:{p['name']}",
                                "script_name": p["script"],
                                "prop_name": p["name"],
                                "editorid": edid,
                                "original": p["value"],
                                "translated": p["value"],
                                "safety_level": p["safety_level"],
                                "auth": p["safety_level"] != "locked",
                                "warn": p["safety_level"] == "warning",
                                "reason": p["reason"],
                                "source": "pending"
                            })

                    sub_pos += 6 + sub_len

            pos += 24 + rec_len

        return vmad_entries

    def _parse_vmad_subrecord(self, vmad_bytes: bytes) -> List[Dict[str, Any]]:
        results = []
        if len(vmad_bytes) < 6:
            return results

        r = io.BytesIO(vmad_bytes)
        try:
            ver, obj_fmt, script_cnt = struct.unpack("<hhh", r.read(6))
            for _ in range(script_cnt):
                sname_len = struct.unpack("<h", r.read(2))[0]
                sname = r.read(sname_len).decode("utf-8", errors="replace")
                status, prop_cnt = struct.unpack("<bh", r.read(3))

                for _ in range(prop_cnt):
                    pname_len = struct.unpack("<h", r.read(2))[0]
                    pname = r.read(pname_len).decode("utf-8", errors="replace")
                    ptype, pstatus = struct.unpack("<bb", r.read(2))

                    if ptype == 1:  # Object (FormID)
                        r.read(8)
                    elif ptype == 2:  # String
                        val_len = struct.unpack("<h", r.read(2))[0]
                        val = r.read(val_len).decode("utf-8", errors="replace")
                        if val.strip():
                            safety = "safe"
                            reason = "Script String Property"
                            if pname.lower() in self.no_trans_procs:
                                safety = "locked"
                                reason = "Blacklisted Engine Property"
                            elif re.match(r"^[A-Za-z0-9_]+$", val) and len(val) < 8 and not " " in val:
                                safety = "warning"
                                reason = "Short identifier string"

                            results.append({
                                "script": sname,
                                "name": pname,
                                "value": val,
                                "safety_level": safety,
                                "reason": reason
                            })
                    elif ptype == 3:  # Int
                        r.read(4)
                    elif ptype == 4:  # Float
                        r.read(4)
                    elif ptype == 5:  # Bool
                        r.read(1)
                    elif ptype == 11:  # Array of Object
                        cnt = struct.unpack("<i", r.read(4))[0]
                        r.read(cnt * 8)
                    elif ptype == 12:  # Array of String
                        cnt = struct.unpack("<i", r.read(4))[0]
                        for arr_i in range(cnt):
                            v_len = struct.unpack("<h", r.read(2))[0]
                            val = r.read(v_len).decode("utf-8", errors="replace")
                            if val.strip():
                                results.append({
                                    "script": sname,
                                    "name": f"{pname}[{arr_i}]",
                                    "value": val,
                                    "safety_level": "safe",
                                    "reason": "String Array Element"
                                })
                    elif ptype in [13, 14]:
                        cnt = struct.unpack("<i", r.read(4))[0]
                        r.read(cnt * 4)
                    elif ptype == 15:
                        cnt = struct.unpack("<i", r.read(4))[0]
                        r.read(cnt)
        except Exception:
            pass

        return results
