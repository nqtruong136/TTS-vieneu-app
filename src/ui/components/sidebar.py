"""
Sidebar component for CustomTkinter GUI.
Contains Profile Presets, Voice Selector, Voice Cloning file picker, and Theme toggle.
"""
import os
from typing import Callable, Optional, Dict, Any
import customtkinter as ctk
from tkinter import filedialog

from ...config import PROFILES, PRESET_VOICES, DEFAULT_VOICE, DEFAULT_PROFILE_KEY
from ..styles import COLORS, FONTS


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_profile_change: Optional[Callable[[str], None]] = None,
        on_voice_change: Optional[Callable[[str], None]] = None,
        on_clone_file_change: Optional[Callable[[Optional[str]], None]] = None,
        **kwargs
    ):
        super().__init__(master, width=280, corner_radius=0, **kwargs)
        self.grid_propagate(False)

        self.on_profile_change = on_profile_change
        self.on_voice_change = on_voice_change
        self.on_clone_file_change = on_clone_file_change

        self.selected_ref_audio: Optional[str] = None
        self._profiles_map = {cfg["name"]: key for key, cfg in PROFILES.items()}
        self._voices_map = {f"{v['name']} ({v['gender']} · {v['region']})": v["name"] for v in PRESET_VOICES}
        self._voice_details = {v["name"]: v for v in PRESET_VOICES}

        self._create_widgets()

    def _create_widgets(self):
        # 1. Logo & App Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=16, pady=(18, 12))

        logo_label = ctk.CTkLabel(
            title_frame,
            text="🦜 VieNeu-TTS",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["primary"]
        )
        logo_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Desktop Studio • v3 Turbo 48kHz",
            font=FONTS["caption"],
            text_color="gray"
        )
        subtitle_label.pack(anchor="w")

        separator1 = ctk.CTkFrame(self, height=1, fg_color=COLORS["border_dark"])
        separator1.pack(fill="x", padx=16, pady=4)

        # 2. Section: BỘ CẤU HÌNH CÓ SẴN (Profiles)
        profile_section = ctk.CTkFrame(self, fg_color="transparent")
        profile_section.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            profile_section,
            text="⚙️ BỘ CẤU HÌNH SẴN",
            font=FONTS["header"]
        ).pack(anchor="w", pady=(2, 4))

        profile_names = list(self._profiles_map.keys())
        default_profile_name = PROFILES[DEFAULT_PROFILE_KEY]["name"]

        self.profile_menu = ctk.CTkOptionMenu(
            profile_section,
            values=profile_names,
            command=self._handle_profile_select,
            dynamic_resizing=False,
            height=32
        )
        self.profile_menu.set(default_profile_name)
        self.profile_menu.pack(fill="x", pady=2)

        # Profile description box
        self.profile_desc_box = ctk.CTkLabel(
            profile_section,
            text=PROFILES[DEFAULT_PROFILE_KEY]["description"],
            font=FONTS["caption"],
            text_color="gray",
            wraplength=240,
            justify="left"
        )
        self.profile_desc_box.pack(anchor="w", pady=(4, 6))

        self.btn_apply_profile = ctk.CTkButton(
            profile_section,
            text="🔄 Áp dụng cấu hình",
            height=28,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["primary"],
            text_color=COLORS["primary"],
            hover_color=COLORS["card_bg_dark"],
            command=self._apply_profile_click
        )
        self.btn_apply_profile.pack(fill="x", pady=(0, 4))

        separator2 = ctk.CTkFrame(self, height=1, fg_color=COLORS["border_dark"])
        separator2.pack(fill="x", padx=16, pady=6)

        # 3. Section: CHỌN GIỌNG ĐỌC (Preset Voices)
        voice_section = ctk.CTkFrame(self, fg_color="transparent")
        voice_section.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            voice_section,
            text="🎙️ GIỌNG ĐỌC DỰNG SẴN",
            font=FONTS["header"]
        ).pack(anchor="w", pady=(2, 4))

        voice_display_list = list(self._voices_map.keys())
        default_voice_display = [k for k, v in self._voices_map.items() if v == DEFAULT_VOICE][0]

        self.voice_menu = ctk.CTkOptionMenu(
            voice_section,
            values=voice_display_list,
            command=self._handle_voice_select,
            dynamic_resizing=False,
            height=32
        )
        self.voice_menu.set(default_voice_display)
        self.voice_menu.pack(fill="x", pady=2)

        # Voice details badge
        self.voice_info_label = ctk.CTkLabel(
            voice_section,
            text=self._voice_details[DEFAULT_VOICE]["desc"],
            font=FONTS["caption"],
            text_color="gray",
            wraplength=240,
            justify="left"
        )
        self.voice_info_label.pack(anchor="w", pady=(4, 4))

        separator3 = ctk.CTkFrame(self, height=1, fg_color=COLORS["border_dark"])
        separator3.pack(fill="x", padx=16, pady=6)

        # 4. Section: INSTANT VOICE CLONING (Nhân bản giọng)
        clone_section = ctk.CTkFrame(self, fg_color="transparent")
        clone_section.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            clone_section,
            text="🧬 VOICE CLONING (Tùy chọn)",
            font=FONTS["header"]
        ).pack(anchor="w", pady=(2, 2))

        ctk.CTkLabel(
            clone_section,
            text="Chọn file mẫu 3–8s để nhân bản giọng:",
            font=FONTS["caption"],
            text_color="gray"
        ).pack(anchor="w", pady=(0, 4))

        # File picker button & Clear button
        file_btn_frame = ctk.CTkFrame(clone_section, fg_color="transparent")
        file_btn_frame.pack(fill="x", pady=2)

        self.btn_pick_audio = ctk.CTkButton(
            file_btn_frame,
            text="📁 Chọn file audio...",
            height=30,
            command=self._pick_audio_file,
            font=FONTS["body"]
        )
        self.btn_pick_audio.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_clear_clone = ctk.CTkButton(
            file_btn_frame,
            text="✕",
            width=30,
            height=30,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=self._clear_clone_file
        )
        self.btn_clear_clone.pack(side="right")

        self.clone_file_label = ctk.CTkLabel(
            clone_section,
            text="Chưa chọn (Dùng giọng dựng sẵn)",
            font=FONTS["caption"],
            text_color="gray",
            wraplength=240,
            justify="left"
        )
        self.clone_file_label.pack(anchor="w", pady=(4, 4))

        # 5. Bottom: Appearance Mode Selector
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.pack(side="bottom", fill="x", padx=16, pady=16)

        ctk.CTkLabel(theme_frame, text="🌓 Giao diện:", font=FONTS["caption"], text_color="gray").pack(side="left")
        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Dark", "Light", "System"],
            width=100,
            height=26,
            command=self._change_appearance_mode
        )
        self.theme_menu.set("Dark")
        self.theme_menu.pack(side="right")

    def _handle_profile_select(self, chosen_name: str):
        profile_key = self._profiles_map.get(chosen_name, DEFAULT_PROFILE_KEY)
        desc = PROFILES[profile_key]["description"]
        self.profile_desc_box.configure(text=desc)

    def _apply_profile_click(self):
        chosen_name = self.profile_menu.get()
        profile_key = self._profiles_map.get(chosen_name, DEFAULT_PROFILE_KEY)
        if self.on_profile_change:
            self.on_profile_change(profile_key)

    def _handle_voice_select(self, chosen_display: str):
        voice_name = self._voices_map.get(chosen_display, DEFAULT_VOICE)
        details = self._voice_details.get(voice_name, {})
        self.voice_info_label.configure(text=details.get("desc", ""))
        if self.on_voice_change:
            self.on_voice_change(voice_name)

    def _pick_audio_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file audio mẫu (3-8 giây) để Clone giọng",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.ogg *.m4a"),
                ("WAV Files", "*.wav"),
                ("MP3 Files", "*.mp3"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.selected_ref_audio = file_path
            filename = os.path.basename(file_path)
            self.clone_file_label.configure(
                text=f"🎯 Đã chọn: {filename}",
                text_color=COLORS["secondary"]
            )
            if self.on_clone_file_change:
                self.on_clone_file_change(file_path)

    def _clear_clone_file(self):
        self.selected_ref_audio = None
        self.clone_file_label.configure(
            text="Chưa chọn (Dùng giọng dựng sẵn)",
            text_color="gray"
        )
        if self.on_clone_file_change:
            self.on_clone_file_change(None)

    def _change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode)

    def get_selected_profile_key(self) -> str:
        chosen_name = self.profile_menu.get()
        return self._profiles_map.get(chosen_name, DEFAULT_PROFILE_KEY)

    def get_selected_voice(self) -> str:
        chosen_display = self.voice_menu.get()
        return self._voices_map.get(chosen_display, DEFAULT_VOICE)

    def get_ref_audio(self) -> Optional[str]:
        return self.selected_ref_audio

