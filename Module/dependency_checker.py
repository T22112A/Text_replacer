# dependency_checker.py

import sys
import subprocess
import importlib.util
import pkg_resources

def install(package):
    """Cài đặt một package bằng pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi cài đặt {package}: {e}")
        return False
    return True

def is_module_available(module_name):
    """Kiểm tra xem module có sẵn không (an toàn hơn __import__)."""
    return importlib.util.find_spec(module_name) is not None

def get_installed_version(package_name):
    """Lấy version đã cài đặt của package (nếu có)."""
    try:
        return pkg_resources.get_distribution(package_name).version
    except Exception:
        return None

def version_satisfies(installed, required):
    """So sánh version đã cài với version yêu cầu (>=)."""
    from pkg_resources import parse_version
    return parse_version(installed) >= parse_version(required)

def ask_user_terminal(msg, yes_no=True):
    """Hỏi người dùng qua terminal."""
    print(msg)
    if yes_no:
        while True:
            ans = input("Bạn có muốn chương trình tự động cài đặt các thư viện này không? (y/n): ").strip().lower()
            if ans in ("y", "yes"):
                return True
            elif ans in ("n", "no"):
                return False
    else:
        input("Nhấn Enter để tiếp tục...")
        return None

def check_and_install_dependencies():
    """
    Kiểm tra các thư viện bắt buộc. Nếu thiếu hoặc sai version, hỏi người dùng có muốn cài đặt không.
    Trả về True nếu đầy đủ, False nếu còn thiếu hoặc lỗi.
    """
    print("--- Kiểm tra các thư viện phụ thuộc ---")
    # module_name: (pip_name, min_version hoặc None)
    required_libs = {
        "chardet": ("chardet", None),
        "pandas": ("pandas", None),
        "openpyxl": ("openpyxl", None),
        "flashtext": ("flashtext", None),
        "PIL": ("pillow", None),
        "tqdm": ("tqdm", None),
        "numpy": ("numpy", None),
        "PyQt6": ("PyQt6", None),
    }

    missing_libs = []
    wrong_version_libs = []

    for module_name, (pip_name, min_version) in required_libs.items():
        if is_module_available(module_name):
            if min_version:
                installed_version = get_installed_version(pip_name)
                if installed_version and not version_satisfies(installed_version, min_version):
                    print(f" [!] {pip_name} version {installed_version} < yêu cầu {min_version}")
                    wrong_version_libs.append((pip_name, min_version))
                else:
                    print(f" [OK] Đã tìm thấy: {pip_name}")
            else:
                print(f" [OK] Đã tìm thấy: {pip_name}")
        else:
            print(f" [!] Thiếu thư viện: {pip_name}")
            missing_libs.append(pip_name)

    all_missing = missing_libs + [f"{name}>={ver}" for name, ver in wrong_version_libs]

    if not all_missing:
        print("--- Tất cả thư viện bắt buộc đã được cài đặt và đúng version. ---")
        return True

    msg = (
        f"Một số thư viện bắt buộc chưa được cài đặt hoặc chưa đúng version:\n\n"
        f"{', '.join(all_missing)}\n\n"
        f"Bạn có muốn chương trình tự động cài đặt/cập nhật các thư viện này không?\n"
        f"(Yêu cầu kết nối Internet và có thể mất vài phút)"
    )

    user_agree = ask_user_terminal(msg)

    if not user_agree:
        print("Bạn đã từ chối cài đặt tự động. Vui lòng tự cài đặt các thư viện còn thiếu.")
        return False

    print("\n--- Bắt đầu quá trình cài đặt/cập nhật tự động ---")
    try:
        from tqdm import tqdm
        iterator = tqdm(all_missing, desc="Cài đặt")
    except ImportError:
        iterator = all_missing

    failed_libs = []
    for package in iterator:
        print(f"\n--- Đang cài đặt/cập nhật {package} ---")
        if not install(package):
            failed_libs.append(package)

    if failed_libs:
        msg_error = (
            f"Không thể tự động cài đặt/cập nhật các thư viện sau:\n\n"
            f"{', '.join(failed_libs)}\n\n"
            f"Vui lòng mở Command Prompt hoặc Terminal và chạy lệnh sau:\n\n"
            f"pip install {' '.join(failed_libs)}"
        )
        ask_user_terminal(msg_error, yes_no=False)
        return False
    else:
        msg_done = "Đã cài đặt/cập nhật thành công các thư viện. Vui lòng khởi động lại chương trình."
        ask_user_terminal(msg_done, yes_no=False)
        return True

if __name__ == "__main__":
    check_and_install_dependencies()