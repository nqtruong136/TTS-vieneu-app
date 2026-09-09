"""
YouTube-style Audio Player Bar component for CustomTkinter GUI.
Features interactive scrubbing timeline, -5s / +5s jump buttons, Play/Pause/Stop, and volume control.
"""
import os
import subprocess
from typing import Optional
import customtkinter as ctk

from ...core.audio_player import AudioPlayer
from ..styles import COLORS, FONTS


class PlayerBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        audio_player: AudioPlayer,
        **kwargs
    ):
        super().__init__(master, corner_radius=8, border_width=1, border_color=COLORS["border_dark"], **kwargs)

        self.audio_player = audio_player
        self.current_audio_path: Optional[str] = None
        self._is_user_seeking = False

        self._create_widgets()
        self._start_playback_poller()

    def _create_widgets(self):
        # 1. Top row: Timeline Scrubber (Like YouTube red/accent seek bar)
        timeline_frame = ctk.CTkFrame(self, fg_color="transparent")
        timeline_frame.pack(fill="x", padx=16, pady=(10, 2))

        self.timeline_slider = ctk.CTkSlider(
            timeline_frame,
            from_=0,
            to=1000,
            number_of_steps=1000,
            height=16,
            progress_color=COLORS["primary"],
            button_color=COLORS["primary"],
            button_hover_color=COLORS["primary_hover"],
            command=self._on_slider_scrub
        )
        self.timeline_slider.set(0)
        self.timeline_slider.pack(fill="x")

        # Bind chuột để biết khi nào user đang kéo thả timeline
        self.timeline_slider.bind("<Button-1>", lambda e: self._set_user_seeking(True))
        self.timeline_slider.bind("<ButtonRelease-1>", lambda e: self._on_slider_release())

        # 2. Middle row: Controls (Jump -5s, Play/Pause, Jump +5s, Stop, Time, Volume, Open file)
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x", padx=16, pady=(2, 6))

        # Tua lùi 5 giây (-5s)
        self.btn_back_5 = ctk.CTkButton(
            controls_frame,
            text="⏪ -5s",
            width=54,
            height=32,
            font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["card_bg_dark"],
            hover_color=COLORS["primary"],
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda: self._jump_seconds(-5.0)
        )
        self.btn_back_5.pack(side="left", padx=(0, 4))

        # Nút Play / Pause lớn nổi bật
        self.btn_play = ctk.CTkButton(
            controls_frame,
            text="▶",
            width=46,
            height=34,
            font=("Segoe UI", 15, "bold"),
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=self._play_click
        )
        self.btn_play.pack(side="left", padx=(0, 4))

        # Tua tới 5 giây (+5s)
        self.btn_forward_5 = ctk.CTkButton(
            controls_frame,
            text="+5s ⏩",
            width=54,
            height=32,
            font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["card_bg_dark"],
            hover_color=COLORS["primary"],
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda: self._jump_seconds(5.0)
        )
        self.btn_forward_5.pack(side="left", padx=(0, 4))

        # Nút Stop
        self.btn_stop = ctk.CTkButton(
            controls_frame,
            text="⏹",
            width=36,
            height=32,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLORS["card_bg_dark"],
            hover_color=COLORS["danger"],
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._stop_click
        )
        self.btn_stop.pack(side="left", padx=(0, 12))

        # Bộ đếm thời gian (00:04 / 01:25)
        self.time_label = ctk.CTkLabel(
            controls_frame,
            text="00:00 / 00:00",
            font=FONTS["code"],
            width=105,
            anchor="w"
        )
        self.time_label.pack(side="left", padx=(0, 12))

        # Spacer
        ctk.CTkFrame(controls_frame, fg_color="transparent").pack(side="left", fill="x", expand=True)

        # Volume control
        self.vol_icon = ctk.CTkLabel(controls_frame, text="🔊", font=FONTS["body"])
        self.vol_icon.pack(side="left", padx=(0, 4))

        self.vol_slider = ctk.CTkSlider(
            controls_frame,
            from_=0,
            to=1.0,
            width=85,
            height=14,
            command=self._volume_change
        )
        self.vol_slider.set(self.audio_player.get_volume())
        self.vol_slider.pack(side="left", padx=(0, 10))

        # Open file button
        self.btn_open_file = ctk.CTkButton(
            controls_frame,
            text="📂",
            width=32,
            height=32,
            font=FONTS["body"],
            fg_color="transparent",
            hover_color=COLORS["card_bg_dark"],
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._open_in_explorer
        )
        self.btn_open_file.pack(side="right")

        # 3. Bottom row: Stats & metadata
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.stats_label = ctk.CTkLabel(
            self.stats_frame,
            text="Chưa có bản thu nào được phát.",
            font=FONTS["caption"],
            text_color="gray",
            anchor="w"
        )
        self.stats_label.pack(side="left", fill="x", expand=True)

    def set_audio_result(self, result_dict: dict, auto_play: bool = True):
        """Cập nhật bản thu mới sinh từ TTS Engine hoặc từ thư viện lịch sử."""
        self.current_audio_path = result_dict.get("audio_path")
        duration = result_dict.get("duration", 0.0)
        proc_time = result_dict.get("process_time", 0.0)
        rtf = result_dict.get("rtf", 0.0)
        voice = result_dict.get("voice", "")
        filename = os.path.basename(self.current_audio_path) if self.current_audio_path else ""

        rtf_comparison = f"(Nhanh hơn {1/rtf:.1f}x real-time)" if 0 < rtf < 1 else ""
        stats_text = (
            f"🎵 {filename}  •  ⏱ Tạo: {proc_time:.2f}s  •  "
            f"Độ dài: {duration:.2f}s  •  📊 RTF: {rtf:.3f} {rtf_comparison}  •  Giọng: {voice}"
        )
        self.stats_label.configure(text=stats_text, text_color=COLORS["secondary"])

        mins = int(duration // 60)
        secs = int(duration % 60)
        self.time_label.configure(text=f"00:00 / {mins:02d}:{secs:02d}")

        # Tự động phát nếu auto_play=True
        if auto_play and self.current_audio_path:
            self.play_file(self.current_audio_path)

    def play_file(self, audio_path: str):
        if not os.path.exists(audio_path):
            self.stats_label.configure(text=f"❌ Không tìm thấy tệp âm thanh: {audio_path}", text_color=COLORS["danger"])
            return
        self.current_audio_path = audio_path
        success = self.audio_player.load_and_play(audio_path)
        if success:
            self.btn_play.configure(text="⏸", fg_color=COLORS["primary"])
            self._update_time_display()

    def _play_click(self):
        if self.audio_player.is_playing():
            self.audio_player.pause()
            self.btn_play.configure(text="▶", fg_color=COLORS["secondary"])
        elif self.audio_player.is_paused():
            self.audio_player.resume()
            self.btn_play.configure(text="⏸", fg_color=COLORS["primary"])
        elif self.current_audio_path and os.path.exists(self.current_audio_path):
            self.play_file(self.current_audio_path)

    def _stop_click(self):
        self.audio_player.stop()
        self.btn_play.configure(text="▶", fg_color=COLORS["secondary"])
        self.timeline_slider.set(0)
        self._update_time_display(elapsed=0.0)

    def _jump_seconds(self, delta_sec: float):
        """Tua nhanh tiến hoặc lùi delta giây."""
        self.audio_player.seek_relative(delta_sec)
        elapsed = self.audio_player.get_elapsed_seconds()
        self._update_time_display(elapsed)
        total = self.audio_player.get_total_duration()
        if total > 0:
            self.timeline_slider.set((elapsed / total) * 1000.0)

    def _set_user_seeking(self, is_seeking: bool):
        self._is_user_seeking = is_seeking

    def _on_slider_scrub(self, val: float):
        total = self.audio_player.get_total_duration()
        if total > 0:
            target_sec = (val / 1000.0) * total
            self._update_time_display(target_sec)

    def _on_slider_release(self):
        self._is_user_seeking = False
        val = self.timeline_slider.get()
        total = self.audio_player.get_total_duration()
        if total > 0:
            target_sec = (val / 1000.0) * total
            self.audio_player.seek(target_sec)
            if not self.audio_player.is_playing() and not self.audio_player.is_paused():
                # Nếu chưa phát thì bấm phát luôn tại vị trí đó
                self.audio_player.load_and_play(self.current_audio_path, start_sec=target_sec)
                self.btn_play.configure(text="⏸", fg_color=COLORS["primary"])

    def _volume_change(self, val: float):
        self.audio_player.set_volume(val)
        if val == 0:
            self.vol_icon.configure(text="🔇")
        elif val < 0.5:
            self.vol_icon.configure(text="🔉")
        else:
            self.vol_icon.configure(text="🔊")

    def _open_in_explorer(self):
        if self.current_audio_path and os.path.exists(self.current_audio_path):
            subprocess.Popen(f'explorer /select,"{os.path.abspath(self.current_audio_path)}"')
        else:
            from ...config import OUTPUTS_DIR
            subprocess.Popen(f'explorer "{os.path.abspath(OUTPUTS_DIR)}"')

    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def _update_time_display(self, elapsed: Optional[float] = None):
        total = self.audio_player.get_total_duration()
        if elapsed is None:
            elapsed = self.audio_player.get_elapsed_seconds()
        self.time_label.configure(text=f"{self._format_time(elapsed)} / {self._format_time(total)}")

    def _start_playback_poller(self):
        """Vòng lặp cập nhật tiến độ phát thời gian thực nếu user không đang kéo thanh tua."""
        if self.audio_player.is_playing() and not self._is_user_seeking:
            elapsed = self.audio_player.get_elapsed_seconds()
            total = self.audio_player.get_total_duration()
            self._update_time_display(elapsed)
            if total > 0:
                progress = min(1000.0, (elapsed / total) * 1000.0)
                self.timeline_slider.set(progress)
                self.btn_play.configure(text="⏸", fg_color=COLORS["primary"])
        elif self.audio_player.is_paused():
            self.btn_play.configure(text="▶", fg_color=COLORS["secondary"])

        self.after(100, self._start_playback_poller)
