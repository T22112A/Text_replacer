# config.py

# App version
APP_VERSION = "1.50"

# UI Labels
LABELS = {
    "title": "Text Replacer v{version}",
    "select_data": "Chọn dữ liệu",
    "select_input": "Chọn tệp",
    "data": "Dữ liệu:",
    "input": "Tệp gốc:",
    "default_data_text": "(Mặc định: dictionary.xlsx / dictionary.txt)",
    "default_data_hex": "(Mặc định: patch_data.xlsx)",
    "default_input": "(Chưa chọn tệp)",
    "progress": "Tiến trình:",
    "done": "Hoàn thành!",
    # ... thêm các label khác ...
}

# Encoding options
ENCODING_VALUES = [
    'utf-8', 'utf-8-sig', 'windows-1252',
    'shift_jis', 'cp932', 'euc-jp',
    'gbk', 'gb2312', 'gb18030', 'big5', 'hz',
    'ascii', 'utf-16', 'utf-16-le', 'utf-16-be',
    'cp437', 'cp850', 'iso-8859-1', 'iso-8859-2'
]
ENCODING_LABELS = [
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

# MessageBox texts
MESSAGES = {
    "missing_libs": "Một số thư viện bắt buộc chưa được cài đặt:\n\n{libs}\n\nBạn hãy chạy lệnh sau trong terminal/cmd để cài đặt:\n{cmd}",
    "select_data_file": "Vui lòng chọn tệp dữ liệu (xlsx/txt).",
    "select_input_file": "Vui lòng chọn tệp gốc (TEXT) hoặc (HEX).",
    "not_found_data": "Không tìm thấy dữ liệu",
    "not_found_input": "Không tìm thấy tệp gốc",
    # ... thêm các message khác ...
}

# Các preset biến tách dòng
PRESET_VARS = {
    "rtk1011": ['[0x0D]', '[0x0A]'],
    "rtk14": ['[0x20]', '[0x29]'],
    "other": ['\\r', '\\n']
}

# ... Thêm các cấu hình khác nếu cần ... 