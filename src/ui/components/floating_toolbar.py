"""
Floating Toolbar component (Lark / PopClip Style).
A borderless, sleek horizontal pill that appears near text selection on Windows.
Allows the user to trigger Realtime Speech Synthesis, Stop, or Copy in 1 click.
"""
from typing import Callable, Optional
import customtkinter as ctk

from ..styles import COLORS, FONTS


class FloatingToolbar(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        on_read_click: Optional[Callable[[str], None]] = None,
        on_stop_click: Optional[Callable[[], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self.on_read_click = on_read_click
        self.on_stop_click = on_stop_click
        self.on_dismiss = on_dismiss

        # Cấu hình cửa sổ không viền, luôn nổi lên trên cùng (Topmost)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#181B22")
        self.withdraw()  # Ẩn ban đầu

        self._width = 440
        self._height = 44
        self._current_x = 0
        self._current_y = 0
        self._is_visible = False
        self._current_text = ""
        self._is_reading = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        self._create_widgets()

    def _create_widgets(self):
        # Khung viền dạng Pill bo tròn 20px hiện đại kiểu Lark / macOS
        self.main_pill = ctk.CTkFrame(
            self,
            corner_radius=20,
            fg_color="#181B22",
            border_width=1,
            border_color="#374151"
        )
        self.main_pill.pack(fill="both", expand=True, padx=1, pady=1)

        # 1. Logo & Badge số ký tự (Có thể kéo thả để di chuyển thanh)
        self.left_box = ctk.CTkFrame(self.main_pill, fg_color="transparent")
        self.left_box.pack(side="left", padx=(12, 4))

        self.logo_label = ctk.CTkLabel(
            self.left_box,
            text="🦜",
            font=("Segoe UI Emoji", 14)
        )
        self.logo_label.pack(side="left", padx=(0, 4))

        self.char_badge = ctk.CTkLabel(
            self.left_box,
            text="0 ký tự",
            font=("Segoe UI", 10),
            text_color="#9CA3AF"
        )
        self.char_badge.pack(side="left")

        # Cho phép nhấn giữ logo hoặc badge để kéo thanh nổi nếu cần
        for widget in (self.left_box, self.logo_label, self.char_badge):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

        # Đường phân cách đứng
        sep = ctk.CTkFrame(self.main_pill, width=1, height=20, fg_color="#374151")
        sep.pack(side="left", padx=6)

        # 2. Nút "Đọc ngay" (Nổi bật nhất)
        self.btn_read = ctk.CTkButton(
            self.main_pill,
            text="🔊 Đọc ngay",
            width=90,
            height=28,
            corner_radius=14,
            font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._handle_read_click
        )
        self.btn_read.pack(side="left", padx=3)

        # 3. Nút "Dừng" (Hiển thị khi đang phát)
        self.btn_stop = ctk.CTkButton(
            self.main_pill,
            text="⏹ Dừng",
            width=68,
            height=28,
            corner_radius=14,
            font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=self._handle_stop_click
        )
        # Ẩn nút Dừng khi chưa phát
        self.btn_stop.pack(side="left", padx=3)
        self.btn_stop.pack_forget()

        # 4. Nút "Sao chép"
        self.btn_copy = ctk.CTkButton(
            self.main_pill,
            text="📋 Chép",
            width=68,
            height=28,
            corner_radius=14,
            font=("Segoe UI", 11),
            fg_color="transparent",
            hover_color="#2D3340",
            text_color="#E5E7EB",
            command=self._handle_copy_click
        )
        self.btn_copy.pack(side="left", padx=3)

        # 5. Badge hiển thị giọng đọc hiện tại
        self.voice_badge = ctk.CTkLabel(
            self.main_pill,
            text="🎙 Minh Quân",
            font=("Segoe UI", 10),
            text_color="#60A5FA"
        )
        self.voice_badge.pack(side="left", padx=(4, 6))

        # 6. Nút Đóng (✕)
        self.btn_close = ctk.CTkButton(
            self.main_pill,
            text="✕",
            width=26,
            height=26,
            corner_radius=13,
            font=("Segoe UI", 11, "bold"),
            fg_color="transparent",
            hover_color="#DC2626",
            text_color="#9CA3AF",
            command=self.hide
        )
        self.btn_close.pack(side="right", padx=(2, 8))

    def show_at(self, screen_x: int, screen_y: int, text: str, voice_name: Optional[str] = None):
        """Hiển thị thanh nổi ngay tại vị trí con trỏ chuột vừa bôi đen xong."""
        self._current_text = text.strip()
        count = len(self._current_text)
        self.char_badge.configure(text=f"{count} ký tự")

        if voice_name:
            self.voice_badge.configure(text=f"🎙 {voice_name}")

        self.set_reading_state(False)

        # Tính toán tọa độ hiển thị đảm bảo nằm trọn trong màn hình
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        target_x = max(10, min(sw - self._width - 10, screen_x - (self._width // 2)))
        target_y = screen_y + 16

        # Nếu gần mép dưới màn hình thì đẩy thanh nổi lên phía trên con trỏ chuột
        if target_y + self._height > sh - 15:
            target_y = max(10, screen_y - self._height - 16)

        self._current_x = target_x
        self._current_y = target_y

        self.geometry(f"{self._width}x{self._height}+{target_x}+{target_y}")
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self._is_visible = True

    def hide(self):
        """Ẩn thanh nổi."""
        if self._is_visible:
            self._is_visible = False
            self.withdraw()
            if self.on_dismiss:
                self.on_dismiss()

    def _start_drag(self, event):
        self._drag_start_x = event.x_root - self._current_x
        self._drag_start_y = event.y_root - self._current_y

    def _on_drag(self, event):
        self._current_x = event.x_root - self._drag_start_x
        self._current_y = event.y_root - self._drag_start_y
        self.geometry(f"{self._width}x{self._height}+{self._current_x}+{self._current_y}")

    def is_point_inside(self, px: int, py: int) -> bool:
        """Kiểm tra xem tọa độ chuột (px, py) có nằm trong vùng thanh nổi hay không."""
        if not self._is_visible:
            return False
        # Đệm thêm 6px biên an toàn xung quanh thanh nổi
        return (
            (self._current_x - 6) <= px <= (self._current_x + self._width + 6)
            and (self._current_y - 6) <= py <= (self._current_y + self._height + 6)
        )

    def set_reading_state(self, is_reading: bool):
        """Cập nhật giao diện thanh nổi khi đang phát âm thanh."""
        self._is_reading = is_reading
        if is_reading:
            self.btn_read.configure(
                text="⚡ Đang đọc...",
                fg_color="#10B981",
                hover_color="#059669"
            )
            self.btn_stop.pack(side="left", padx=3, before=self.btn_copy)
        else:
            self.btn_read.configure(
                text="🔊 Đọc ngay",
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"]
            )
            self.btn_stop.pack_forget()

    def _handle_read_click(self):
        if self._is_reading:
            return
        if self.on_read_click and self._current_text:
            self.set_reading_state(True)
            self.on_read_click(self._current_text)

    def _handle_stop_click(self):
        self.set_reading_state(False)
        if self.on_stop_click:
            self.on_stop_click()

    def _handle_copy_click(self):
        if self._current_text:
            import pyperclip
            pyperclip.copy(self._current_text)
            orig_text = self.btn_copy.cget("text")
            self.btn_copy.configure(text="✓ Đã chép", text_color="#10B981")
            self.after(1200, lambda: self.btn_copy.configure(text=orig_text, text_color="#E5E7EB"))
