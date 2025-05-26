APP_VERSION = "1.50"

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re

missing_libs = []

try:
    import chardet
except ImportError:
    missing_libs.append("chardet")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    missing_libs.append("pandas")

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    if PANDAS_AVAILABLE:
        missing_libs.append("openpyxl")

try:
    from flashtext import KeywordProcessor
    FLASHTEXT_AVAILABLE = True
except ImportError:
    FLASHTEXT_AVAILABLE = False
    missing_libs.append("flashtext")

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
    try:
        RESAMPLE = Image.Resampling.LANCZOS
    except AttributeError:
        RESAMPLE = Image.LANCZOS
except ImportError:
    PIL_AVAILABLE = False
    missing_libs.append("pillow")
    RESAMPLE = None

def show_missing_libs_and_exit():
    if missing_libs:
        msg = (
            "Một số thư viện bắt buộc chưa được cài đặt:\n\n"
            + "\n".join(f"- {lib}" for lib in missing_libs)
            + "\n\nBạn hãy chạy lệnh sau trong terminal/cmd để cài đặt:\n"
            + "pip install " + " ".join(set(missing_libs))
        )
        messagebox.showerror("Thiếu thư viện ngoài", msg)
        sys.exit(1)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def save_duplicate_to_excel(duplicate_info, file_path="Duplicate.xlsx"):
    if not PANDAS_AVAILABLE:
        raise ImportError("Chưa cài pandas. Vui lòng chạy: pip install pandas openpyxl")
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

def save_duplicate_and_update_xlsx(duplicate_info, orig_xlsx, file_path="Duplicate.xlsx"):
    if not PANDAS_AVAILABLE:
        raise ImportError("Chưa cài pandas. Vui lòng chạy: pip install pandas openpyxl")
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

def detect_encoding(file_path, sample_size=10000):
    if "chardet" in missing_libs:
        raise ImportError("Chưa cài chardet. Vui lòng chạy: pip install chardet")
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

def load_dictionary_txt(dict_file, encoding, show_popup=None):
    translation_dict = {}
    duplicate_info = []
    line_number_map = {}

    with open(dict_file, 'r', encoding=encoding) as f:
        for i, line in enumerate(f, 1):
            if '=' in line:
                src, tgt = line.strip().split('=', 1)
                src = src.strip()
                tgt = tgt.strip()
                if src in translation_dict:
                    duplicate_info.append((i, src, tgt))
                    if src in line_number_map:
                        prev_line = line_number_map[src]
                        duplicate_info.append((prev_line, src, translation_dict[src]))
                translation_dict[src] = tgt
                if src not in line_number_map:
                    line_number_map[src] = i

    if duplicate_info:
        group_count = save_duplicate_to_excel(duplicate_info, "Duplicate.xlsx")
        if show_popup:
            show_popup(
                f"Phát hiện dòng trùng trong từ điển {os.path.basename(dict_file)}",
                f"Đã lưu {group_count} cặp trùng vào Duplicate.xlsx.\n"
                f"(File từ điển: {os.path.basename(dict_file)})\n"
                f"\nLưu ý: File từ điển dạng TXT sẽ không tự động xóa dòng trùng!\n"
                f"Bạn nên kiểm tra file Duplicate.xlsx và tự chỉnh lại file TXT nếu cần."
            )
        raise Exception("DUPLICATE_DETECTED")

    return translation_dict

def load_dictionary_excel(excel_file, sheet_name=0, show_popup=None):
    if not PANDAS_AVAILABLE:
        raise ImportError("Chưa cài pandas. Vui lòng chạy: pip install pandas openpyxl")
    df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str)

    translation_dict = {}
    duplicate_info = []
    line_number_map = {}

    for idx, row in df.iterrows():
        src = str(row[0]).strip()
        tgt = str(row[1]).strip()
        excel_line = idx + 2
        if src in translation_dict:
            duplicate_info.append((excel_line, src, tgt))
            if src in line_number_map:
                prev_line = line_number_map[src]
                duplicate_info.append((prev_line, src, translation_dict[src]))
        translation_dict[src] = tgt
        if src not in line_number_map:
            line_number_map[src] = excel_line

    if duplicate_info:
        group_count = save_duplicate_and_update_xlsx(duplicate_info, excel_file, "Duplicate.xlsx")
        if show_popup:
            show_popup(
                f"Phát hiện dòng trùng trong từ điển {os.path.basename(excel_file)}",
                f"Đã lưu {group_count} cặp trùng vào Duplicate.xlsx.\n"
                f"(File từ điển: {os.path.basename(excel_file)})\n"
                f"\nCác dòng trùng này đã được xóa khỏi file từ điển {os.path.basename(excel_file)}!\n"
                f"Bạn nên kiểm tra file Duplicate.xlsx và chỉnh lại file từ điển nếu cần."
            )
        raise Exception("DUPLICATE_DETECTED")

    return translation_dict

