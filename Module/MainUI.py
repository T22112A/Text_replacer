# MainUI.py

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dependency_checker import check_and_install_dependencies
from Functions import process_separated_progress, load_patch_data_xlsx
from libs import resource_path, patch_bytes
from config import LABELS, ENCODING_VALUES, ENCODING_LABELS, PRESET_VARS

class TextReplacerApp(tk.Tk):
    def __init__(self):
        check_and_install_dependencies()
        super().__init__()
        self.title(f"Text Replacer v1.50")
        self.geometry("760x530")
        self.resizable(False, False)
        self.selected_data_file = None
        self.selected_input_file = None
        self.detected_encoding = None
        self.raw_detected_encoding = None

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

        try:
            from PIL import Image, ImageTk
            from libs import RESAMPLE
            for idx, path in enumerate(self.icon_paths):
                try:
                    img = Image.open(path)
                    img = img.resize((128, 128), RESAMPLE)
                    self.icon_images[idx] = ImageTk.PhotoImage(img)
                except Exception:
                    self.icon_images[idx] = None
        except ImportError:
            pass
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

        self.encoding_values = ENCODING_VALUES
        self.encoding_labels = ENCODING_LABELS
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
                from libs import detect_encoding
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