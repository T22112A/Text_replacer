# libs.py

# Các hàm dùng chung, không phụ thuộc UI

# Ví dụ:
# def detect_encoding(...):
#     ...

# def save_duplicate_to_excel(...):
#     ...

# def split_long_lines(...):
#     ...

# def patch_bytes(...):
#     ...

# ... 

import os
import sys
import pandas as pd

# Hàm lấy đường dẫn resource (dùng cho PyInstaller)
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Lưu các dòng trùng lặp vào file Excel
def save_duplicate_to_excel(duplicate_info, file_path="Duplicate.xlsx"):
    if not duplicate_info:
        return 0
    from collections import defaultdict
    group = defaultdict(list)
    for ln, src, tgt in sorted(duplicate_info):
        group[src].append((ln, src, tgt))
    rows = []
    for idx, (src, lst) in enumerate(group.items()):
        seen_lines = set()
        for ln, s, tgt in sorted(lst):
            key = (ln, s, tgt)
            if key not in seen_lines:
                rows.append({"Dòng": ln, "Từ khóa trùng": s, "Giá trị": tgt})
                seen_lines.add(key)
        rows.append({"Dòng": "---", "Từ khóa trùng": "", "Giá trị": ""})
    if rows and rows[-1].get("Dòng") == "---":
        rows.pop()
    df = pd.DataFrame(rows)
    df.to_excel(file_path, index=False)
    return len(group)

# Lưu và cập nhật file Excel khi có dòng trùng
def save_duplicate_and_update_xlsx(duplicate_info, orig_xlsx, file_path="Duplicate.xlsx"):
    if not duplicate_info:
        return 0
    df = pd.read_excel(orig_xlsx, dtype=str)
    duplicate_rows_idx = set()
    for ln, src, tgt in duplicate_info:
        duplicate_rows_idx.add(ln - 2)
    group_count = save_duplicate_to_excel(duplicate_info, file_path)
    df_clean = df.drop(index=list(duplicate_rows_idx))
    df_clean.to_excel(orig_xlsx, index=False)
    return group_count

# Phát hiện encoding file
def detect_encoding(file_path, sample_size=10000):
    import chardet
    with open(file_path, 'rb') as f:
        detector = chardet.universaldetector.UniversalDetector()
        for line in f:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
    encoding = detector.result['encoding']
    if encoding and encoding.lower() == "macroman":
        return "windows-1252", "MacRoman"
    return encoding, encoding

# Chuyển chuỗi hex sang bytes
def parse_hex_string(s):
    try:
        s = s.strip().replace(",", " ")
        parts = s.split()
        if len(parts) > 1 and all(p.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in p) for p in parts):
            arr = []
            for p in parts:
                arr.append(int(p, 16))
            return bytes(arr)
        else:
            return s.encode("utf-8")
    except Exception:
        return s.encode("utf-8")

# Patch bytes cho file nhị phân
def patch_bytes(original_bytes, patch_list):
    arr = bytearray(original_bytes)
    for offset, value_bytes in patch_list:
        arr[offset:offset+len(value_bytes)] = value_bytes
    return bytes(arr)

# Tách dòng dài
def split_long_lines(text, limit, append_vars=None):
    import re
    if limit <= 0:
        return text
    append_vars = append_vars or []
    append_str = ''.join(append_vars)
    append_cost = len(append_vars)
    forbidden_first = set(['.', ',', ';', '?', '!'])
    lines = text.splitlines(keepends=True)
    result = []
    for line in lines:
        match = re.match(r'^(.*?)(\r\n|\n|\r)?$', line)
        content, line_ending = match.group(1), match.group(2) or ''
        if not content:
            result.append(line_ending)
            continue
        current = content
        if not append_str:
            parts = []
            while len(current) > limit:
                split_pos = current.rfind(' ', 0, limit + 1)
                if split_pos <= 0:
                    split_pos = limit
                part = current[:split_pos].rstrip()
                rest = current[split_pos:].lstrip()
                while rest and rest[0] in forbidden_first:
                    part += rest[0]
                    rest = rest[1:]
                parts.append(part + '\n')
                current = rest
            parts.append(current + line_ending)
            result.extend(parts)
        else:
            buffer = ""
            while len(current) + append_cost > limit:
                max_len = limit - append_cost
                split_pos = current.rfind(' ', 0, max_len + 1)
                if split_pos <= 0:
                    split_pos = max_len
                part = current[:split_pos].rstrip()
                rest = current[split_pos:].lstrip()
                while rest and rest[0] in forbidden_first:
                    part += rest[0]
                    rest = rest[1:]
                buffer += part + append_str
                current = rest
            buffer += current + line_ending
            result.append(buffer)
    return ''.join(result) 