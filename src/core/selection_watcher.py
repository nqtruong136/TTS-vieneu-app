"""
Selection Watcher service.
Monitors mouse drag and release events across any Windows application (pynput).
When text is highlighted, triggers the capture of selected text and requests
display of the floating toolbar (Lark / PopClip style).
"""
import ctypes
import threading
import time
from typing import Callable, Optional
from pynput import mouse
import pyperclip

from .logger import AppLogger

user32 = ctypes.windll.user32

KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_C = 0x43


class SelectionWatcher:
    """
    Theo dõi thao tác kéo thả chuột (Mouse Drag & Release) trên toàn hệ điều hành Windows.
    Khi phát hiện người dùng tô đen văn bản, tự động sao chép nhanh và gửi tọa độ
    để hiển thị thanh công cụ nổi (Floating Toolbar) kiểu Lark.
    """
    def __init__(
        self,
        on_selection: Optional[Callable[[str, int, int], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
        is_point_inside_toolbar: Optional[Callable[[int, int], bool]] = None,
    ):
        self.on_selection = on_selection
        self.on_dismiss = on_dismiss
        self.is_point_inside_toolbar = is_point_inside_toolbar

        self._is_active = False
        self._running = False
        self._listener: Optional[mouse.Listener] = None

        self._down_pos = (0, 0)
        self._down_time = 0.0
        self._last_up_time = 0.0
        self._last_up_pos = (0, 0)
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        return self._is_active

    def set_active(self, active: bool):
        with self._lock:
            self._is_active = active
            if active:
                AppLogger.info("Đã BẬT chế độ hiển thị thanh nổi khi tô đen văn bản (Lark style).", source="SelectionWatcher")
            else:
                AppLogger.info("Đã TẮT chế độ hiển thị thanh nổi khi tô đen.", source="SelectionWatcher")
                if self.on_dismiss:
                    self.on_dismiss()

    def start(self):
        """Khởi động luồng hook chuột ngầm."""
        if self._running:
            return
        self._running = True
        self._listener = mouse.Listener(on_click=self._on_click)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        """Dừng hoàn toàn lắng nghe sự kiện chuột."""
        self._running = False
        self._is_active = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _on_click(self, x, y, button, pressed):
        if button != mouse.Button.left:
            return

        if pressed:
            self._down_pos = (x, y)
            self._down_time = time.time()

            # Nếu người dùng bấm chuột bên ngoài thanh nổi, ẩn thanh nổi đi
            if self.is_point_inside_toolbar and not self.is_point_inside_toolbar(x, y):
                if self.on_dismiss:
                    self.on_dismiss()
        else:
            if not self._is_active:
                return

            # Nếu nhả chuột bên trong thanh nổi, bỏ qua vì đang thao tác trên nút bấm của thanh nổi
            if self.is_point_inside_toolbar and self.is_point_inside_toolbar(x, y):
                return

            now = time.time()
            dx = abs(x - self._down_pos[0])
            dy = abs(y - self._down_pos[1])
            dist = (dx * dx + dy * dy) ** 0.5

            is_drag = dist >= 10
            is_double_click = (
                not is_drag
                and (now - self._last_up_time < 0.35)
                and (abs(x - self._last_up_pos[0]) < 8 and abs(y - self._last_up_pos[1]) < 8)
            )

            self._last_up_time = now
            self._last_up_pos = (x, y)

            if is_drag or is_double_click:
                # Đẩy sang luồng worker xử lý để đảm bảo không làm khựng chuyển động chuột của hệ thống
                threading.Thread(
                    target=self._capture_selection_worker,
                    args=(x, y),
                    daemon=True,
                    name="SelectionCaptureWorker"
                ).start()

    def _capture_selection_worker(self, screen_x: int, screen_y: int):
        # Đợi ứng dụng bên ngoài cập nhật highlight xong (40ms)
        time.sleep(0.04)

        old_clipboard = ""
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

        try:
            pyperclip.copy("")
        except Exception:
            pass

        # Giả lập tổ hợp phím Ctrl + C để lấy văn bản được bôi đen
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_C, 0, 0, 0)
        time.sleep(0.01)
        user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

        selected_text = ""
        for _ in range(12):
            time.sleep(0.015)
            try:
                val = pyperclip.paste()
                if val:
                    selected_text = val.strip()
                    break
            except Exception:
                pass

        # Khôi phục nội dung khay nhớ tạm ban đầu để thao tác bôi đen không làm ô nhiễm Clipboard của người dùng
        if old_clipboard:
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass

        if selected_text and len(selected_text) >= 2:
            AppLogger.info(
                f"Phát hiện văn bản tô đen ({len(selected_text)} ký tự): '{selected_text[:30]}...'",
                source="SelectionWatcher"
            )
            if self.on_selection:
                self.on_selection(selected_text, screen_x, screen_y)
