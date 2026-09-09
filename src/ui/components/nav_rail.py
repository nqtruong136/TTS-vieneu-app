"""
Left Primary Navigation Rail for switching between main app sections:
- Giọng có sẵn (Preset Voices)
- Clone Voice (Voice Cloning)
- Các giọng đã tạo (Generated Voice Library with Pagination & YouTube Scrubber)
- Cài đặt hệ thống (Settings, Hardware, Benchmark, Model Cache)
"""
from typing import Callable, Optional, Dict
import customtkinter as ctk

from ..styles import COLORS, FONTS


class NavRail(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_nav_change: Optional[Callable[[str], None]] = None,
        on_open_log: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, width=195, corner_radius=0, **kwargs)
        self.grid_propagate(False)

        self.on_nav_change = on_nav_change
        self.on_open_log = on_open_log
        self.current_view = "preset"
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}

        self._create_widgets()

    def _create_widgets(self):
        # 1. Brand Logo & Title
        brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        brand_frame.pack(fill="x", padx=14, pady=(18, 16))

        logo_label = ctk.CTkLabel(
            brand_frame,
            text="🦜 VieNeu-TTS",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS["primary"]
        )
        logo_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            brand_frame,
            text="Studio • v3 Turbo",
            font=FONTS["caption"],
            text_color="gray"
        )
        sub_label.pack(anchor="w")

        separator = ctk.CTkFrame(self, height=1, fg_color=COLORS["border_dark"])
        separator.pack(fill="x", padx=12, pady=(0, 12))

        # 2. Nav Menu Section
        menu_items = [
            ("preset", "🎙️  Giọng có sẵn", "Dùng 23 giọng đọc dựng sẵn"),
            ("clone", "🧬  Clone Voice", "Nhân bản giọng nói mẫu 3–8s"),
            ("realtime", "⚡  Đọc Realtime", "Tự động đọc khi Copy Clipboard"),
            ("history", "🎵  Các giọng đã tạo", "Thư viện bản thu & Phân trang"),
            ("settings", "⚙️  Cài đặt & Máy", "Hardware, CPU/GPU, Benchmark"),
        ]

        for key, text, desc in menu_items:
            btn = ctk.CTkButton(
                self,
                text=text,
                height=42,
                corner_radius=8,
                font=("Segoe UI", 12, "bold"),
                anchor="w",
                fg_color=COLORS["primary"] if key == self.current_view else "transparent",
                hover_color=COLORS["primary_hover"] if key == self.current_view else COLORS["card_bg_dark"],
                text_color="white" if key == self.current_view else "#D1D5DB",
                command=lambda k=key: self._handle_click(k)
            )
            btn.pack(fill="x", padx=10, pady=4)
            self._nav_buttons[key] = btn

        # 3. Bottom status badge, log button & theme switch
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=12, pady=16)

        # Nút xem nhật ký Log Console
        self.btn_open_log = ctk.CTkButton(
            bottom_frame,
            text="📜 Xem Log Console",
            height=28,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            hover_color=COLORS["card_bg_dark"],
            command=self._handle_open_log
        )
        self.btn_open_log.pack(fill="x", pady=(0, 8))

        # Status badge indicator
        self.status_badge = ctk.CTkLabel(
            bottom_frame,
            text="● Engine: Sẵn sàng",
            font=("Segoe UI", 10),
            text_color=COLORS["secondary"],
            anchor="w"
        )
        self.status_badge.pack(fill="x", pady=(0, 8))

        # Theme toggle
        theme_row = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        theme_row.pack(fill="x")

        ctk.CTkLabel(theme_row, text="🌓 Giao diện:", font=FONTS["caption"], text_color="gray").pack(side="left")
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row,
            values=["Dark", "Light", "System"],
            width=80,
            height=24,
            font=("Segoe UI", 10),
            command=self._change_appearance_mode
        )
        self.theme_menu.set("Dark")
        self.theme_menu.pack(side="right")

    def _handle_click(self, key: str):
        if key == self.current_view:
            return

        # Update button colors
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(
                    fg_color=COLORS["primary"],
                    hover_color=COLORS["primary_hover"],
                    text_color="white"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=COLORS["card_bg_dark"],
                    text_color="#D1D5DB"
                )

        self.current_view = key
        if self.on_nav_change:
            self.on_nav_change(key)

    def set_engine_status(self, is_ready: bool, is_loading: bool, error: Optional[str] = None):
        if error:
            self.status_badge.configure(text="● Engine: Lỗi", text_color=COLORS["danger"])
        elif is_loading:
            self.status_badge.configure(text="● Engine: Đang tải...", text_color="#F59E0B")
        elif is_ready:
            self.status_badge.configure(text="● Engine: Sẵn sàng", text_color=COLORS["secondary"])
        else:
            self.status_badge.configure(text="● Engine: Chưa nạp", text_color="gray")

    def _handle_open_log(self):
        if self.on_open_log:
            self.on_open_log()

    def _change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode)
