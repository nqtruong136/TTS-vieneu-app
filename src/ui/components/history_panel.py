"""
History Panel component for CustomTkinter GUI.
Displays previous generations from SQLite database, allows quick re-play, loading text, or deletion.
"""
import os
import subprocess
from typing import Callable, Optional
import customtkinter as ctk

from ...database.history_manager import HistoryManager, HistoryRecord
from ...config import OUTPUTS_DIR
from ..styles import COLORS, FONTS


class HistoryPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        history_manager: HistoryManager,
        on_play_request: Optional[Callable[[str], None]] = None,
        on_load_text_request: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, width=320, corner_radius=8, **kwargs)
        self.grid_propagate(False)

        self.history_manager = history_manager
        self.on_play_request = on_play_request
        self.on_load_text_request = on_load_text_request

        self._create_widgets()
        self.refresh_list()

    def _create_widgets(self):
        # 1. Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(12, 6))

        title_label = ctk.CTkLabel(
            header_frame,
            text="📋 LỊCH SỬ BẢN THU",
            font=FONTS["header"]
        )
        title_label.pack(side="left")

        # Quick action buttons
        btn_open_folder = ctk.CTkButton(
            header_frame,
            text="📁",
            width=28,
            height=26,
            font=FONTS["body"],
            fg_color="transparent",
            hover_color=COLORS["card_bg_dark"],
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._open_output_folder
        )
        btn_open_folder.pack(side="right", padx=(4, 0))

        btn_clear_all = ctk.CTkButton(
            header_frame,
            text="🗑",
            width=28,
            height=26,
            font=FONTS["body"],
            fg_color="transparent",
            hover_color=COLORS["danger"],
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._clear_all_records
        )
        btn_clear_all.pack(side="right")

        separator = ctk.CTkFrame(self, height=1, fg_color=COLORS["border_dark"])
        separator.pack(fill="x", padx=12, pady=4)

        # 2. Scrollable list of history cards
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        # Empty state label
        self.empty_label = ctk.CTkLabel(
            self.scroll_frame,
            text="Chưa có bản thu nào.\nHãy tạo giọng nói để lưu vào đây!",
            font=FONTS["caption"],
            text_color="gray",
            justify="center"
        )

    def refresh_list(self):
        # Xóa các widget cũ trong scroll frame
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        records = self.history_manager.get_records(limit=30)
        if not records:
            self.empty_label = ctk.CTkLabel(
                self.scroll_frame,
                text="Chưa có bản thu nào.\nHãy tạo giọng nói để lưu vào đây!",
                font=FONTS["caption"],
                text_color="gray",
                justify="center"
            )
            self.empty_label.pack(pady=40)
            return

        for record in records:
            self._create_card(record)

    def _create_card(self, record: HistoryRecord):
        card = ctk.CTkFrame(
            self.scroll_frame,
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        card.pack(fill="x", padx=6, pady=4)

        # Top row: Voice badge & Timestamp
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=8, pady=(6, 2))

        voice_badge = ctk.CTkLabel(
            top_row,
            text=f"🎙 {record.voice_name}",
            font=("Segoe UI", 10, "bold"),
            text_color=COLORS["primary"]
        )
        voice_badge.pack(side="left")

        time_label = ctk.CTkLabel(
            top_row,
            text=record.timestamp,
            font=("Segoe UI", 9),
            text_color="gray"
        )
        time_label.pack(side="right")

        # Middle row: Text preview snippet
        clean_text = record.text.replace("\n", " ")
        snippet = clean_text[:80] + ("..." if len(clean_text) > 80 else "")
        text_label = ctk.CTkLabel(
            card,
            text=f'"{snippet}"',
            font=FONTS["caption"],
            wraplength=270,
            justify="left"
        )
        text_label.pack(anchor="w", padx=8, pady=2)

        # Bottom row: Stats & Action buttons
        bottom_row = ctk.CTkFrame(card, fg_color="transparent")
        bottom_row.pack(fill="x", padx=8, pady=(2, 6))

        stats_text = f"⏱ {record.duration:.1f}s • RTF {record.rtf:.2f}"
        stats_label = ctk.CTkLabel(
            bottom_row,
            text=stats_text,
            font=("Segoe UI", 9),
            text_color="gray"
        )
        stats_label.pack(side="left")

        # Delete button
        btn_del = ctk.CTkButton(
            bottom_row,
            text="✕",
            width=22,
            height=22,
            font=("Segoe UI", 10),
            fg_color="transparent",
            text_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=lambda r_id=record.id: self._delete_record(r_id)
        )
        btn_del.pack(side="right", padx=(2, 0))

        # Load text button
        btn_load = ctk.CTkButton(
            bottom_row,
            text="📋 Nạp",
            width=46,
            height=22,
            font=("Segoe UI", 10),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda t=record.text: self._load_text(t)
        )
        btn_load.pack(side="right", padx=(2, 2))

        # Play button
        btn_play = ctk.CTkButton(
            bottom_row,
            text="▶ Nghe",
            width=54,
            height=22,
            font=("Segoe UI", 10, "bold"),
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=lambda p=record.audio_path: self._play_audio(p)
        )
        btn_play.pack(side="right", padx=(0, 2))

    def _play_audio(self, audio_path: str):
        if self.on_play_request:
            self.on_play_request(audio_path)

    def _load_text(self, text: str):
        if self.on_load_text_request:
            self.on_load_text_request(text)

    def _delete_record(self, record_id: int):
        self.history_manager.delete_record(record_id)
        self.refresh_list()

    def _clear_all_records(self):
        self.history_manager.clear_all()
        self.refresh_list()

    def _open_output_folder(self):
        subprocess.Popen(f'explorer "{os.path.abspath(OUTPUTS_DIR)}"')

