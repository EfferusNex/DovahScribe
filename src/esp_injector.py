"""
🐾 Skyrim Translator AI — Direct ESP String Injector
Выполняет прямую точечную замену локализованных строк в бинарных плагинах (.esp/.esm/.esl).
Сохраняет 100% исходной бинарной структуры плагина, порядок мастеров, FormID и флаги.
"""

import json
import struct
import zlib
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any


class ESPInjector:
    """
    Прямой инжектор переведенных строк в файлы плагинов TES V: Skyrim SE.
    Работает со структурой Bethesda TES4/GRUP/Record/Subrecord.
    """

    # Соответствие полей из review.json типам бинарных субрекордов в зависимости от типа рекорда
    TYPE_FIELD_TO_SUBRECORD = {
        (b"MGEF", "Description"): b"DNAM",
        (b"MGEF", "Name"): b"FULL",
        (b"PERK", "Description"): b"DESC",
        (b"PERK", "Name"): b"FULL",
        (b"BOOK", "BookText"): b"DESC",
        (b"BOOK", "Description"): b"DESC",
        (b"BOOK", "Name"): b"FULL",
        (b"MESG", "Description"): b"DESC",
        (b"MESG", "Name"): b"FULL",
        (b"LSCR", "Description"): b"DESC",
        (b"QUST", "Name"): b"FULL",
        (b"QUST", "Objectives"): b"NNAM",
        (b"QUST", "Stages"): b"CNAM",
        (b"INFO", "Prompt"): b"RNAM",
        (b"DIAL", "Name"): b"FULL",
        (b"NPC_", "ShortName"): b"SHRT",
        (b"NPC_", "Name"): b"FULL",
        (b"REFR", "MapMarker.Name"): b"FULL",
        (b"REFR", "MapMarker.Name.String"): b"FULL",
        (b"REFR", "Name"): b"FULL",
    }

    # Базовое соответствие полей субрекордам по умолчанию
    DEFAULT_FIELD_TO_SUBRECORD = {
        "Name": b"FULL",
        "MapMarker.Name": b"FULL",
        "MapMarker.Name.String": b"FULL",
        "Description": b"DESC",
        "ShortName": b"SHRT",
        "BookText": b"DESC",
        "Prompt": b"RNAM",
        "Objectives": b"NNAM",
        "Stages": b"CNAM",
    }

    @staticmethod
    def parse_formid_int(formid_str: str) -> int:
        """Извлекает 24-битный FormID из строки вида '036A44:Skyrim.esm' или '00036A44'."""
        hex_part = formid_str.split(":")[0].strip()
        return int(hex_part, 16) & 0x00FFFFFF

    @classmethod
    def extract_all_strings(cls, esp_path: Path) -> List[Dict[str, Any]]:
        """
        Рекурсивно сканирует бинарную структуру плагина (.esp/.esm/.esl) и извлекает
        100% текстовых полей со всех уровней вложенности GRUP, включая сжатые ячейки и диалоги.
        """
        from src.io_utils import is_valid_string

        esp_path = Path(esp_path)
        if not esp_path.exists():
            raise FileNotFoundError(f"Файл плагина не найден: {esp_path}")

        raw = esp_path.read_bytes()
        if len(raw) < 24:
            return []

        header_sig, header_size, header_flags, header_formid = struct.unpack("<4sIII", raw[:16])
        if header_sig != b"TES4":
            return []

        header_body = raw[24 : 24 + header_size]
        masters = []
        h_pos = 0
        while h_pos < len(header_body):
            if h_pos + 6 > len(header_body):
                break
            s_sig = header_body[h_pos : h_pos + 4]
            s_size = struct.unpack("<H", header_body[h_pos + 4 : h_pos + 6])[0]
            s_data = header_body[h_pos + 6 : h_pos + 6 + s_size]
            if s_sig == b"MAST":
                m_name = s_data.decode("latin1", errors="ignore").rstrip("\x00")
                masters.append(m_name)
            h_pos += 6 + s_size

        if not masters:
            masters = ["Skyrim.esm"]

        plugin_name = esp_path.name
        extracted_items = []
        item_id = 1

        def resolve_formid_str(formid_int: int) -> str:
            master_idx = (formid_int >> 24) & 0xFF
            local_id = formid_int & 0x00FFFFFF
            if master_idx < len(masters):
                m_file = masters[master_idx]
            else:
                m_file = plugin_name
            return f"{local_id:06X}:{m_file}"

        def decode_text(raw_bytes: bytes) -> str:
            try:
                return raw_bytes.decode("utf-8").rstrip("\x00")
            except UnicodeDecodeError:
                try:
                    return raw_bytes.decode("cp1251").rstrip("\x00")
                except UnicodeDecodeError:
                    return raw_bytes.decode("latin1", errors="ignore").rstrip("\x00")

        def parse_subs(data: bytes) -> List[Tuple[bytes, bytes]]:
            subs = []
            pos = 0
            while pos < len(data):
                if pos + 6 > len(data):
                    break
                s_sig = data[pos : pos + 4]
                s_size = struct.unpack("<H", data[pos + 4 : pos + 6])[0]
                s_val = data[pos + 6 : pos + 6 + s_size]
                subs.append((s_sig, s_val))
                pos += 6 + s_size
            return subs

        def process_grup_extract(data: bytes):
            nonlocal item_id
            pos = 0
            while pos < len(data):
                if pos + 24 > len(data):
                    break
                sig = data[pos : pos + 4]
                if sig == b"GRUP":
                    grup_size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
                    process_grup_extract(data[pos + 24 : pos + grup_size])
                    pos += grup_size
                else:
                    rec_size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
                    rec_flags, rec_formid = struct.unpack("<II", data[pos + 8 : pos + 16])
                    rec_body = data[pos + 24 : pos + 24 + rec_size]
                    pos += 24 + rec_size

                    is_comp = (rec_flags & 0x00040000) != 0
                    if is_comp:
                        try:
                            body = zlib.decompress(rec_body[4:])
                        except Exception:
                            continue
                    else:
                        body = rec_body

                    subs = parse_subs(body)
                    rec_type_str = sig.decode("latin1", errors="ignore").rstrip("\x00")
                    formid_str = resolve_formid_str(rec_formid)

                    edid = ""
                    for s_sig, s_val in subs:
                        if s_sig == b"EDID":
                            edid = decode_text(s_val)
                            break

                    resp_idx = 0
                    btn_idx = 0
                    for s_sig, s_val in subs:
                        field_name = None
                        if s_sig == b"FULL":
                            field_name = "Name"
                        elif s_sig == b"DESC":
                            field_name = "BookText" if rec_type_str == "BOOK" else "Description"
                        elif s_sig == b"DNAM" and rec_type_str in ["MGEF", "PERK"]:
                            field_name = "Description"
                        elif s_sig == b"SHRT":
                            field_name = "ShortName"
                        elif s_sig == b"RNAM" and rec_type_str == "INFO":
                            field_name = "Prompt"
                        elif s_sig == b"NNAM" and rec_type_str == "QUST":
                            field_name = "Objectives"
                        elif s_sig == b"CNAM" and rec_type_str == "QUST":
                            field_name = "Stages"
                        elif s_sig == b"NAM1" and rec_type_str == "INFO":
                            field_name = f"Responses[{resp_idx}].Text"
                            resp_idx += 1
                        elif s_sig == b"ITXT" and rec_type_str == "MESG":
                            field_name = f"Buttons[{btn_idx}]"
                            btn_idx += 1

                        if field_name:
                            text = decode_text(s_val)
                            if is_valid_string(text, allow_russian=True):
                                extracted_items.append({
                                    "id": item_id,
                                    "formid": formid_str,
                                    "type": rec_type_str,
                                    "path": field_name,
                                    "field": field_name,
                                    "text": text,
                                    "editorid": edid,
                                    "speaker": "",
                                    "topic": ""
                                })
                                item_id += 1

        process_grup_extract(raw[24 + header_size:])
        return extracted_items

    @classmethod
    def inject_translations(
        cls,
        source_esp: Path,
        target_esp: Path,
        review_file: Path,
    ) -> Dict[str, Any]:
        """
        Читает source_esp, накладывает переводы из review_file и сохраняет в target_esp.
        """
        source_esp = Path(source_esp)
        target_esp = Path(target_esp)
        review_file = Path(review_file)

        if not source_esp.exists():
            raise FileNotFoundError(f"Исходный плагин не найден: {source_esp}")
        if not review_file.exists():
            raise FileNotFoundError(f"Файл ревью не найден: {review_file}")

        review_data = json.load(open(review_file, encoding="utf-8"))
        entries = review_data.get("entries", [])
        
        # Индексируем переводы:
        # { (formid_24bit, field_name): translated_text }
        # { (formid_24bit, 'Responses', index): translated_text }
        # { (formid_24bit, 'Buttons', index): translated_text }
        translations: Dict[Tuple[int, str], str] = {}
        indexed_translations: Dict[Tuple[int, str, int], str] = {}
        vmad_translations: Dict[Tuple[int, str, str], str] = {}

        total_review_items = 0
        for entry in entries:
            # Пропускаем внешние MCM записи (они экспортируются в Interface/Translations/*.txt)
            if entry.get("type") == "MCM" or str(entry.get("formid", "")).startswith("MCM:"):
                continue

            trans = entry.get("translated", "")
            if trans is None:
                continue
            trans = str(trans).strip()
            if not trans:
                continue

            formid_int = cls.parse_formid_int(entry["formid"])
            field = entry.get("field", "Name")
            total_review_items += 1

            if entry.get("type") == "VMAD" or field.startswith("VMAD:"):
                script_name = entry.get("script_name") or (field.split(":")[1] if ":" in field else "")
                prop_name = entry.get("prop_name") or (field.split(":")[2] if field.count(":") >= 2 else field)
                vmad_translations[(formid_int, script_name.lower(), prop_name.lower())] = trans
            elif field.startswith("Responses[") and ".Text" in field:
                try:
                    idx = int(field.split("[")[1].split("]")[0])
                    indexed_translations[(formid_int, "Responses", idx)] = trans
                except Exception:
                    translations[(formid_int, field)] = trans
            elif field.startswith("Buttons["):
                try:
                    idx = int(field.split("[")[1].split("]")[0])
                    indexed_translations[(formid_int, "Buttons", idx)] = trans
                except Exception:
                    translations[(formid_int, field)] = trans
            else:
                translations[(formid_int, field)] = trans

        # Читаем исходный ESP
        raw_data = source_esp.read_bytes()
        if raw_data[:4] != b"TES4":
            raise ValueError(f"Файл {source_esp.name} не является корректным TES4 плагином.")

        applied_count = 0

        # Рекурсивный парсер и сборщик иерархии GRUP/Record
        def process_container(data: bytes, pos: int, end: int) -> bytes:
            nonlocal applied_count
            output_parts = []

            while pos < end:
                tag = data[pos : pos + 4]
                if len(tag) < 4:
                    break

                if tag == b"GRUP":
                    grup_header = data[pos : pos + 24]
                    grup_size = struct.unpack_from("<I", grup_header, 4)[0]
                    grup_body = data[pos + 24 : pos + grup_size]
                    
                    # Рекурсивно обрабатываем тело группы
                    new_grup_body = process_container(grup_body, 0, len(grup_body))
                    new_grup_size = 24 + len(new_grup_body)
                    
                    # Обновляем размер группы в заголовке
                    new_grup_header = grup_header[:4] + struct.pack("<I", new_grup_size) + grup_header[8:24]
                    output_parts.append(new_grup_header + new_grup_body)
                    pos += grup_size
                else:
                    # Обычный рекорд (24 байта заголовок)
                    rec_header = data[pos : pos + 24]
                    rec_type = tag
                    data_size = struct.unpack_from("<I", rec_header, 4)[0]
                    flags = struct.unpack_from("<I", rec_header, 8)[0]
                    formid = struct.unpack_from("<I", rec_header, 12)[0]
                    formid_24bit = formid & 0x00FFFFFF

                    rec_body = data[pos + 24 : pos + 24 + data_size]
                    pos += 24 + data_size

                    # Проверяем, сжат ли рекорд (флаг 0x00040000)
                    is_compressed = bool(flags & 0x00040000)
                    if is_compressed:
                        uncompressed_size = struct.unpack_from("<I", rec_body, 0)[0]
                        decompressed_body = zlib.decompress(rec_body[4:])
                        processed_body, modified = process_record_subrecords(
                            decompressed_body, formid_24bit, rec_type
                        )
                        if modified:
                            new_compressed = zlib.compress(processed_body)
                            new_rec_body = struct.pack("<I", len(processed_body)) + new_compressed
                        else:
                            new_rec_body = rec_body
                    else:
                        new_rec_body, modified = process_record_subrecords(
                            rec_body, formid_24bit, rec_type
                        )

                    # Обновляем заголовок рекорда
                    new_data_size = len(new_rec_body)
                    new_rec_header = rec_header[:4] + struct.pack("<I", new_data_size) + rec_header[8:24]
                    output_parts.append(new_rec_header + new_rec_body)

            return b"".join(output_parts)

        def process_record_subrecords(
            body: bytes, formid_24bit: int, rec_type: bytes
        ) -> Tuple[bytes, bool]:
            nonlocal applied_count
            modified = False
            sub_pos = 0
            new_sub_parts = []
            matched_fields = set()
            
            # Счетчики для индексированных полей в рамках одного рекорда
            nam1_index = 0
            itxt_index = 0

            while sub_pos < len(body):
                stype = body[sub_pos : sub_pos + 4]
                if len(stype) < 4:
                    new_sub_parts.append(body[sub_pos:])
                    break

                ssize = struct.unpack_from("<H", body, sub_pos + 4)[0]
                sdata = body[sub_pos + 6 : sub_pos + 6 + ssize]
                sub_pos += 6 + ssize

                replacement_text: Optional[str] = None
                matched_name: Optional[str] = None

                # 1. Поиск замены по индексированным типам
                if stype == b"VMAD" and vmad_translations:
                    new_vmad_bytes, vmad_applied = cls.patch_vmad_subrecord(sdata, formid_24bit, vmad_translations)
                    if vmad_applied > 0:
                        new_sub_parts.append(b"VMAD" + struct.pack("<H", len(new_vmad_bytes)) + new_vmad_bytes)
                        applied_count += vmad_applied
                        modified = True
                        continue
                    else:
                        new_sub_parts.append(stype + struct.pack("<H", ssize) + sdata)
                        continue
                elif stype == b"NAM1":
                    if (formid_24bit, "Responses", nam1_index) in indexed_translations:
                        replacement_text = indexed_translations[(formid_24bit, "Responses", nam1_index)]
                    nam1_index += 1
                elif stype == b"ITXT":
                    if (formid_24bit, "Buttons", itxt_index) in indexed_translations:
                        replacement_text = indexed_translations[(formid_24bit, "Buttons", itxt_index)]
                    itxt_index += 1
                else:
                    # 2. Поиск по специфическому маппингу (тип_рекорда, имя_поля)
                    for (m_rectype, field_name), mapped_stype in cls.TYPE_FIELD_TO_SUBRECORD.items():
                        if rec_type == m_rectype and stype == mapped_stype:
                            if (formid_24bit, field_name) in translations:
                                replacement_text = translations[(formid_24bit, field_name)]
                                matched_name = field_name
                                break

                    # 3. Поиск по базовому маппингу по умолчанию
                    if replacement_text is None:
                        for field_name, mapped_stype in cls.DEFAULT_FIELD_TO_SUBRECORD.items():
                            if stype == mapped_stype:
                                if (formid_24bit, field_name) in translations:
                                    replacement_text = translations[(formid_24bit, field_name)]
                                    matched_name = field_name
                                    break

                if replacement_text is not None:
                    # Строки в Skyrim SE заканчиваются нулевым байтом
                    new_sdata = replacement_text.encode("utf-8") + b"\x00"
                    new_ssize = len(new_sdata)
                    new_sub_parts.append(stype + struct.pack("<H", new_ssize) + new_sdata)
                    applied_count += 1
                    modified = True
                    if matched_name:
                        matched_fields.add(matched_name)
                else:
                    new_sub_parts.append(stype + struct.pack("<H", ssize) + sdata)

            # 4. Вставка отсутствующих в оригинале субрекордов (FULL, SHRT, DESC и т.д.)
            missing_subrecords = []
            for (f_id, field_name), trans_text in translations.items():
                if f_id == formid_24bit and field_name not in matched_fields:
                    target_sub_sig = None
                    if (rec_type, field_name) in cls.TYPE_FIELD_TO_SUBRECORD:
                        target_sub_sig = cls.TYPE_FIELD_TO_SUBRECORD[(rec_type, field_name)]
                    elif field_name in cls.DEFAULT_FIELD_TO_SUBRECORD:
                        target_sub_sig = cls.DEFAULT_FIELD_TO_SUBRECORD[field_name]

                    if target_sub_sig:
                        new_sdata = trans_text.encode("utf-8") + b"\x00"
                        missing_sub = target_sub_sig + struct.pack("<H", len(new_sdata)) + new_sdata
                        missing_subrecords.append(missing_sub)
                        applied_count += 1
                        modified = True

            if missing_subrecords:
                insert_idx = 0
                if len(new_sub_parts) > 0 and new_sub_parts[0].startswith(b"EDID"):
                    insert_idx = 1
                for sub in reversed(missing_subrecords):
                    new_sub_parts.insert(insert_idx, sub)

            return b"".join(new_sub_parts), modified

        # Запускаем прямую трансформацию
        new_plugin_data = process_container(raw_data, 0, len(raw_data))

        # Сохраняем в целевой файл
        target_esp.parent.mkdir(parents=True, exist_ok=True)
        target_esp.write_bytes(new_plugin_data)

        return {
            "success": True,
            "source": str(source_esp),
            "target": str(target_esp),
            "total_review_items": total_review_items,
            "applied_count": applied_count,
            "original_size": len(raw_data),
            "new_size": len(new_plugin_data),
        }

    @classmethod
    def patch_vmad_subrecord(
        cls,
        vmad_bytes: bytes,
        formid_24bit: int,
        vmad_translations: Dict[Tuple[int, str, str], str]
    ) -> Tuple[bytes, int]:
        """
        Точечно заменяет значения строковых свойств в бинарном субрекорде VMAD.
        """
        if len(vmad_bytes) < 6:
            return vmad_bytes, 0

        import io
        r = io.BytesIO(vmad_bytes)
        out = io.BytesIO()

        ver, obj_fmt, script_cnt = struct.unpack("<hhh", r.read(6))
        out.write(struct.pack("<hhh", ver, obj_fmt, script_cnt))

        applied = 0
        for _ in range(script_cnt):
            sname_len = struct.unpack("<h", r.read(2))[0]
            sname_bytes = r.read(sname_len)
            sname = sname_bytes.decode("utf-8", errors="replace")
            out.write(struct.pack("<h", sname_len) + sname_bytes)

            status, prop_cnt = struct.unpack("<bh", r.read(3))
            out.write(struct.pack("<bh", status, prop_cnt))

            for _ in range(prop_cnt):
                pname_len = struct.unpack("<h", r.read(2))[0]
                pname_bytes = r.read(pname_len)
                pname = pname_bytes.decode("utf-8", errors="replace")
                out.write(struct.pack("<h", pname_len) + pname_bytes)

                ptype, pstatus = struct.unpack("<bb", r.read(2))
                out.write(struct.pack("<bb", ptype, pstatus))

                if ptype == 1:  # Object
                    out.write(r.read(8))
                elif ptype == 2:  # String
                    val_len = struct.unpack("<h", r.read(2))[0]
                    orig_val = r.read(val_len).decode("utf-8", errors="replace")
                    lookup_key = (formid_24bit, sname.lower(), pname.lower())
                    if lookup_key in vmad_translations:
                        new_text = vmad_translations[lookup_key]
                        new_bytes = new_text.encode("utf-8")
                        out.write(struct.pack("<h", len(new_bytes)) + new_bytes)
                        applied += 1
                    else:
                        out.write(struct.pack("<h", val_len) + orig_val.encode("utf-8"))
                elif ptype in [3, 4]:  # Int, Float
                    out.write(r.read(4))
                elif ptype == 5:  # Bool
                    out.write(r.read(1))
                elif ptype == 11:  # Array of Object
                    cnt = struct.unpack("<i", r.read(4))[0]
                    out.write(struct.pack("<i", cnt) + r.read(cnt * 8))
                elif ptype == 12:  # Array of String
                    cnt = struct.unpack("<i", r.read(4))[0]
                    out.write(struct.pack("<i", cnt))
                    for arr_i in range(cnt):
                        v_len = struct.unpack("<h", r.read(2))[0]
                        orig_val = r.read(v_len).decode("utf-8", errors="replace")
                        lookup_key = (formid_24bit, sname.lower(), f"{pname}[{arr_i}]".lower())
                        if lookup_key in vmad_translations:
                            new_text = vmad_translations[lookup_key]
                            new_bytes = new_text.encode("utf-8")
                            out.write(struct.pack("<h", len(new_bytes)) + new_bytes)
                            applied += 1
                        else:
                            out.write(struct.pack("<h", v_len) + orig_val.encode("utf-8"))
                elif ptype in [13, 14]:
                    cnt = struct.unpack("<i", r.read(4))[0]
                    out.write(struct.pack("<i", cnt) + r.read(cnt * 4))
                elif ptype == 15:
                    cnt = struct.unpack("<i", r.read(4))[0]
                    out.write(struct.pack("<i", cnt) + r.read(cnt))

        # Копируем остаток если есть (фрагменты квестов)
        rem = r.read()
        if rem:
            out.write(rem)

        return out.getvalue(), applied


