"""
Clipboard Watcher service.
Continuously monitors Windows Clipboard in a background daemon thread.
When active, detects new copied text (Ctrl+C) and triggers the realtime speech pipeline.
"""
import threading
import time
from typing import Callable, Optional
import pyperclip

from .logger import AppLogger


class ClipboardWatcher:
    def __init__(
        self,
        on_new_text: Optional[Callable[[str], None]] = None,
        poll_interval_sec: float = 0.35,
    ):
        self.on_new_text = on_new_text
        self.poll_interval_sec = poll_interval_sec

        self._is_active = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_text = ""
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        return self._is_active

    def set_active(self, active: bool):
        """Bật/tắt chế độ tự động lắng nghe clipboard."""
        with self._lock:
            self._is_active = active
            if active:
                # Ghi nhận nội dung clipboard hiện tại để KHÔNG bị đọc nhầm đoạn cũ
                try:
                    self._last_text = pyperclip.paste().strip()
                except Exception:
                    self._last_text = ""
                AppLogger.info("Đã BẬT chế độ tự động đọc khi Copy (Clipboard Trigger).", source="ClipboardWatcher")
            else:
                AppLogger.info("Đã TẮT chế độ tự động đọc Clipboard.", source="ClipboardWatcher")

    def start(self):
        """Khởi động luồng giám sát khay nhớ tạm."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="ClipboardWatcherWorker"
        )
        self._thread.start()

    def stop(self):
        """Dừng hoàn toàn luồng giám sát."""
        self._running = False
        self._is_active = False

    def _worker(self):
        while self._running:
            try:
                if self._is_active:
                    current = pyperclip.paste()
                    if current:
                        clean = current.strip()
                        # Chỉ kích hoạt nếu nội dung mới khác nội dung cũ và có ít nhất 2 ký tự
                        if len(clean) >= 2 and clean != self._last_text:
                            self._last_text = clean
                            AppLogger.info(f"Phát hiện văn bản mới từ Clipboard ({len(clean)} ký tự)", source="ClipboardWatcher")
                            if self.on_new_text:
                                try:
                                    self.on_new_text(clean)
                                except Exception as e:
                                    AppLogger.exception(f"Lỗi khi xử lý callback văn bản clipboard: {e}", exc=e, source="ClipboardWatcher")
            except Exception:
                # Bỏ qua các lỗi tạm thời khi Clipboard đang bị ứng dụng khác khóa (như Excel, Word)
                pass

            time.sleep(self.poll_interval_sec)