def parse_hex_string(s):
    try:
        s = s.strip().replace(",", " ")
        parts = s.split()
        if len(parts) > 1 and all(p.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in p) for p in parts):
            arr = []
            for p in parts:
                if p.startswith("0x"):
                    arr.append(int(p, 16))
                else:
                    arr.append(int(p, 16))
            return bytes(arr)
        else:
            return s.encode("utf-8")
    except Exception:
        return s.encode("utf-8")

def load_patch_data_xlsx(file_path, show_popup=None):
    if not PANDAS_AVAILABLE:
        raise ImportError("Chưa cài pandas. Vui lòng chạy: pip install pandas openpyxl")
    import pandas as pd
    df = pd.read_excel(file_path, dtype=str)
    columns = list(df.columns)
    if len(columns) < 3:
        if show_popup:
            show_popup("Thiếu cột C", "File patch_data.xlsx phải có 3 cột: Offset, Value, Số bytes ghi (C).")
        raise Exception("Thiếu cột C")

    patch_list = []
    valid_indices = []
    written_ranges = []  # (start, end, idx, row)
    group_dict = {}      # (offset_int, byte_len_int) -> list of (idx, row)

    overlap_groups = []  # list of lists, mỗi group là một list các dòng trùng offset
    overlap_pairs = []   # từng cặp chồng lấn (ko phải trùng hoàn toàn)

    # 1. Gom nhóm các dòng trùng hoàn toàn offset + length
    for idx, row in df.iterrows():
        offset = row[0]
        value = row[1]
        byte_len = row[2] if len(row) > 2 else ""
        if not offset or not value or not byte_len:
            continue
        try:
            offset_int = int(offset, 0)
            byte_len_int = int(byte_len)
            assert byte_len_int > 0
        except Exception:
            continue
        group_key = (offset_int, byte_len_int)
        group_dict.setdefault(group_key, []).append( (idx, row) )

    # Đánh dấu các dòng thuộc nhóm trùng offset
    grouped_trung_offset_idx = set()
    for grp in group_dict.values():
        if len(grp) >= 2:
            overlap_groups.append(grp)
            for idx, _ in grp:
                grouped_trung_offset_idx.add(idx)

    # 2. Duyệt lại để kiểm tra chồng lấn, bỏ qua các dòng đã nằm trong nhóm trùng offset
    for idx, row in df.iterrows():
        if idx in grouped_trung_offset_idx:
            continue
        offset = row[0]
        value = row[1]
        byte_len = row[2] if len(row) > 2 else ""
        if not offset or not value or not byte_len:
            continue
        try:
            offset_int = int(offset, 0)
            byte_len_int = int(byte_len)
        except Exception:
            continue

        start = offset_int
        end = offset_int + byte_len_int - 1

        # Kiểm tra chồng lấn vùng ghi với các vùng đã ghi trước đó
        overlap_found = False
        for s, e, idx_gay, row_gay in written_ranges:
            if not (end < s or start > e):
                overlap_pairs.append((
                    dict(row_gay), dict(row), idx_gay, idx, "Gây chồng lấn"
                ))
                overlap_found = True
                break
        if overlap_found:
            continue

        value_bytes = parse_hex_string(value)
        if len(value_bytes) > byte_len_int:
            overlap_pairs.append((
                None,
                dict(row) | {"Ghi chú": "Value dài hơn số bytes ghi"},
                None,
                idx,
                "Value dài hơn số bytes ghi"
            ))
            continue
        if len(value_bytes) < byte_len_int:
            value_bytes = value_bytes + b"\x00" * (byte_len_int - len(value_bytes))
        patch_list.append((offset_int, value_bytes))
        valid_indices.append(idx)
        written_ranges.append((start, end, idx, row))

    # Xuất Overlap.xlsx nếu có lỗi
    if overlap_groups or overlap_pairs:
        overlap_rows = []
        # Nhóm các dòng trùng offset
        for group in overlap_groups:
            for idx, row in group:
                row_new = dict(row).copy()
                row_new["Loại"] = "Trùng Offset"
                row_new["Dòng"] = str(idx+2)
                overlap_rows.append(row_new)
            # Ngăn cách giữa các nhóm: dòng "---"
            sep_row = {col: "" for col in overlap_rows[-1].keys()}
            sep_row["Loại"] = "---"
            overlap_rows.append(sep_row)
        # Các cặp chồng lấn hoặc lỗi value
        for pair in overlap_pairs:
            row1, row2, idx1, idx2, loai = pair
            if loai == "Gây chồng lấn":
                row1_new = row1.copy()
                row1_new["Loại"] = "Gây chồng lấn"
                row1_new["Dòng"] = str(idx1+2)
                overlap_rows.append(row1_new)
                row2_new = row2.copy()
                row2_new["Loại"] = "Bị chồng lấn"
                row2_new["Dòng"] = str(idx2+2)
                overlap_rows.append(row2_new)
            elif loai == "Value dài hơn số bytes ghi":
                row2_new = row2.copy()
                row2_new["Loại"] = "Value dài hơn số bytes ghi"
                row2_new["Dòng"] = str(idx2+2)
                overlap_rows.append(row2_new)
            sep_row = {col: "" for col in overlap_rows[-1].keys()}
            sep_row["Loại"] = "---"
            overlap_rows.append(sep_row)

        overlap_df = pd.DataFrame(overlap_rows)
        overlap_df.to_excel("Overlap.xlsx", index=False)
        # Loại tất cả idx thuộc nhóm trùng offset và idx thuộc pair khỏi patch_list
        all_overlap_idx = set(grouped_trung_offset_idx)
        for row1, row2, idx1, idx2, loai in overlap_pairs:
            if idx1 is not None:
                all_overlap_idx.add(idx1)
            if idx2 is not None:
                all_overlap_idx.add(idx2)
        cleaned_df = df.drop(index=[i for i in df.index if i not in valid_indices or i in all_overlap_idx])
        cleaned_df.to_excel(file_path, index=False)
        msg = (
            f"Phát hiện {len(overlap_groups)} nhóm dòng trùng offset và {len(overlap_pairs)} trường hợp lỗi khác.\n"
            "Các dòng này đã được lưu vào Overlap.xlsx và xóa khỏi patch_data.xlsx.\n"
            "Hãy kiểm tra lại file Overlap.xlsx!"
        )
        if show_popup:
            show_popup("Lỗi dữ liệu patch", msg)
    return patch_list