def inject_and_deploy_mod(
    plugin_name: str,
    original_mod_folder: Path,
    review_file: Path,
    mo2_mods_dir: Path,
    mo2_profile_dir: Path,
) -> Dict[str, Any]:
    """
    Универсальный оркестратор для прямого инжекта и деплоя любого мода в MO2.
    """
    clean_plugin = plugin_name.strip()
    source_esp = original_mod_folder / clean_plugin
    
    mod_base_name = original_mod_folder.name
    ru_mod_folder = mo2_mods_dir / f"{mod_base_name} [RU]"
    target_esp = ru_mod_folder / clean_plugin

    res = ESPInjector.inject_translations(
        source_esp=source_esp,
        target_esp=target_esp,
        review_file=review_file,
    )

    # Обновляем modlist.txt
    modlist_path = mo2_profile_dir / "modlist.txt"
    if modlist_path.exists():
        lines = modlist_path.read_text(encoding="utf-8").splitlines()
        ru_entry = f"+{ru_mod_folder.name}"
        orig_entry = f"+{original_mod_folder.name}"

        # Удаляем старые записи если были
        lines = [l for l in lines if l != ru_entry and l != f"-{ru_mod_folder.name}"]

        if orig_entry in lines:
            idx = lines.index(orig_entry)
            lines.insert(idx, ru_entry)
        else:
            lines.insert(0, ru_entry)

        modlist_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        res["modlist_updated"] = True
    else:
        res["modlist_updated"] = False

    return res
