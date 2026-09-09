"""
Log Console component for CustomTkinter GUI.
Displays real-time logs, exceptions, tracebacks, and filters with Copy & Clear functionality.
"""
from typing import Optional
import customtkinter as ctk

from ...core.logger import AppLogger, LogEntry
from ..styles import COLORS, FONTS
from ..dispatcher import UIDispatcher


class LogConsole(ctk.CTkFrame):
    def __init__(
        self,
        master,
        height: int = 220,
        **kwargs
    ):
        super().__init__(master, corner_radius=8, border_width=1, border_color=COLORS["border_dark"], fg_color=COLORS["card_bg_dark"], **kwargs)

        self._filter_level = "ALL"
        self._auto_scroll = True

        self._create_widgets()

        # Đăng ký nhận log thời gian thực từ AppLogger
        AppLogger.subscribe(self._on_new_log)

        # Nạp lịch sử log ban đầu
        self._load_initial_history()

    def _create_widgets(self):
        # 1. Header Toolbar
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            header_frame,
            text="📜 NHẬT KÝ HỆ THỐNG & DEBUG LOGS",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["primary"]
        ).pack(side="left")

        # Nút Xóa log
        btn_clear = ctk.CTkButton(
            header_frame,
            text="🗑 Xóa",
            width=54,
            height=24,
            font=FONTS["caption"],
            fg_color="transparent",
            text_color=COLORS["danger"],
            border_width=1,
            border_color=COLORS["danger"],
            hover_color=COLORS["card_bg_dark"],
            command=self._clear_logs
        )
        btn_clear.pack(side="right", padx=(4, 0))

        # Nút Sao chép log
        btn_copy = ctk.CTkButton(
            header_frame,
            text="📋 Sao chép",
            width=76,
            height=24,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._copy_logs
        )
        btn_copy.pack(side="right", padx=(4, 0))

        # Filter Level
        self.filter_menu = ctk.CTkOptionMenu(
            header_frame,
            values=["Tất cả log", "INFO", "SUCCESS", "WARNING", "ERROR"],
            width=100,
            height=24,
            font=FONTS["caption"],
            command=self._on_filter_change
        )
        self.filter_menu.set("Tất cả log")
        self.filter_menu.pack(side="right", padx=(4, 0))

        # 2. Log Textbox (Monospaced font)
        self.textbox = ctk.CTkTextbox(
            self,
            font=("Consolas", 11),
            wrap="none",
            corner_radius=6,
            border_width=0,
            fg_color="#111827"  # Slate dark background
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _load_initial_history(self):
        history = AppLogger.get_history()
        for entry in history:
            self._append_entry(entry)

    def _on_new_log(self, entry: LogEntry):
        UIDispatcher.post(self._append_entry, entry)

    def _append_entry(self, entry: LogEntry):
        if self._filter_level != "ALL" and entry.level != self._filter_level:
            return

        line = entry.format_line() + "\n"
        self.textbox.insert("end", line)

        if self._auto_scroll:
            self.textbox.see("end")

    def _on_filter_change(self, val: str):
        if val == "Tất cả log":
            self._filter_level = "ALL"
        else:
            self._filter_level = val

        # Vẽ lại toàn bộ log theo filter mới
        self.textbox.delete("1.0", "end")
        self._load_initial_history()

    def _clear_logs(self):
        AppLogger.clear()
        self.textbox.delete("1.0", "end")

    def _copy_logs(self):
        content = self.textbox.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)

