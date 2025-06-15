# Functions.py

# Các hàm xử lý đặc thù cho app

# Ví dụ:
# def process_separated_progress(...):
#     ...

# def load_dictionary_txt(...):
#     ...

# def load_dictionary_excel(...):
#     ...

# def load_patch_data_xlsx(...):
#     ...

# ... 

import os
import re
import pandas as pd
from libs import save_duplicate_to_excel, save_duplicate_and_update_xlsx, parse_hex_string, split_long_lines

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

def load_patch_data_xlsx(file_path, show_popup=None):
    df = pd.read_excel(file_path, dtype=str)
    columns = list(df.columns)
    if len(columns) < 3:
        if show_popup:
            show_popup("Thiếu cột C", "File patch_data.xlsx phải có 3 cột: Offset, Value, Số bytes ghi (C).")
        raise Exception("Thiếu cột C")
    patch_list = []
    valid_indices = []
    written_ranges = []
    group_dict = {}
    overlap_groups = []
    overlap_pairs = []
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
    grouped_trung_offset_idx = set()
    for grp in group_dict.values():
        if len(grp) >= 2:
            overlap_groups.append(grp)
            for idx, _ in grp:
                grouped_trung_offset_idx.add(idx)
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
    if overlap_groups or overlap_pairs:
        overlap_rows = []
        for group in overlap_groups:
            for idx, row in group:
                row_new = dict(row).copy()
                row_new["Loại"] = "Trùng Offset"
                row_new["Dòng"] = str(idx+2)
                overlap_rows.append(row_new)
            sep_row = {col: "" for col in overlap_rows[-1].keys()}
            sep_row["Loại"] = "---"
            overlap_rows.append(sep_row)
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

def replacing_progress(content, translation_dict, progress_callback, auto_split=False, split_limit=80, append_vars=None):
    from flashtext import KeywordProcessor
    keys = sorted(translation_dict, key=len, reverse=True)
    try:
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
        import re
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
                import time
                time.sleep(0.01)
    progress_callback(100)

def process_separated_progress(
    original_file, dict_file_path, update_status, progress_callback,
    status_progress_label, on_save_done, show_popup,
    auto_split, split_limit, input_encoding,
    append_vars=None, return_content=False):
    try:
        if dict_file_path is None:
            if show_popup:
                show_popup(
                    "Không tìm thấy dữ liệu",
                    "Không tìm thấy dữ liệu mặc định (patch_data.xlsx hoặc patch_data.txt) trong thư mục hiện tại.\n"
                    "Vui lòng chọn tệp dữ liệu hoặc thêm file patch_data.xlsx/txt vào thư mục!"
                )
            status_progress_label("Chờ thao tác...")
            progress_callback(0)
            return None if return_content else None
        if dict_file_path.lower().endswith('.xlsx'):
            translation_dict = load_dictionary_excel(dict_file_path, show_popup=show_popup)
        elif dict_file_path.lower().endswith('.txt'):
            dict_encoding, _ = detect_encoding(dict_file_path)
            translation_dict = load_dictionary_txt(dict_file_path, dict_encoding, show_popup=show_popup)
        else:
            if show_popup:
                show_popup("Lỗi", "Vui lòng chọn dữ liệu định dạng .xlsx hoặc .txt.")
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
        if show_popup:
            show_popup("Lỗi", str(e))
        return None if return_content else None 