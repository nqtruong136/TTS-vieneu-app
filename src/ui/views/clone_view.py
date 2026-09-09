"""
Clone Voice View (Tab 2: Clone Voice).
Dedicated workspace for Instant Voice Cloning from a 3-8s audio clip.
"""
import os
from tkinter import filedialog
from typing import Callable, Optional
import soundfile as sf
import customtkinter as ctk

from ..styles import COLORS, FONTS
from ..components.editor_panel import EditorPanel
from ..components.player_bar import PlayerBar
from ...core.audio_player import AudioPlayer
from ...core.logger import AppLogger
from ...core.progress import ProgressTracker


class CloneVoiceView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        audio_player: AudioPlayer,
        on_clone_request: Optional[Callable[[str, str, bool, bool], None]] = None,
        progress_tracker: Optional[ProgressTracker] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.audio_player = audio_player
        self.on_clone_request = on_clone_request
        self.progress_tracker = progress_tracker

        self.ref_audio_path: Optional[str] = None
        self._sample_player = AudioPlayer()

        self._create_widgets()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=0, minsize=300)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Left Sub-Sidebar: Reference Audio Selection & Preview
        left_frame = ctk.CTkFrame(
            self,
            width=300,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        left_frame.grid_propagate(False)

        ctk.CTkLabel(
            left_frame,
            text="🧬 THÔNG TIN GIỌNG MẪU",
            font=FONTS["header"]
        ).pack(anchor="w", padx=14, pady=(14, 6))

        # Card chọn file audio
        file_card = ctk.CTkFrame(
            left_frame,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color="transparent"
        )
        file_card.pack(fill="x", padx=14, pady=4)

        self.btn_browse = ctk.CTkButton(
            file_card,
            text="📁 Chọn file âm thanh mẫu...",
            height=34,
            font=("Segoe UI", 12, "bold"),
            command=self._pick_reference_file
        )
        self.btn_browse.pack(fill="x", padx=10, pady=(10, 6))

        self.file_status_label = ctk.CTkLabel(
            file_card,
            text="Chưa chọn file audio",
            font=FONTS["caption"],
            text_color="gray",
            wraplength=250,
            justify="left"
        )
        self.file_status_label.pack(anchor="w", padx=10, pady=2)

        self.file_meta_label = ctk.CTkLabel(
            file_card,
            text="",
            font=("Segoe UI", 10),
            text_color=COLORS["secondary"],
            wraplength=250,
            justify="left"
        )
        self.file_meta_label.pack(anchor="w", padx=10, pady=(0, 8))

        # Preview player for reference clip
        preview_frame = ctk.CTkFrame(file_card, fg_color="transparent")
        preview_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_listen_ref = ctk.CTkButton(
            preview_frame,
            text="▶ Nghe mẫu",
            width=90,
            height=26,
            font=FONTS["caption"],
            state="disabled",
            fg_color=COLORS["secondary"],
            command=self._play_reference_sample
        )
        self.btn_listen_ref.pack(side="left", padx=(0, 4))

        self.btn_stop_ref = ctk.CTkButton(
            preview_frame,
            text="⏹ Dừng",
            width=60,
            height=26,
            font=FONTS["caption"],
            state="disabled",
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._stop_reference_sample
        )
        self.btn_stop_ref.pack(side="left")

        # Denoise switch
        self.denoise_switch = ctk.CTkSwitch(
            left_frame,
            text="Tự động khử nhiễu (Denoise)",
            font=FONTS["caption"]
        )
        self.denoise_switch.select()
        self.denoise_switch.pack(anchor="w", padx=14, pady=12)
        self.denoise_switch.pack(anchor="w", padx=14, pady=(10, 4))

        # Clean Timbre switch
        self.clean_timbre_switch = ctk.CTkSwitch(
            left_frame,
            text="Ưu tiên trong trẻo (Lọc vang/hộp)",
            font=FONTS["caption"]
        )
        self.clean_timbre_switch.select()
        self.clean_timbre_switch.pack(anchor="w", padx=14, pady=(4, 12))

        # Instruction Card
        tips_card = ctk.CTkFrame(
            left_frame,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color="transparent"
        )
        tips_card.pack(fill="x", padx=14, pady=4)

        ctk.CTkLabel(
            tips_card,
            text="💡 Bí quyết âm thanh trong trẻo (48kHz):",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["primary"]
        ).pack(anchor="w", padx=10, pady=(8, 4))

        tips_text = (
            "• Độ dài khuyến nghị: 3 đến 8 giây.\n"
            "• Âm thanh nói rõ ràng, tự nhiên.\n"
            "• Không có nhạc nền hoặc tiếng ồn lớn.\n"
            "• Định dạng: .wav, .mp3, .m4a, .ogg.\n\n"
            "Mô hình sẽ trích xuất đặc trưng âm sắc (speaker embedding) để đọc câu mới."
            "• Đầu ra luôn đạt chuẩn Studio 48,000 Hz.\n"
            "• Bật 'Ưu tiên trong trẻo': loại bỏ tiếng vang phòng (reverb) và tiếng bí từ micro mẫu.\n"
            "• Đoạn mẫu lý tưởng: 3 đến 6 giây, nói to rõ, miệng cách micro 10-15cm, không vang tường.\n"
            "• Hỗ trợ định dạng: .wav, .mp3, .m4a, .flac, .ogg."
        )
        ctk.CTkLabel(
            tips_card,
            text=tips_text,
            font=FONTS["caption"],
            text_color="gray",
            wraplength=250,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(0, 10))

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
        self.editor_panel.btn_generate.configure(text="🧬 BẮT ĐẦU CLONE GIỌNG NÓI  (Ctrl + Enter)")

        self.player_bar = PlayerBar(
            center_frame,
            audio_player=self.audio_player
        )
        self.player_bar.grid(row=1, column=0, sticky="ew")

    def _pick_reference_file(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file audio mẫu (3–8s) để clone giọng",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.m4a *.ogg"),
                ("WAV Files", "*.wav"),
                ("MP3 Files", "*.mp3"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.ref_audio_path = file_path
            filename = os.path.basename(file_path)
            self.file_status_label.configure(
                text=f"🎯 {filename}",
                text_color="white"
            )

            # Đọc thông tin file
            try:
                info = sf.info(file_path)
                meta_str = f"Thời lượng: {info.duration:.1f}s • {info.samplerate} Hz • {info.channels} kênh"
                self.file_meta_label.configure(text=meta_str)
                AppLogger.info(f"Đã chọn clip mẫu: {filename} ({info.duration:.1f}s, {info.samplerate}Hz)", source="VoiceCloner")
            except Exception as e:
                AppLogger.warning(f"Không thể đọc metadata của file {filename}: {e}", source="VoiceCloner")
                self.file_meta_label.configure(text="")

            self.btn_listen_ref.configure(state="normal")
            self.btn_stop_ref.configure(state="normal")

    def _play_reference_sample(self):
        if self.ref_audio_path and os.path.exists(self.ref_audio_path):
            AppLogger.info(f"Nghe thử clip mẫu: {os.path.basename(self.ref_audio_path)}", source="VoiceCloner")
            self._sample_player.load_and_play(self.ref_audio_path)

    def _stop_reference_sample(self):
        self._sample_player.stop()

    def _handle_generate_click(self, text: str):
        if not self.ref_audio_path or not os.path.exists(self.ref_audio_path):
            warn_msg = "Vui lòng chọn file âm thanh mẫu (3–8s) ở cột bên trái trước!"
            AppLogger.warning(warn_msg, source="VoiceCloner")
            self.editor_panel.set_status(f"⚠️ {warn_msg}", is_error=True)
            return

        denoise = bool(self.denoise_switch.get())
        AppLogger.info(f"Bắt đầu yêu cầu nhân bản giọng nói (Denoise: {denoise})...", source="VoiceCloner")
        clean_timbre = bool(self.clean_timbre_switch.get())
        AppLogger.info(f"Bắt đầu yêu cầu nhân bản giọng nói (Denoise: {denoise}, Trong trẻo: {clean_timbre})...", source="VoiceCloner")
        if self.on_clone_request:
            self.on_clone_request(text, self.ref_audio_path, denoise)
            self.on_clone_request(text, self.ref_audio_path, denoise, clean_timbre)