def patch_bytes(original_bytes, patch_list):
    arr = bytearray(original_bytes)
    for offset, value_bytes in patch_list:
        arr[offset:offset+len(value_bytes)] = value_bytes
    return bytes(arr)

def replacing_progress(content, translation_dict, progress_callback, auto_split=False, split_limit=80, append_vars=None):
    if not FLASHTEXT_AVAILABLE:
        raise ImportError("Chưa cài flashtext. Vui lòng chạy: pip install flashtext")

    keys = sorted(translation_dict, key=len, reverse=True)

    try:
        from flashtext import KeywordProcessor
        keyword_processor = KeywordProcessor()
        for k in keys:
            v = translation_dict[k]
            if k:
                keyword_processor.add_keyword(k, v)

        total_len = len(content)
        chunk_size = 256 * 1024
        result_chunks = []

        for i in range(0, total_len, chunk_size):
            chunk = content[i:i+chunk_size]
            replaced_chunk = keyword_processor.replace_keywords(chunk)

            if auto_split:
                replaced_chunk = split_long_lines(replaced_chunk, split_limit, append_vars)

            result_chunks.append(replaced_chunk)

            percent = min(100, (i + chunk_size) / total_len * 100)
            progress_callback(percent)

        progress_callback(100)
        return ''.join(result_chunks)

    except Exception as e:
        print(f"FlashText gặp lỗi! Đang chuyển sang phương pháp thay thế bằng regex. Lỗi: {e}")

        pattern = re.compile('|'.join(re.escape(k) for k in keys))
        total_len = len(content)
        chunk_size = 256 * 1024
        result_chunks = []

        for i in range(0, total_len, chunk_size):
            chunk = content[i:i+chunk_size]
            replaced_chunk = pattern.sub(lambda m: translation_dict[m.group(0)], chunk)

            if auto_split:
                replaced_chunk = split_long_lines(replaced_chunk, split_limit, append_vars)

            result_chunks.append(replaced_chunk)

            percent = min(100, (i + chunk_size) / total_len * 100)
            progress_callback(percent)

        progress_callback(100)
        return ''.join(result_chunks)

def reading_progress(original_file, input_encoding, progress_callback):
    file_size = os.path.getsize(original_file)
    read_size = 0
    content = ""
    with open(original_file, 'r', encoding=input_encoding, errors='replace') as f_in:
        while True:
            chunk = f_in.read(8 * 1024)
            if not chunk:
                break
            content += chunk
            read_size += len(chunk.encode(input_encoding, errors='ignore'))
            percent = min(100, read_size / file_size * 100) if file_size > 0 else 100
            progress_callback(percent)
    progress_callback(100)
    return content

def split_long_lines(text, limit, append_vars=None):
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

def saving_progress(output_file, content, progress_callback):
    total = len(content)
    chunk_size = 8 * 1024
    written = 0
    SIMULATE_DELAY = False
    SMALL_FILE_SIZE = 20 * 1024 * 1024
    if total <= SMALL_FILE_SIZE:
        SIMULATE_DELAY = True
    with open(output_file, 'w', encoding='utf-8') as f_out:
        for i in range(0, total, chunk_size):
            chunk = content[i:i + chunk_size]
            f_out.write(chunk)
            f_out.flush()
            written += len(chunk)
            percent = min(100, written / total * 100)
            progress_callback(percent)
            if SIMULATE_DELAY:
                time.sleep(0.01)
    progress_callback(100)

