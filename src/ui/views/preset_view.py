"""
Preset Voices View (Tab 1: Giọng có sẵn).
Allows users to choose from 23 curated Vietnamese voices and generate natural speech.
"""
from typing import Callable, Optional
import customtkinter as ctk

from ...config import PRESET_VOICES, DEFAULT_VOICE
from ..styles import COLORS, FONTS
from ..components.editor_panel import EditorPanel
from ..components.player_bar import PlayerBar
from ...core.audio_player import AudioPlayer
from ...core.progress import ProgressTracker


class PresetView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        audio_player: AudioPlayer,
        on_generate_request: Optional[Callable[[str, str], None]] = None,
        progress_tracker: Optional[ProgressTracker] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.audio_player = audio_player
        self.on_generate_request = on_generate_request
        self.progress_tracker = progress_tracker
        self.selected_voice = DEFAULT_VOICE

        self._voices_dict = {v["name"]: v for v in PRESET_VOICES}
        self._all_voice_names = [v["name"] for v in PRESET_VOICES]

        self._create_widgets()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=0, minsize=260)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Left Sub-Sidebar: Voice Selection & Info
        sidebar_frame = ctk.CTkFrame(
            self,
            width=260,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        sidebar_frame.grid_propagate(False)

        ctk.CTkLabel(
            sidebar_frame,
            text="🎙️ DANH SÁCH GIỌNG ĐỌC",
            font=FONTS["header"]
        ).pack(anchor="w", padx=14, pady=(14, 6))

        # Filter buttons row: Tất cả | Nam | Nữ
        filter_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        filter_frame.pack(fill="x", padx=14, pady=(0, 8))

        self.btn_all = ctk.CTkButton(
            filter_frame,
            text="Tất cả",
            width=60,
            height=24,
            font=FONTS["caption"],
            fg_color=COLORS["primary"],
            command=lambda: self._filter_voices("all")
        )
        self.btn_all.pack(side="left", padx=(0, 4))

        self.btn_male = ctk.CTkButton(
            filter_frame,
            text="Nam",
            width=50,
            height=24,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda: self._filter_voices("Nam")
        )
        self.btn_male.pack(side="left", padx=(0, 4))

        self.btn_female = ctk.CTkButton(
            filter_frame,
            text="Nữ",
            width=50,
            height=24,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda: self._filter_voices("Nữ")
        )
        self.btn_female.pack(side="left")

        # OptionMenu to pick voice
        self.voice_menu = ctk.CTkOptionMenu(
            sidebar_frame,
            values=self._all_voice_names,
            height=34,
            command=self._on_voice_select
        )
        self.voice_menu.set(DEFAULT_VOICE)
        self.voice_menu.pack(fill="x", padx=14, pady=(0, 12))

        # Voice Detail Card
        self.detail_card = ctk.CTkFrame(
            sidebar_frame,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color="transparent"
        )
        self.detail_card.pack(fill="x", padx=14, pady=4)

        self.voice_name_label = ctk.CTkLabel(
            self.detail_card,
            text=f"👤 {DEFAULT_VOICE}",
            font=("Segoe UI", 13, "bold"),
            text_color=COLORS["primary"]
        )
        self.voice_name_label.pack(anchor="w", padx=10, pady=(8, 2))

        self.voice_tags_label = ctk.CTkLabel(
            self.detail_card,
            text="Nam • Bắc • Tự nhiên",
            font=FONTS["caption"],
            text_color=COLORS["secondary"]
        )
        self.voice_tags_label.pack(anchor="w", padx=10, pady=2)

        self.voice_desc_label = ctk.CTkLabel(
            self.detail_card,
            text="Giọng đọc nam miền Bắc truyền cảm, tự nhiên, mượt mà chuẩn phát thanh viên.",
            font=FONTS["caption"],
            text_color="gray",
            wraplength=210,
            justify="left"
        )
        self.voice_desc_label.pack(anchor="w", padx=10, pady=(2, 10))

        # 2. Right / Center Container: EditorPanel + PlayerBar
        center_frame = ctk.CTkFrame(self, fg_color="transparent")
        center_frame.grid(row=0, column=1, sticky="nsew")
        center_frame.grid_rowconfigure(0, weight=1)
        center_frame.grid_rowconfigure(1, weight=0)
        center_frame.grid_columnconfigure(0, weight=1)

        self.editor_panel = EditorPanel(
            center_frame,
            on_generate=self._handle_generate_click,
            progress_tracker=self.progress_tracker
        )
        self.editor_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        self.player_bar = PlayerBar(
            center_frame,
            audio_player=self.audio_player
        )
        self.player_bar.grid(row=1, column=0, sticky="ew")

        # Cập nhật chi tiết ban đầu
        self._on_voice_select(DEFAULT_VOICE)

    def _filter_voices(self, filter_type: str):
        self.btn_all.configure(fg_color=COLORS["primary"] if filter_type == "all" else "transparent")
        self.btn_male.configure(fg_color=COLORS["primary"] if filter_type == "Nam" else "transparent")
        self.btn_female.configure(fg_color=COLORS["primary"] if filter_type == "Nữ" else "transparent")

        if filter_type == "all":
            filtered = self._all_voice_names
        else:
            filtered = [v["name"] for v in PRESET_VOICES if v["gender"] == filter_type]

        self.voice_menu.configure(values=filtered)
        if filtered:
            self.voice_menu.set(filtered[0])
            self._on_voice_select(filtered[0])

    def _on_voice_select(self, voice_name: str):
        self.selected_voice = voice_name
        data = self._voices_dict.get(voice_name, {})
        self.voice_name_label.configure(text=f"👤 {voice_name}")
        self.voice_tags_label.configure(text=f"{data.get('gender', '')} • {data.get('region', '')} • {data.get('style', '')}")
        self.voice_desc_label.configure(text=data.get('desc', ''))

    def set_selected_voice(self, voice_name: str):
        """Đặt giọng đọc được chọn theo cấu hình lưu trữ."""
        if voice_name in self._all_voice_names:
            self.voice_menu.set(voice_name)
            self._on_voice_select(voice_name)


    def _handle_generate_click(self, text: str):
        if self.on_generate_request:
            self.on_generate_request(text, self.selected_voice)


