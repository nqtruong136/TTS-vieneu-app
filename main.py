"""
Entrypoint for VieNeu-TTS Studio Desktop Application.
Supports both silent GUI launch (pythonw.exe) and diagnostic console launch (python.exe).
"""
import sys
import os
import io
import time

# 1. Tắt hoàn toàn progress bar của Hugging Face và tqdm trên terminal
# để tránh lỗi 'NoneType' object has no attribute 'write' khi chạy bằng pythonw.exe
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

# 2. Đảm bảo thư mục dự án nằm trong sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 3. Chuẩn hóa luồng xuất nhập chuẩn (stdout / stderr) ngay lập tức
# Khi chạy qua pythonw.exe, sys.stdout và sys.stderr mặc định là None.
# Ta mở một file stream thật (TextIOWrapper) để các thư viện như tqdm, huggingface, sounddevice
# không bao giờ bị lỗi 'NoneType' has no attribute 'write' hay 'flush'.
LOG_FILE_PATH = os.path.join(BASE_DIR, "app_output.log")

try:
    _log_stream = open(LOG_FILE_PATH, "a", encoding="utf-8", buffering=1)
except Exception:
    _log_stream = io.StringIO()

if sys.stdout is None:
    sys.stdout = _log_stream
elif hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = _log_stream
elif hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if getattr(sys, "__stdout__", None) is None:
    sys.__stdout__ = sys.stdout
if getattr(sys, "__stderr__", None) is None:
    sys.__stderr__ = sys.stderr


def run_app():
    """Khởi chạy ứng dụng với bộ giám sát và bắt lỗi toàn diện."""
    try:
        from src.ui.app_window import AppWindow
        app = AppWindow()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as exc:
        import traceback
        crash_report = traceback.format_exc()
        crash_path = os.path.join(BASE_DIR, "startup_crash.log")
        try:
            with open(crash_path, "w", encoding="utf-8") as f:
                f.write(f"VIE-NEU TTS STUDIO - BÁO CÁO LỖI KHỞI ĐỘNG\n")
                f.write(f"Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                f.write(crash_report)
        except Exception:
            pass

        # Hiển thị popup lỗi trực quan trên Windows nếu chạy qua pythonw
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "VieNeu-TTS Studio - Lỗi Khởi Động",
                f"Không thể khởi động ứng dụng:\n\n{exc}\n\n"
                f"Chi tiết kỹ thuật đã được ghi lại tại:\n{crash_path}\n\n"
                f"Bạn có thể mở tệp 'run_debug.bat' để xem chi tiết log chẩn đoán."
            )
            root.destroy()
        except Exception:
            pass

        sys.exit(1)
    finally:
        # Đảm bảo dọn dẹp sạch tiến trình, không để lại zombie process
        os._exit(0)


if __name__ == "__main__":
    run_app()