def process_separated_progress(
    original_file, dict_file_path, update_status, progress_callback,
    status_progress_label, on_save_done, show_popup,
    auto_split, split_limit, input_encoding,
    append_vars=None, return_content=False):

    try:
        if dict_file_path is None:
            messagebox.showerror(
                "Không tìm thấy dữ liệu",
                "Không tìm thấy dữ liệu mặc định (patch_data.xlsx hoặc patch_data.txt) trong thư mục hiện tại.\n"
                "Vui lòng chọn tệp dữ liệu hoặc thêm file patch_data.xlsx/txt vào thư mục!"
            )
            status_progress_label("Chờ thao tác...")
            progress_callback(0)
            return None if return_content else None
        if dict_file_path.lower().endswith('.xlsx'):
            if not PANDAS_AVAILABLE or not OPENPYXL_AVAILABLE:
                raise ImportError("Chưa cài pandas hoặc openpyxl. Vui lòng chạy: pip install pandas openpyxl")
            translation_dict = load_dictionary_excel(dict_file_path, show_popup=show_popup)
        elif dict_file_path.lower().endswith('.txt'):
            if "chardet" in missing_libs:
                raise ImportError("Chưa cài chardet. Vui lòng chạy: pip install chardet")
            dict_encoding, _ = detect_encoding(dict_file_path)
            translation_dict = load_dictionary_txt(dict_file_path, dict_encoding, show_popup=show_popup)
        else:
            messagebox.showerror("Lỗi", "Vui lòng chọn dữ liệu định dạng .xlsx hoặc .txt.")
            status_progress_label("Chờ thao tác...")
            progress_callback(0)
            return None if return_content else None

        status_progress_label("Đang đọc tệp...")
        progress_callback(0)
        content = reading_progress(original_file, input_encoding, progress_callback)
        status_progress_label("Đang thay thế...")
        progress_callback(0)
        content = replacing_progress(content, translation_dict, progress_callback, auto_split, split_limit, append_vars)
        if return_content:
            progress_callback(100)
            status_progress_label("Xử lý xong!")
            return content
        status_progress_label("Đang lưu tệp...")
        progress_callback(0)
        base_name = os.path.splitext(original_file)[0]
        output_file = base_name + "_translated.txt"
        saving_progress(output_file, content, progress_callback)
        status_progress_label("Hoàn thành!")
        if on_save_done:
            on_save_done(output_file)
        return None
    except Exception as e:
        if str(e) == "DUPLICATE_DETECTED":
            status_progress_label("Chờ thao tác...")
            progress_callback(0)
            return None if return_content else None
        status_progress_label(f"Lỗi: {str(e)}")
        messagebox.showerror("Lỗi", str(e))
        return None if return_content else None

class TextReplacerApp(tk.Tk):

    def __init__(self):

        super().__init__()
        self.title(f"Text Replacer v{APP_VERSION}")
        self.geometry("760x530")
        self.resizable(False, False)
        self.selected_data_file = None
        self.selected_input_file = None
        self.detected_encoding = None
        self.raw_detected_encoding = None

        self.after(50, show_missing_libs_and_exit)


        self.label = tk.Label(
            self,
            text="Chọn tệp dữ liệu (xlsx/txt) và tệp gốc cần xử lý hoặc xuất",
            font=("Arial", 12)
        )
        self.label.pack(pady=8)

        frm = tk.Frame(self)
        frm.pack(pady=5, fill=tk.X)

        self.icon_state = 0
        self.icon_paths = [
            resource_path("TEXT.png"),
            resource_path("HEX.png")
        ]
        self.icon_images = [None, None]

        if PIL_AVAILABLE:
            for idx, path in enumerate(self.icon_paths):
                try:
                    img = Image.open(path)
                    img = img.resize((128, 128), RESAMPLE)
                    self.icon_images[idx] = ImageTk.PhotoImage(img)
                except Exception:
                    self.icon_images[idx] = None
        if self.icon_images[0]:
            self.icon_button = tk.Button(
                frm,
                image=self.icon_images[0],
                width=132, height=132,
                command=self.toggle_icon
            )
        else:
            self.icon_button = tk.Button(
                frm,
                text="TEXT",
                width=12, height=6,
                command=self.toggle_icon
            )
        self.icon_button.grid(row=0, column=0, rowspan=7, padx=(8, 5), pady=2, sticky="nw")

        self.data_label = tk.Label(
            frm,
            text="Dữ liệu:",
            font=("Arial", 10)
        )
        self.data_label.grid(row=0, column=1, sticky="e", padx=(0, 3), pady=2)

        self.data_file_var = tk.StringVar()
        self.set_data_file_var_default()
        self.data_file_display = tk.Label(
            frm,
            textvariable=self.data_file_var,
            width=38,
            anchor='w',
            relief=tk.SUNKEN,
            font=("Arial", 10),
            height=1
        )
        self.data_file_display.grid(row=0, column=2, padx=3, pady=2, sticky="ew")
        self.btn_select_data = tk.Button(
            frm,
            text="Chọn dữ liệu",
            command=self.select_data_file,
            font=("Arial", 10),
            height=1, width=13
        )
        self.btn_select_data.grid(row=0, column=3, padx=(3, 0), pady=2, sticky="ew")

        self.input_label = tk.Label(
            frm,
            text="Tệp gốc:", font=("Arial", 10)
        )
        self.input_label.grid(row=1, column=1, sticky="e", padx=(0, 3), pady=2)
        self.input_file_var = tk.StringVar(value="(Chưa chọn tệp)")
        self.input_file_display = tk.Label(
            frm,
            textvariable=self.input_file_var,
            width=38,
            anchor='w',
            relief=tk.SUNKEN,
            font=("Arial", 10),
            height=1
        )
        self.input_file_display.grid(row=1, column=2, padx=3, pady=2, sticky="ew")
        self.btn_select_input = tk.Button(
            frm,
            text="Chọn tệp",
            command=self.select_input_file,
            font=("Arial", 10),
            height=1, width=13
        )
        self.btn_select_input.grid(row=1, column=3, padx=(3, 0), pady=2, sticky="ew")

        self.encoding_values = [
            'utf-8', 'utf-8-sig', 'windows-1252',
            'shift_jis', 'cp932', 'euc-jp',
            'gbk', 'gb2312', 'gb18030', 'big5', 'hz',
            'ascii', 'utf-16', 'utf-16-le', 'utf-16-be',
            'cp437', 'cp850', 'iso-8859-1', 'iso-8859-2'
        ]
        self.encoding_labels = [
            "Unicode (UTF-8, đa ngôn ngữ)",
            "Unicode (UTF-8 BOM)",
            "ANSI (Windows-1252, tiếng Việt cũ)",
            "Tiếng Nhật (Shift_JIS)",
            "Tiếng Nhật (CP932, Windows)",
            "Tiếng Nhật (EUC-JP)",
            "Trung Quốc (GBK, Windows)",
            "Trung Quốc (GB2312, Simplified)",
            "Trung Quốc (GB18030, Unicode full)",
            "Trung Quốc (Big5, Phồn thể, Đài Loan/HK)",
            "Trung Quốc (HZ, cũ)",
            "ASCII (Mỹ)",
            "Unicode (UTF-16)",
            "Unicode (UTF-16 Little Endian)",
            "Unicode (UTF-16 Big Endian)",
            "MS-DOS (US, CP437)",
            "MS-DOS (Western Europe, CP850)",
            "Tây Âu (ISO-8859-1)",
            "Đông Âu (ISO-8859-2)"
        ]
        self.encoding_var = tk.StringVar(value="")
        self.encoding_combobox = ttk.Combobox(
            frm,
            textvariable=self.encoding_var,
            values=self.encoding_labels,
            width=32,
            font=('Arial', 10)
        )
        self.encoding_combobox.grid(row=2, column=2, sticky="w", pady=(2, 2))
        self.lbl_detect_encoding = tk.Label(
            frm,
            text="(Detect: ---)",
            font=("Arial", 9, "italic"),
            fg="#555", width=32, anchor='w'
        )
        self.lbl_detect_encoding.grid(row=2, column=2, padx=(250, 0), sticky="w")

        self.auto_split_var = tk.IntVar(value=0)
        self.chk_auto_split = tk.Checkbutton(
            frm,
            text="Tự động tách dòng khi đạt",
            variable=self.auto_split_var,
            font=("Arial", 10),
            command=self.on_auto_split_changed
        )
        self.chk_auto_split.grid(row=3, column=2, sticky="w", pady=(2, 2))

        self.split_limit_var = tk.StringVar(value="80")
        self.entry_split_limit = tk.Entry(frm, textvariable=self.split_limit_var, width=5, font=("Arial", 10))
        self.entry_split_limit.grid(row=3, column=2, padx=(200, 0), sticky="w")
        self.split_limit_label = tk.Label(frm, text="ký tự", font=("Arial", 10))
        self.split_limit_label.grid(row=3, column=2, padx=(250, 0), sticky="w")

        self.var_entries_frame = tk.Frame(frm)
        self.var_entries_frame.grid(row=4, column=2, columnspan=2, sticky="w", pady=(8, 0), padx=(0,0))
        self.use_default_vars_var = tk.IntVar(value=0)
        self.use_default_vars_chk = tk.Checkbutton(
            self.var_entries_frame,
            text="Thêm biến khi tách dòng (ví dụ: [0x0D], [0x0A])",
            variable=self.use_default_vars_var,
            command=self.toggle_default_vars,
            font=("Arial", 10)
        )
        self.use_default_vars_chk.pack(side="top", anchor="w", padx=0)

        self.rtk_radio_var = tk.IntVar(value=0)
        self.rtk_frame = tk.LabelFrame(self.var_entries_frame, text="Chọn mẫu biến nhanh", font=("Arial", 10))
        self.rtk1011_radio = tk.Radiobutton(
            self.rtk_frame, text="Romance of the Three Kingdoms 10,11...", variable=self.rtk_radio_var, value=1,
            command=self.on_rtk_radio_changed, font=("Arial", 10)
        )
        self.rtk14_radio = tk.Radiobutton(
            self.rtk_frame, text="Romance of the Three Kingdoms 14...", variable=self.rtk_radio_var, value=2,
            command=self.on_rtk_radio_changed, font=("Arial", 10)
        )
        self.rtk_khac_radio = tk.Radiobutton(
            self.rtk_frame, text="Game khác...", variable=self.rtk_radio_var, value=3,
            command=self.on_rtk_radio_changed, font=("Arial", 10)
        )
        self.rtk1011_radio.pack(side="top", anchor="w", pady=1)
        self.rtk14_radio.pack(side="top", anchor="w", pady=1)
        self.rtk_khac_radio.pack(side="top", anchor="w", pady=1)
        self.rtk_frame.pack_forget()

        self.vars_entries_subframe = tk.Frame(self.var_entries_frame)
        self.vars_entries_subframe.pack(side="top", anchor="w", pady=(2, 0))

        self.vars_dynamic_entries = []
        self.toggle_default_vars()
        self.on_auto_split_changed()

        frm.grid_columnconfigure(2, weight=1)

        self.btn_run = tk.Button(
            self, text="Thực hiện thay thế",
            command=self.run_processing, font=("Arial", 11),
            bg="#217346", fg="white", height=2
        )
        self.btn_run.pack(pady=6, ipadx=8, fill=tk.X, padx=16)

        self.status_var = tk.StringVar(value="Chờ thao tác...")
        self.status_label = tk.Label(self, textvariable=self.status_var, font=("Arial", 10))
        self.status_label.pack(pady=3)
        self.progress_label = tk.StringVar(value="Tiến trình:")
        self.progress_lbl = tk.Label(self, textvariable=self.progress_label)
        self.progress_lbl.pack()
        self.progress = ttk.Progressbar(self, orient='horizontal', length=520, mode='determinate')
        self.progress.pack(pady=2)

        self.update_hex_mode_ui()

    def set_data_file_var_default(self):
        if getattr(self, "icon_state", 0) == 1:
            self.data_file_var.set("(Mặc định: patch_data.xlsx)")
        else:
            self.data_file_var.set("(Mặc định: dictionary.xlsx / dictionary.txt)")

    def select_data_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Tệp dữ liệu (*.xlsx, *.txt)", "*.xlsx *.txt")]
        )
        if file_path:
            self.selected_data_file = file_path
            self.data_file_var.set(os.path.basename(file_path))
        else:
            self.selected_data_file = None
            self.set_data_file_var_default()

    def select_input_file(self):
        file_path = None
        if self.icon_state == 1:
            file_path = filedialog.askopenfilename(
                title="Chọn file gốc để patch (HEX)",
                filetypes=[("Binary files", "*.*"), ("All Files", "*.*")]
            )
        else:
            file_path = filedialog.askopenfilename(
                filetypes=[("Tệp văn bản (*.txt)", "*.txt")]
            )
        if file_path:
            self.selected_input_file = file_path
            self.input_file_var.set(os.path.basename(file_path))
            try:
                encoding, raw_encoding = detect_encoding(file_path)
                self.detected_encoding = encoding
                self.raw_detected_encoding = raw_encoding
                if encoding:
                    if encoding != raw_encoding:
                        self.lbl_detect_encoding.config(
                            text=f"(Detect: {encoding} / {raw_encoding})")
                    else:
                        self.lbl_detect_encoding.config(
                            text=f"(Detect: {encoding})")
                else:
                    self.lbl_detect_encoding.config(text="(Detect: ???)")
            except Exception as e:
                self.detected_encoding = None
                self.raw_detected_encoding = None
                self.lbl_detect_encoding.config(text="(Detect: lỗi)")
        else:
            self.selected_input_file = None
            self.input_file_var.set("(Chưa chọn tệp)")
            self.lbl_detect_encoding.config(text="(Detect: ---)")

    def toggle_icon(self):
        self.icon_state = 1 - self.icon_state
        if self.icon_images[self.icon_state]:
            self.icon_button.config(image=self.icon_images[self.icon_state], text="")
        else:
            self.icon_button.config(image="", text="HEX" if self.icon_state else "TEXT")
        self.set_data_file_var_default()
        self.input_file_var.set("(Chưa chọn tệp)")
        self.selected_input_file = None
        self.update_hex_mode_ui()

    def update_hex_mode_ui(self):
        if self.icon_state == 1:
            self.chk_auto_split.grid_remove()
            self.entry_split_limit.grid_remove()
            self.split_limit_label.grid_remove()
            self.var_entries_frame.grid_remove()
            self.encoding_combobox.grid_remove()
            self.lbl_detect_encoding.grid_remove()
            self.btn_select_input.config(state="normal")
        else:
            self.chk_auto_split.grid()
            self.entry_split_limit.grid()
            self.split_limit_label.grid()
            self.var_entries_frame.grid()
            self.encoding_combobox.grid()
            self.lbl_detect_encoding.grid()
            self.btn_select_input.config(state="normal")

    def on_auto_split_changed(self):
        auto_split = self.auto_split_var.get() == 1
        state = "normal" if auto_split else "disabled"
        self.use_default_vars_chk.config(state=state)
        if not auto_split:
            self.use_default_vars_var.set(0)
            self.rtk_frame.pack_forget()
            self.clear_var_entries()
            entry = tk.Entry(self.vars_entries_subframe, width=10, font=("Arial", 10))
            entry.pack(side="left", padx=(5, 0))
            entry.config(state="disabled")
            self.vars_dynamic_entries.append(entry)
            for child in self.vars_entries_subframe.winfo_children():
                child.config(state="disabled")
        else:
            self.toggle_default_vars()

    def clear_var_entries(self):
        for e in self.vars_dynamic_entries:
            e.destroy()
        self.vars_dynamic_entries.clear()

    def update_var_entries_by_rtk(self):
        preset_vars = []
        radio = self.rtk_radio_var.get()
        if radio == 1:
            preset_vars = ['[0x0D]', '[0x0A]']
        elif radio == 2:
            preset_vars = ['[0x20]', '[0x29]']
        elif radio == 3:
            preset_vars = ['\\r', '\\n']
        current_values = [e.get() for e in self.vars_dynamic_entries]
        self.clear_var_entries()
        for v in preset_vars:
            entry = tk.Entry(self.vars_entries_subframe, width=10, font=("Arial", 10))
            entry.pack(side="left", padx=(5, 0))
            entry.insert(0, v)
            entry.config(state="normal")
            self.vars_dynamic_entries.append(entry)
        for v in current_values[len(preset_vars):]:
            entry = tk.Entry(self.vars_entries_subframe, width=10, font=("Arial", 10))
            entry.pack(side="left", padx=(5, 0))
            entry.insert(0, v)
            entry.config(state="normal")
            self.vars_dynamic_entries.append(entry)
        if not self.vars_dynamic_entries:
            entry = tk.Entry(self.vars_entries_subframe, width=10, font=("Arial", 10))
            entry.pack(side="left", padx=(5, 0))
            entry.config(state="normal")
            self.vars_dynamic_entries.append(entry)
        self.update_var_add_remove_buttons()

    def on_rtk_radio_changed(self):
        self.update_var_entries_by_rtk()

    def toggle_default_vars(self):
        self.clear_var_entries()
        if self.use_default_vars_var.get() == 1:
            self.rtk_frame.pack(side="top", anchor="w", fill="x", padx=12, pady=(2, 0))
            self.update_var_entries_by_rtk()
        else:
            self.rtk_frame.pack_forget()
            entry = tk.Entry(self.vars_entries_subframe, width=10, font=("Arial", 10))
            entry.pack(side="left", padx=(5, 0))
            entry.config(state="disabled")
            self.vars_dynamic_entries.append(entry)
        self.update_var_add_remove_buttons()

    def update_var_add_remove_buttons(self):
        if hasattr(self, 'add_var_btn') and self.add_var_btn.winfo_exists():
            self.add_var_btn.pack_forget()
        if hasattr(self, 'remove_var_btn') and self.remove_var_btn.winfo_exists():
            self.remove_var_btn.pack_forget()
        if self.use_default_vars_var.get() == 1 and self.auto_split_var.get() == 1:
            self.add_var_btn = tk.Button(self.vars_entries_subframe, text="+", width=2, command=self.on_add_var_btn)
            self.add_var_btn.pack(side="left", padx=(10, 0))
            self.remove_var_btn = tk.Button(self.vars_entries_subframe, text="-", width=2, command=self.on_remove_var_btn)
            self.remove_var_btn.pack(side="left")

    def on_add_var_btn(self):
        entry = tk.Entry(self.vars_entries_subframe, width=10, font=("Arial", 10))
        entry.pack(side="left", padx=(5, 0))
        entry.config(state="normal")
        self.vars_dynamic_entries.append(entry)
        self.update_var_add_remove_buttons()

    def on_remove_var_btn(self):
        if len(self.vars_dynamic_entries) > 1:
            entry = self.vars_dynamic_entries.pop()
            entry.destroy()
        self.update_var_add_remove_buttons()

    def run_processing(self):
        if self.icon_state == 0 and not self.selected_input_file:
            messagebox.showerror("Thiếu tệp gốc", "Vui lòng chọn tệp gốc (TEXT) hoặc (HEX).")
            return

        if self.icon_state == 1 and not self.selected_input_file:
            messagebox.showerror("Thiếu tệp gốc", "Vui lòng chọn tệp gốc để patch (HEX).")
            return

        data_file_to_use = self.selected_data_file
        if data_file_to_use is None:
            cwd = os.getcwd()
            if self.icon_state == 1:
                default_xlsx = os.path.join(cwd, "patch_data.xlsx")
            else:
                default_xlsx = os.path.join(cwd, "dictionary.xlsx")
                default_txt = os.path.join(cwd, "dictionary.txt")
            if os.path.exists(default_xlsx):
                data_file_to_use = default_xlsx
            elif self.icon_state == 0 and os.path.exists(default_txt):
                data_file_to_use = default_txt
            else:
                messagebox.showerror(
                    "Không tìm thấy dữ liệu",
                    f"Không tìm thấy file {'patch_data' if self.icon_state == 1 else 'dictionary'}.xlsx"
                    f"{'' if self.icon_state == 1 else ' hoặc .txt'}."
                )
                return

        try:
            split_limit = int(self.split_limit_var.get())
            if split_limit < 10 or split_limit > 1000:
                raise ValueError
        except Exception:
            split_limit = 80

        auto_split = self.auto_split_var.get() == 1

        label = self.encoding_var.get()
        if label in self.encoding_labels:
            encoding = self.encoding_values[self.encoding_labels.index(label)]
        else:
            encoding = self.detected_encoding or "utf-8"

        if self.use_default_vars_var.get() == 1:
            append_vars = [e.get() for e in self.vars_dynamic_entries if e.get().strip()]
        else:
            append_vars = []

        if self.icon_state == 0:
            self.status_var.set("Đang xử lý (TEXT)...")
            self.progress['value'] = 0
            self.progress_label.set("Tiến trình:")
            threading.Thread(
                target=self.process_file_text,
                args=(self.selected_input_file, data_file_to_use, auto_split, split_limit, encoding, append_vars),
                daemon=True
            ).start()
        else:
            self.status_var.set("Đang xử lý (HEX)...")
            self.progress['value'] = 0
            self.progress_label.set("Tiến trình:")
            threading.Thread(
                target=self.process_file_hex,
                args=(data_file_to_use, encoding),
                daemon=True
            ).start()

    def process_file_text(self, input_file, data_file, auto_split, split_limit, input_encoding, append_vars):
        self.update_status("Bắt đầu xử lý...")
        process_separated_progress(
            input_file,
            data_file,
            self.update_status,
            self.update_progress,
            self.update_progress_label,
            self.on_save_complete,
            self.show_popup,
            auto_split,
            split_limit,
            input_encoding,
            append_vars
        )


    def process_file_hex(self, data_file, input_encoding):
        self.update_status("Bắt đầu xử lý (HEX)...")

        input_file = self.selected_input_file
        if not input_file:
            messagebox.showerror("Thiếu tệp gốc", "Vui lòng chọn tệp gốc để patch (HEX).")
            self.update_status("Thiếu tệp gốc")
            return

        base_name, ext = os.path.splitext(input_file)
        output_file = f"{base_name}_patched{ext}"

        try:
            if not data_file.lower().endswith('.xlsx'):
                messagebox.showerror("Lỗi", "File patch chỉ hỗ trợ định dạng .xlsx với 3 cột: Offset, Value, Số bytes ghi.")
                return
            patch_list = load_patch_data_xlsx(
                data_file,
                show_popup=lambda title, msg: messagebox.showerror(title, msg)
            )
            if not patch_list:
                messagebox.showerror("Lỗi", "Không có patch nào hợp lệ trong file patch_data.xlsx.")
                return
            with open(input_file, "rb") as f:
                original_bytes = f.read()
            patched_bytes = patch_bytes(original_bytes, patch_list)
            with open(output_file, "wb") as f:
                f.write(patched_bytes)
            self.progress['value'] = 100
            self.progress_label.set("Hoàn thành!")
            self.update_status(f"Đã lưu file nhị phân: {os.path.basename(output_file)}")
            messagebox.showinfo("Thành công", f"Đã lưu tệp nhị phân:\n{output_file}")
        except Exception as e:
            if str(e) == "Thiếu cột C":
                self.update_status("Lỗi: Thiếu cột C")
            elif str(e) == "OVERLAP_DETECTED":
                self.update_status("Có dòng patch lỗi, đã xuất Overlap.xlsx")
            else:
                self.update_status(f"Lỗi HEX: {str(e)}")
            messagebox.showerror("Lỗi HEX", str(e))


    def update_status(self, text):
        if threading.current_thread() is threading.main_thread():
            self.status_var.set(text)
            self.update_idletasks()
        else:
            self.after(0, self.update_status, text)

    def update_progress(self, percent):
        if threading.current_thread() is threading.main_thread():
            self.progress['value'] = percent
            self.update_idletasks()
        else:
            self.after(0, self.update_progress, percent)

    def update_progress_label(self, text):
        if threading.current_thread() is threading.main_thread():
            self.progress_label.set(text)
            self.update_idletasks()
        else:
            self.after(0, self.update_progress_label, text)

    def show_popup(self, title, msg):
        self.after(0, lambda: messagebox.showinfo(title, msg, parent=self))

    def on_save_complete(self, output_file):
        self.update_status("Hoàn thành!")
        self.progress['value'] = 100
        self.progress_label.set("Hoàn thành!")
        messagebox.showinfo("Thành công", f"Đã lưu tệp kết quả:\n{output_file}")

if __name__ == "__main__":
    app = TextReplacerApp()
    app.mainloop()