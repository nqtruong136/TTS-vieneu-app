"""
Settings & Diagnostics View (Tab: Cài đặt hệ thống).
Hardware readiness check, PyTorch CUDA auto-install with live logs and progress %,
Model cache manager, Benchmark with % progress, and Live Log Console.
"""
import os
import sys
import subprocess
import threading
from typing import Callable, Optional
from tkinter import filedialog
import customtkinter as ctk

from ..styles import COLORS, FONTS
from ...core.hardware_service import HardwareService
from ...core.tts_engine import TTSEngine
from ...core.logger import AppLogger
from ...core.progress import ProgressTracker
from ..components.log_console import LogConsole
from ..components.progress_bar import ProgressDisplay
from ..components.action_log_box import ActionLogBox
from ..dispatcher import UIDispatcher
from ...config import PROFILES, DEFAULT_PROFILE_KEY, PRESET_VOICES, DEFAULT_VOICE, OUTPUTS_DIR
from ...core.config_manager import ConfigManager


class SettingsView(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master,
        tts_engine: TTSEngine,
        config_manager: Optional[ConfigManager] = None,
        on_profile_reloaded: Optional[Callable[[str], None]] = None,
        on_config_saved: Optional[Callable[[dict], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.tts_engine = tts_engine
        self.config_manager = config_manager or ConfigManager.get_instance()
        self.on_profile_reloaded = on_profile_reloaded
        self.on_config_saved = on_config_saved
        self._profiles_map = {cfg["name"]: key for key, cfg in PROFILES.items()}

        # Thư mục cài đặt CUDA do người dùng chỉ định (mặc định là .venv hiện tại)
        self.install_folder_var = ctk.StringVar(value=os.path.abspath(sys.prefix))

        # Biến cấu hình ứng dụng được nạp từ ConfigManager
        self.auto_load_var = ctk.BooleanVar(value=self.config_manager.get("auto_load_on_startup", True))
        self.auto_play_var = ctk.BooleanVar(value=self.config_manager.get("auto_play_audio", True))
        self.output_dir_var = ctk.StringVar(value=self.config_manager.get("audio_output_dir", str(OUTPUTS_DIR)))
        self.default_voice_var = ctk.StringVar(value=self.config_manager.get("default_voice", DEFAULT_VOICE))
        self.theme_var = ctk.StringVar(value=self.config_manager.get("appearance_mode", "Dark"))
        self.realtime_clip_var = ctk.BooleanVar(value=self.config_manager.get("realtime_clipboard_trigger", False))

        prebuf = self.config_manager.get("realtime_prebuffer_chunks", 2)
        if prebuf == 1:
            buf_str = "1 chunk (Siêu tốc ~200ms - Cho máy mạnh)"
        elif prebuf == 3:
            buf_str = "3 chunks (Mượt mà tối đa - Chống giật)"
        else:
            buf_str = "2 chunks (Cân bằng - Khuyên dùng)"
        self.jitter_buffer_var = ctk.StringVar(value=buf_str)

        # Các tracker tiến trình chuyên biệt
        self.cuda_progress = ProgressTracker()
        self.sec2_cuda_progress = ProgressTracker()
        self.bench_progress = ProgressTracker()
        self.download_progress = ProgressTracker()

        self._create_widgets()
        self._refresh_hardware_info()
        self._refresh_model_cache_info()


    def _create_widgets(self):
        # Header
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            title_frame,
            text="⚙️ CÀI ĐẶT HỆ THỐNG & CHẨN ĐOÁN PHẦN CỨNG",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS["primary"]
        ).pack(side="left")

        btn_refresh_all = ctk.CTkButton(
            title_frame,
            text="🔄 Quét lại phần cứng",
            width=140,
            height=28,
            font=FONTS["caption"],
            command=self._refresh_all
        )
        btn_refresh_all.pack(side="right")

        # =========================================================================
        # SECTION 1: KIỂM TRA PHẦN CỨNG (Hardware Readiness)
        # =========================================================================
        sec1 = self._create_section_card("🔍 1. KIỂM TRA PHẦN CỨNG & TÍNH SẴN SÀNG")

        # Row CPU & ONNX
        self.cpu_info_label = ctk.CTkLabel(
            sec1,
            text="Đang kiểm tra CPU...",
            font=FONTS["body"],
            justify="left",
            anchor="w"
        )
        self.cpu_info_label.pack(fill="x", padx=14, pady=(6, 2))

        # Row GPU & CUDA
        self.gpu_info_label = ctk.CTkLabel(
            sec1,
            text="Đang kiểm tra GPU...",
            font=FONTS["body"],
            justify="left",
            anchor="w"
        )
        self.gpu_info_label.pack(fill="x", padx=14, pady=2)

        # CUDA Instruction / One-click install frame
        self.cuda_guide_frame = ctk.CTkFrame(sec1, fg_color=COLORS["card_bg_dark"], corner_radius=6)
        self.cuda_guide_frame.pack(fill="x", padx=14, pady=(8, 12))

        self.cuda_status_badge = ctk.CTkLabel(
            self.cuda_guide_frame,
            text="Trạng thái CUDA: Đang kiểm tra...",
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        )
        self.cuda_status_badge.pack(fill="x", padx=10, pady=(8, 2))

        self.cuda_help_text = ctk.CTkLabel(
            self.cuda_guide_frame,
            text="",
            font=FONTS["caption"],
            text_color="gray",
            wraplength=700,
            justify="left"
        )
        self.cuda_help_text.pack(fill="x", padx=10, pady=2)

        # Thanh tiến trình phần trăm cài đặt CUDA
        self.cuda_progress_display = ProgressDisplay(
            self.cuda_guide_frame,
            tracker=self.cuda_progress
        )
        self.cuda_progress_display.pack(fill="x", padx=10, pady=(4, 6))

        # Folder cài đặt cho Section 1 do user chỉ đến
        self.folder_frame_sec1 = ctk.CTkFrame(self.cuda_guide_frame, fg_color="transparent")
        self.folder_frame_sec1.pack(fill="x", padx=10, pady=(2, 6))

        ctk.CTkLabel(
            self.folder_frame_sec1,
            text="📁 Folder cài (Môi trường / Thư mục đích do user chỉ đến):",
            font=FONTS["caption"],
            text_color=COLORS["text_muted_dark"],
            anchor="w"
        ).pack(fill="x", pady=(0, 2))

        f_sub1 = ctk.CTkFrame(self.folder_frame_sec1, fg_color="transparent")
        f_sub1.pack(fill="x")

        self.entry_folder_sec1 = ctk.CTkEntry(
            f_sub1,
            textvariable=self.install_folder_var,
            height=28,
            font=FONTS["caption"]
        )
        self.entry_folder_sec1.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            f_sub1,
            text="📂 Chọn thư mục...",
            width=120,
            height=28,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._browse_install_folder
        ).pack(side="right")

        self.btn_install_cuda = ctk.CTkButton(
            self.cuda_guide_frame,
            text="🚀 Bắt đầu cài đặt PyTorch CUDA cho GPU (Tự động)",
            height=32,
            font=FONTS["caption"],
            command=self._install_cuda_click
        )
        # Hộp log ngữ cảnh cho quá trình cài đặt CUDA
        self.cuda_log_box = ActionLogBox(self.cuda_guide_frame, title="Tiến trình cài đặt PyTorch CUDA")

        # =========================================================================
        # SECTION 2: CẤU HÌNH ENGINE & THIẾT BỊ (Engine Setup)
        # =========================================================================
        sec2 = self._create_section_card("⚙️ 2. CẤU HÌNH ENGINE, LƯU TRỮ & TÙY CHỌN HỆ THỐNG")

        # --- A. CẤU HÌNH ENGINE & MÔ HÌNH ---
        card_engine = ctk.CTkFrame(sec2, fg_color=COLORS["card_bg_dark"], corner_radius=6)
        card_engine.pack(fill="x", padx=14, pady=(8, 6))

        ctk.CTkLabel(
            card_engine,
            text="🧠 CẤU HÌNH MÔ HÌNH & KHỞI ĐỘNG",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["primary"],
            anchor="w"
        ).pack(fill="x", padx=12, pady=(8, 4))

        cfg_grid = ctk.CTkFrame(card_engine, fg_color="transparent")
        cfg_grid.pack(fill="x", padx=12, pady=(0, 6))
        cfg_grid.grid_columnconfigure(0, weight=1)
        cfg_grid.grid_columnconfigure(1, weight=1)

        # Chọn bộ profile
        ctk.CTkLabel(cfg_grid, text="Bộ cấu hình mẫu khởi động:", font=FONTS["caption"], text_color=COLORS["text_muted_dark"]).grid(row=0, column=0, sticky="w", pady=2)
        profile_names = list(self._profiles_map.keys())
        self.profile_menu = ctk.CTkOptionMenu(
            cfg_grid,
            values=profile_names,
            height=32,
            command=self._on_profile_select
        )
        saved_prof_key = self.config_manager.get("default_profile", DEFAULT_PROFILE_KEY)
        saved_prof_name = PROFILES.get(saved_prof_key, PROFILES[DEFAULT_PROFILE_KEY])["name"]
        self.profile_menu.set(saved_prof_name)
        self.profile_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 6))

        # Precision (fp32 vs int8)
        ctk.CTkLabel(cfg_grid, text="Độ chính xác CPU (Precision):", font=FONTS["caption"], text_color=COLORS["text_muted_dark"]).grid(row=0, column=1, sticky="w", pady=2)
        self.precision_menu = ctk.CTkOptionMenu(
            cfg_grid,
            values=["fp32 (Chất lượng tối đa)", "int8 (Tăng tốc VNNI - Nhẹ x4)"],
            height=32
        )
        saved_prec = self.config_manager.get("precision", "fp32")
        self.precision_menu.set("int8 (Tăng tốc VNNI - Nhẹ x4)" if saved_prec == "int8" else "fp32 (Chất lượng tối đa)")
        self.precision_menu.grid(row=1, column=1, sticky="ew", pady=(0, 6))

        # Profile description
        self.profile_desc_label = ctk.CTkLabel(
            card_engine,
            text=PROFILES.get(saved_prof_key, PROFILES[DEFAULT_PROFILE_KEY])["description"],
            font=FONTS["caption"],
            text_color="gray",
            anchor="w",
            wraplength=700,
            justify="left"
        )
        self.profile_desc_label.pack(fill="x", padx=12, pady=(0, 6))

        # Switch auto-load on startup
        self.switch_auto_load = ctk.CTkSwitch(
            card_engine,
            text="⚡ Tự động nạp mô hình ngay khi mở ứng dụng (Startup Auto-load)",
            variable=self.auto_load_var,
            font=FONTS["caption"]
        )
        self.switch_auto_load.pack(anchor="w", padx=12, pady=(0, 10))

        # --- B. LƯU TRỮ & THƯ MỤC XUẤT TỆP ÂM THANH ---
        card_storage = ctk.CTkFrame(sec2, fg_color=COLORS["card_bg_dark"], corner_radius=6)
        card_storage.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(
            card_storage,
            text="💾 THƯ MỤC LƯU TRỮ & PHÁT ÂM THANH",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["primary"],
            anchor="w"
        ).pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            card_storage,
            text="📁 Thư mục lưu tệp âm thanh WAV sinh ra:",
            font=FONTS["caption"],
            text_color=COLORS["text_muted_dark"],
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 2))

        f_out_row = ctk.CTkFrame(card_storage, fg_color="transparent")
        f_out_row.pack(fill="x", padx=12, pady=(0, 6))

        self.entry_output_dir = ctk.CTkEntry(
            f_out_row,
            textvariable=self.output_dir_var,
            height=30,
            font=FONTS["caption"]
        )
        self.entry_output_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            f_out_row,
            text="📂 Chọn thư mục...",
            width=120,
            height=30,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._browse_output_folder
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            f_out_row,
            text="📁 Mở thư mục",
            width=100,
            height=30,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._open_output_folder
        ).pack(side="right")

        self.switch_auto_play = ctk.CTkSwitch(
            card_storage,
            text="▶️ Tự động phát âm thanh ngay sau khi tạo xong (Auto-play)",
            variable=self.auto_play_var,
            font=FONTS["caption"]
        )
        self.switch_auto_play.pack(anchor="w", padx=12, pady=(0, 10))

        # --- C. GIỌNG ĐỌC, GIAO DIỆN & REALTIME ---
        card_prefs = ctk.CTkFrame(sec2, fg_color=COLORS["card_bg_dark"], corner_radius=6)
        card_prefs.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(
            card_prefs,
            text="🎨 GIỌNG ĐỌC, GIAO DIỆN & REALTIME STREAMING",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["primary"],
            anchor="w"
        ).pack(fill="x", padx=12, pady=(8, 4))

        pref_grid = ctk.CTkFrame(card_prefs, fg_color="transparent")
        pref_grid.pack(fill="x", padx=12, pady=(0, 6))
        pref_grid.grid_columnconfigure(0, weight=1)
        pref_grid.grid_columnconfigure(1, weight=1)

        # Giọng đọc mặc định
        ctk.CTkLabel(pref_grid, text="Giọng đọc ưu tiên ban đầu:", font=FONTS["caption"], text_color=COLORS["text_muted_dark"]).grid(row=0, column=0, sticky="w", pady=2)
        voice_names = [v["name"] for v in PRESET_VOICES]
        self.default_voice_menu = ctk.CTkOptionMenu(
            pref_grid,
            values=voice_names,
            height=32
        )
        saved_voice = self.config_manager.get("default_voice", DEFAULT_VOICE)
        if saved_voice in voice_names:
            self.default_voice_menu.set(saved_voice)
        else:
            self.default_voice_menu.set(DEFAULT_VOICE)
        self.default_voice_menu.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 6))

        # Giao diện mặc định (Theme)
        ctk.CTkLabel(pref_grid, text="Giao diện hiển thị mặc định:", font=FONTS["caption"], text_color=COLORS["text_muted_dark"]).grid(row=0, column=1, sticky="w", pady=2)
        self.theme_menu_setting = ctk.CTkOptionMenu(
            pref_grid,
            values=["Dark", "Light", "System"],
            height=32,
            command=self._on_theme_select
        )
        self.theme_menu_setting.set(self.theme_var.get())
        self.theme_menu_setting.grid(row=1, column=1, sticky="ew", pady=(0, 6))

        # Realtime Jitter-Buffer & Clipboard Trigger
        ctk.CTkLabel(pref_grid, text="Bộ đệm Realtime (Jitter-Buffer):", font=FONTS["caption"], text_color=COLORS["text_muted_dark"]).grid(row=2, column=0, sticky="w", pady=2)
        self.jitter_menu = ctk.CTkOptionMenu(
            pref_grid,
            values=[
                "1 chunk (Siêu tốc ~200ms - Cho máy mạnh)",
                "2 chunks (Cân bằng - Khuyên dùng)",
                "3 chunks (Mượt mà tối đa - Chống giật)"
            ],
            height=32
        )
        self.jitter_menu.set(self.jitter_buffer_var.get())
        self.jitter_menu.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 6))

        # Switch Clipboard trigger
        self.switch_clip_trigger = ctk.CTkSwitch(
            pref_grid,
            text="📋 Tự động bật đọc khi Copy (Clipboard Trigger)",
            variable=self.realtime_clip_var,
            font=FONTS["caption"]
        )
        self.switch_clip_trigger.grid(row=3, column=1, sticky="w", pady=(0, 6))

        # --- D. THANH THAO TÁC CẤU HÌNH (Action Buttons) ---
        action_bar = ctk.CTkFrame(sec2, fg_color="transparent")
        action_bar.pack(fill="x", padx=14, pady=(8, 12))

        self.btn_save_config = ctk.CTkButton(
            action_bar,
            text="💾 Lưu cấu hình mặc định",
            height=38,
            width=180,
            font=("Segoe UI", 12, "bold"),
            fg_color="#10B981",
            hover_color="#059669",
            command=self._save_configuration
        )
        self.btn_save_config.pack(side="left", padx=(0, 10))

        self.btn_apply_config = ctk.CTkButton(
            action_bar,
            text="🔄 Áp dụng & Nạp lại Engine",
            height=38,
            width=200,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._apply_engine_config
        )
        self.btn_apply_config.pack(side="left", padx=(0, 10))

        self.btn_reset_config = ctk.CTkButton(
            action_bar,
            text="↩️ Khôi phục mặc định",
            height=38,
            width=160,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._reset_configuration
        )
        self.btn_reset_config.pack(side="left")


        # -------------------------------------------------------------------------
        # KHUNG HỖ TRỢ CÀI ĐẶT PYTORCH CUDA TRỰC TIẾP TẠI MỤC 2
        # -------------------------------------------------------------------------
        self.sec2_cuda_card = ctk.CTkFrame(
            sec2,
            fg_color=COLORS["card_bg_dark"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"]
        )

        ctk.CTkLabel(
            self.sec2_cuda_card,
            text="📦 HỖ TRỢ CÀI ĐẶT PYTORCH CUDA CHO GPU (TRỰC TIẾP TẠI ĐÂY)",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["primary"],
            anchor="w"
        ).pack(fill="x", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            self.sec2_cuda_card,
            text="💡 Bạn đang chọn cấu hình GPU nhưng máy chưa có thư viện PyTorch CUDA. Hãy chỉ định Folder cài đặt và nhấn nút bên dưới để cài trực tiếp.",
            font=FONTS["caption"],
            text_color="gray",
            wraplength=720,
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 8))

        # Folder cài đặt do user chỉ đến
        ctk.CTkLabel(
            self.sec2_cuda_card,
            text="📁 Folder cài (Thư mục môi trường / cài đặt do user chỉ đến):",
            font=FONTS["caption"],
            text_color=COLORS["text_muted_dark"],
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 2))

        f_sub2 = ctk.CTkFrame(self.sec2_cuda_card, fg_color="transparent")
        f_sub2.pack(fill="x", padx=12, pady=(0, 4))

        self.entry_folder_sec2 = ctk.CTkEntry(
            f_sub2,
            textvariable=self.install_folder_var,
            height=30,
            font=FONTS["caption"]
        )
        self.entry_folder_sec2.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            f_sub2,
            text="📂 Chọn thư mục...",
            width=130,
            height=30,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._browse_install_folder
        ).pack(side="right")

        ctk.CTkLabel(
            self.sec2_cuda_card,
            text="ℹ️ Mặc định là môi trường ảo (.venv). Bạn có thể bấm 'Chọn thư mục...' để trỏ đến thư mục khác.",
            font=("Segoe UI", 9),
            text_color="gray",
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 4))

        # Nhãn thông tin gói tự động cài đặt
        ctk.CTkLabel(
            self.sec2_cuda_card,
            text="📦 Gói tự động cài: torch & torchaudio (cu128) + transformers==4.57.6 (chuẩn SDK)",
            font=("Segoe UI", 10, "italic"),
            text_color=COLORS["secondary"],
            anchor="w"
        ).pack(fill="x", padx=12, pady=(0, 6))

        # Nút bấm cài đặt tại Mục 2 (đặt phía trên thanh tiến trình để luôn hiển thị rõ ràng)
        self.btn_install_cuda_sec2 = ctk.CTkButton(
            self.sec2_cuda_card,
            text="🚀 Bắt đầu cài đặt PyTorch CUDA vào Folder này (Tự động)",
            height=34,
            font=("Segoe UI", 11, "bold"),
            fg_color="#10B981",
            hover_color="#059669",
            command=self._install_cuda_sec2_click
        )
        self.btn_install_cuda_sec2.pack(padx=12, pady=(0, 6), anchor="w")

        # Thanh tiến trình cài đặt CUDA tại Mục 2
        self.sec2_cuda_progress_display = ProgressDisplay(
            self.sec2_cuda_card,
            tracker=self.sec2_cuda_progress
        )
        self.sec2_cuda_progress_display.pack(fill="x", padx=12, pady=(0, 8))

        # Hộp log trạng thái theo ngữ cảnh cho việc nạp Engine tại Mục 2
        self.engine_log_box = ActionLogBox(sec2, title="Trạng thái cấu hình Engine")

        # =========================================================================
        # SECTION 3: QUẢN LÝ MÔ HÌNH & TẢI TRƯỚC (Model Cache)
        # =========================================================================
        sec3 = self._create_section_card("📥 3. QUẢN LÝ MÔ HÌNH & TẢI TRƯỚC (CACHE)")

        cache_top = ctk.CTkFrame(sec3, fg_color="transparent")
        cache_top.pack(fill="x", padx=14, pady=6)

        self.cache_size_label = ctk.CTkLabel(
            cache_top,
            text="Tổng dung lượng cache: Đang tính...",
            font=FONTS["header"],
            text_color=COLORS["secondary"]
        )
        self.cache_size_label.pack(side="left")

        btn_open_cache = ctk.CTkButton(
            cache_top,
            text="📂 Mở thư mục Cache",
            width=130,
            height=26,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._open_cache_folder
        )
        btn_open_cache.pack(side="right")

        # Progress bar cho việc tải trước mô hình
        self.dl_progress_display = ProgressDisplay(
            sec3,
            tracker=self.download_progress
        )
        self.dl_progress_display.pack(fill="x", padx=14, pady=(4, 6))

        # Model cards container
        self.model_cards_frame = ctk.CTkFrame(sec3, fg_color="transparent")
        self.model_cards_frame.pack(fill="x", padx=14, pady=(0, 12))
        self.model_cards_frame.pack(fill="x", padx=14, pady=(0, 6))

        # Hộp log trạng thái theo ngữ cảnh cho việc tải mô hình tại Mục 3
        self.cache_log_box = ActionLogBox(sec3, title="Trạng thái nạp mô hình Hugging Face")

        # =========================================================================
        # SECTION 4: BENCHMARK TỐC ĐỘ (Speed Benchmark)
        # =========================================================================
        sec4 = self._create_section_card("⚡ 4. KIỂM TRA TỐC ĐỘ NHÂN GIỌNG (BENCHMARK)")

        ctk.CTkLabel(
            sec4,
            text="Chạy thử nghiệm sinh 1 câu nói chuẩn hóa để đo lường tốc độ xử lý và chỉ số RTF (Real-Time Factor).",
            font=FONTS["caption"],
            text_color="gray"
        ).pack(anchor="w", padx=14, pady=(4, 6))

        # Thanh tiến trình phần trăm Benchmark
        self.bench_progress_display = ProgressDisplay(
            sec4,
            tracker=self.bench_progress
        )
        self.bench_progress_display.pack(fill="x", padx=14, pady=(0, 8))

        bench_btn_row = ctk.CTkFrame(sec4, fg_color="transparent")
        bench_btn_row.pack(fill="x", padx=14, pady=(0, 8))

        self.btn_run_benchmark = ctk.CTkButton(
            bench_btn_row,
            text="🚀 Bắt đầu Benchmark",
            height=34,
            width=160,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=self._start_benchmark_click
        )
        self.btn_run_benchmark.pack(side="left", padx=(0, 10))

        # Hộp log trạng thái theo ngữ cảnh cho Benchmark tại Mục 4
        self.bench_log_box = ActionLogBox(sec4, title="Trạng thái kiểm tra Benchmark")

        # Benchmark results card (hidden initially)
        self.bench_results_card = ctk.CTkFrame(sec4, fg_color=COLORS["card_bg_dark"], corner_radius=6)

        self.bench_result_text = ctk.CTkLabel(
            self.bench_results_card,
            text="",
            font=("Segoe UI", 11),
            justify="left",
            anchor="w"
        )
        self.bench_result_text.pack(fill="x", padx=12, pady=10)

        # =========================================================================
        # SECTION 5: LIVE LOG CONSOLE (Debug Logs & Exceptions)
        # =========================================================================
        sec5 = self._create_section_card("📜 5. NHẬT KÝ HỆ THỐNG VÀ DEBUG CONSOLE")

        self.log_console = LogConsole(sec5, height=220)
        self.log_console.pack(fill="x", padx=14, pady=(4, 12))

    def _create_section_card(self, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color="transparent"
        )
        card.pack(fill="x", pady=6)

        header = ctk.CTkLabel(
            card,
            text=title,
            font=FONTS["header"],
            text_color=COLORS["primary"]
        )
        header.pack(anchor="w", padx=14, pady=(10, 4))

        sep = ctk.CTkFrame(card, height=1, fg_color=COLORS["border_dark"])
        sep.pack(fill="x", padx=14, pady=2)
        return card

    def _refresh_all(self):
        AppLogger.info("Bắt đầu quét lại phần cứng và cache...", source="Settings")
        self._refresh_hardware_info()
        self._refresh_model_cache_info()

    def _refresh_hardware_info(self):
        hw = HardwareService.get_hardware_info()

        # CPU info
        self.cpu_info_label.configure(
            text=f"💻 CPU: {hw['cpu_name']} ({hw['cpu_cores']} luồng xử lý) • ONNX Runtime v{hw['ort_version']} [CPU]"
        )

        # GPU info
        if hw["has_nvidia"]:
            self.gpu_info_label.configure(
                text=f"🎮 GPU: {hw['gpu_name']} • VRAM: {hw['gpu_vram']} • Driver: {hw['gpu_driver']}"
            )

            if hw["cuda_available"]:
                self.cuda_status_badge.configure(
                    text="✅ PyTorch CUDA: ĐÃ SẴN SÀNG (GPU Acceleration)",
                    text_color=COLORS["secondary"]
                )
                self.cuda_help_text.configure(
                    text=f"Card đồ họa {hw['gpu_name']} sẵn sàng tăng tốc PyTorch trên CUDA. Bạn có thể chọn cấu hình GPU ở mục 2 bên dưới."
                )
                self.btn_install_cuda.pack_forget()
                self.folder_frame_sec1.pack_forget()
                self.sec2_cuda_card.pack_forget()
            else:
                self.cuda_status_badge.configure(
                    text="⚠️ PyTorch CUDA: Chưa cài đặt (Đang chạy ONNX Runtime CPU)",
                    text_color="#F59E0B"
                )
                self.cuda_help_text.configure(
                    text=(
                        f"Phát hiện máy có card rời {hw['gpu_name']} ({hw['gpu_vram']}).\n"
                        "Hiện tại ứng dụng đang chạy rất tốt trên CPU bằng ONNX Runtime. Nếu muốn tận dụng GPU để tổng hợp văn bản dài hàng loạt (batching), hãy cài thêm PyTorch CUDA:\n"
                        "👉 uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128"
                    )
                )
                self.folder_frame_sec1.pack(fill="x", padx=10, pady=(2, 6))
                self.btn_install_cuda.pack(padx=10, pady=(4, 8), anchor="w")
        else:
            self.gpu_info_label.configure(
                text="🎮 GPU: Không phát hiện GPU NVIDIA rời. Hệ thống chạy tối ưu trên CPU qua ONNX Runtime."
            )
            self.cuda_status_badge.configure(text="ℹ️ Chế độ CPU ONNX (Khuyên dùng)")
            self.btn_install_cuda.pack_forget()
            self.folder_frame_sec1.pack_forget()
            self.sec2_cuda_card.pack_forget()

    def _refresh_model_cache_info(self):
        cache = HardwareService.get_model_cache_info()
        self.cache_size_label.configure(
            text=f"Tổng dung lượng Cache: {cache['total_size_mb']} MB ({len(cache['models'])} mô hình)"
        )

        for widget in self.model_cards_frame.winfo_children():
            widget.destroy()

        for key, m in cache["models"].items():
            row = ctk.CTkFrame(self.model_cards_frame, fg_color=COLORS["card_bg_dark"], corner_radius=6)
            row.pack(fill="x", pady=3)

            status_icon = "✅ Đã tải" if m["is_downloaded"] else "⚪ Chưa tải"
            status_color = COLORS["secondary"] if m["is_downloaded"] else "gray"

            left_box = ctk.CTkFrame(row, fg_color="transparent")
            left_box.pack(side="left", padx=10, pady=8)

            ctk.CTkLabel(left_box, text=m["name"], font=("Segoe UI", 11, "bold")).pack(anchor="w")
            ctk.CTkLabel(left_box, text=f"Repo: {m['repo']} • Dung lượng: {m['size_mb']} MB", font=FONTS["caption"], text_color="gray").pack(anchor="w")

            right_box = ctk.CTkFrame(row, fg_color="transparent")
            right_box.pack(side="right", padx=10)

            badge = ctk.CTkLabel(right_box, text=status_icon, font=FONTS["caption"], text_color=status_color)
            badge.pack(side="left", padx=8)

            btn_dl = ctk.CTkButton(
                right_box,
                text="⬇️ Tải lại / Nạp" if m["is_downloaded"] else "⬇️ Tải trước",
                width=100,
                height=24,
                font=FONTS["caption"],
                command=lambda k=key: self._predownload_model(k)
            )
            btn_dl.pack(side="left")

    def _predownload_model(self, model_key: str):
        mode_map = {"v3_nano": "v3nano", "v3_turbo": "v3turbo"}
        mode = mode_map.get(model_key, "v3turbo")

        self.download_progress.update(10.0, message=f"Bắt đầu nạp mô hình {model_key}...", stage="Download")
        self.cache_log_box.show_loading(
            title=f"Đang nạp mô hình: {model_key}",
            message="Đang kết nối Hugging Face Hub và chuẩn bị tải trọng số tệp ONNX..."
        )
        self.cache_log_box.append_log(f"Model: {model_key} | Khởi động luồng tải ngầm...")
        AppLogger.info(f"Bắt đầu tải trước mô hình {model_key} từ Hugging Face...", source="ModelCache")

        def _worker():
            try:
                from vieneu import Vieneu
                self.download_progress.update(40.0, message="Đang tải tệp ONNX và cấu hình...", stage="Download")
                UIDispatcher.post(self.cache_log_box.append_log, "Đang tải các file ONNX & tokenizer...")
                _ = Vieneu(mode=mode)
                self.download_progress.complete(f"Tải thành công {model_key}!")
                AppLogger.success(f"Tải thành công mô hình {model_key}!", source="ModelCache")
                UIDispatcher.post(
                    self.cache_log_box.show_success,
                    "Tải mô hình hoàn tất",
                    f"✅ Mô hình '{model_key}' đã được lưu trong bộ nhớ đệm máy tính!",
                    "Đã lưu tại cache directory. Bây giờ bạn có thể chọn cấu hình tương ứng ở Mục 2."
                )
                self.after(500, self._refresh_model_cache_info)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self.download_progress.error(f"Lỗi tải: {e}")
                AppLogger.exception(f"Lỗi khi tải mô hình {model_key}", exc=e, source="ModelCache")
                UIDispatcher.post(
                    self.cache_log_box.show_error,
                    f"Lỗi tải mô hình {model_key}",
                    str(e),
                    tb,
                    "Vui lòng kiểm tra lại kết nối mạng Internet hoặc proxy của bạn."
                )

        threading.Thread(target=_worker, daemon=True).start()

    def _open_cache_folder(self):
        cache_dir = os.path.expanduser(r"~/.cache/huggingface/hub")
        os.makedirs(cache_dir, exist_ok=True)
        AppLogger.info(f"Mở thư mục Cache: {cache_dir}", source="Settings")
        subprocess.Popen(f'explorer "{os.path.abspath(cache_dir)}"')

    def _browse_install_folder(self):
        initial = self.install_folder_var.get()
        if not initial or not os.path.isdir(initial):
            initial = os.path.abspath(sys.prefix)
        chosen = filedialog.askdirectory(
            initialdir=initial,
            title="Chọn thư mục cài đặt / Thư mục môi trường (Folder cài)"
        )
        if chosen:
            clean_path = os.path.normpath(chosen)
            self.install_folder_var.set(clean_path)
            AppLogger.info(f"Đã chỉ định Folder cài đặt: {clean_path}", source="Settings")

    def _show_sec2_cuda_card(self):
        if self.sec2_cuda_card.winfo_manager() == "pack":
            return
        if self.engine_log_box.winfo_manager() == "pack":
            self.sec2_cuda_card.pack(fill="x", padx=14, pady=(0, 10), before=self.engine_log_box)
        else:
            self.sec2_cuda_card.pack(fill="x", padx=14, pady=(0, 10))

    def _hide_sec2_cuda_card(self):
        if self.sec2_cuda_card.winfo_manager() == "pack":
            self.sec2_cuda_card.pack_forget()

    def _browse_output_folder(self):
        """Mở hộp thoại chọn thư mục lưu trữ file âm thanh."""
        chosen = filedialog.askdirectory(
            initialdir=self.output_dir_var.get(),
            title="Chọn thư mục lưu tệp âm thanh xuất ra"
        )
        if chosen:
            clean_path = os.path.normpath(chosen)
            self.output_dir_var.set(clean_path)
            AppLogger.info(f"Đã chọn thư mục lưu âm thanh: {clean_path}", source="Settings")

    def _open_output_folder(self):
        """Mở thư mục lưu âm thanh trong Windows File Explorer."""
        folder = self.output_dir_var.get().strip()
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
        try:
            os.startfile(folder)
            AppLogger.info(f"Đã mở thư mục âm thanh trong File Explorer: {folder}", source="Settings")
        except Exception as e:
            AppLogger.error(f"Không thể mở thư mục '{folder}': {e}", source="Settings")

    def _on_theme_select(self, new_theme: str):
        """Khi người dùng đổi giao diện trong menu Settings."""
        self.theme_var.set(new_theme)
        ctk.set_appearance_mode(new_theme)

    def _save_configuration(self):
        """Lưu vĩnh viễn các tùy chọn của người dùng vào user_settings.json."""
        chosen_profile_name = self.profile_menu.get()
        profile_key = self._profiles_map.get(chosen_profile_name, DEFAULT_PROFILE_KEY)
        precision_str = "int8" if "int8" in self.precision_menu.get() else "fp32"
        auto_load = self.auto_load_var.get()
        output_dir = self.output_dir_var.get().strip()
        auto_play = self.auto_play_var.get()
        default_voice = self.default_voice_menu.get()
        theme_mode = self.theme_var.get()
        clip_trigger = self.realtime_clip_var.get()

        jitter_str = self.jitter_menu.get()
        prebuf = 2
        if "1" in jitter_str:
            prebuf = 1
        elif "3" in jitter_str:
            prebuf = 3

        settings_to_save = {
            "default_profile": profile_key,
            "precision": precision_str,
            "auto_load_on_startup": auto_load,
            "audio_output_dir": output_dir,
            "auto_play_audio": auto_play,
            "default_voice": default_voice,
            "appearance_mode": theme_mode,
            "realtime_clipboard_trigger": clip_trigger,
            "realtime_prebuffer_chunks": prebuf,
        }

        # 1. Ghi vào ConfigManager & file JSON
        success = self.config_manager.save(settings_to_save)

        # 2. Cập nhật các service tại chỗ
        self.tts_engine.set_output_dir(output_dir)
        ctk.set_appearance_mode(theme_mode)

        if self.on_config_saved:
            self.on_config_saved(settings_to_save)

        # 3. Hiển thị thông báo trực quan
        if success:
            self.engine_log_box.show_success(
                title="Đã lưu cấu hình thành công",
                message="💾 Toàn bộ thiết lập đã được lưu vào 'user_settings.json'.",
                details=(
                    f"• Cấu hình khởi động: {chosen_profile_name}\n"
                    f"• Thư mục lưu audio: {output_dir}\n"
                    f"• Giọng đọc mặc định: {default_voice}\n"
                    f"• Tự động nạp khi mở app: {'Bật' if auto_load else 'Tắt'}\n"
                    f"• Tự động phát sau khi tạo: {'Bật' if auto_play else 'Tắt'}\n"
                    f"• Giao diện hiển thị: {theme_mode}\n"
                    f"• Realtime Jitter-Buffer: {prebuf} chunks"
                )
            )
            AppLogger.success("Đã lưu cấu hình người dùng vào user_settings.json thành công.", source="Settings")
        else:
            self.engine_log_box.show_error(
                title="Lỗi lưu cấu hình",
                message="Không thể ghi vào tệp user_settings.json. Vui lòng kiểm tra lại quyền truy cập thư mục."
            )

    def _reset_configuration(self):
        """Khôi phục cấu hình về mặc định xuất xưởng."""
        defaults = self.config_manager.reset_defaults()
        default_prof_name = PROFILES[DEFAULT_PROFILE_KEY]["name"]
        self.profile_menu.set(default_prof_name)
        self._on_profile_select(default_prof_name)
        self.precision_menu.set("fp32 (Chất lượng tối đa)")
        self.auto_load_var.set(True)
        self.output_dir_var.set(str(OUTPUTS_DIR))
        self.auto_play_var.set(True)
        self.default_voice_menu.set(DEFAULT_VOICE)
        self.theme_var.set("Dark")
        self.theme_menu_setting.set("Dark")
        ctk.set_appearance_mode("Dark")
        self.realtime_clip_var.set(False)
        self.jitter_menu.set("2 chunks (Cân bằng - Khuyên dùng)")

        self.tts_engine.set_output_dir(str(OUTPUTS_DIR))

        if self.on_config_saved:
            self.on_config_saved(defaults)

        self.engine_log_box.show_success(
            title="Đã khôi phục cài đặt gốc",
            message="Toàn bộ thông số đã được đưa về cấu hình chuẩn ban đầu.",
            details=f"Mô hình: {default_prof_name} | Thư mục: {OUTPUTS_DIR} | Giọng: {DEFAULT_VOICE}"
        )
        AppLogger.info("Đã khôi phục cấu hình mặc định ban đầu.", source="Settings")

    def _on_profile_select(self, chosen_name: str):
        profile_key = self._profiles_map.get(chosen_name, DEFAULT_PROFILE_KEY)
        self.profile_desc_label.configure(text=PROFILES[profile_key]["description"])
        AppLogger.info(f"Đã chọn cấu hình: {chosen_name}", source="Settings")

        # Tự động hiển thị khung cài đặt trực tiếp tại Mục 2 nếu chọn GPU mà chưa có CUDA
        hw = HardwareService.get_hardware_info()
        if "cuda" in profile_key.lower() and not hw.get("cuda_available"):
            self._show_sec2_cuda_card()
        else:
            self._hide_sec2_cuda_card()

    def _apply_engine_config(self):
        if self.tts_engine.is_loading():
            warn = "Hệ thống đang tải một mô hình khác trong nền. Vui lòng đợi hoàn tất trước khi thay đổi cấu hình!"
            AppLogger.warning(warn, source="Settings")
            self.engine_log_box.show_warning(
                title="Đang bận nạp mô hình",
                message=warn,
                suggestion="Vui lòng chờ thanh tiến trình nạp hoàn thành 100% rồi bấm áp dụng lại."
            )
            return

        chosen_name = self.profile_menu.get()
        profile_key = self._profiles_map.get(chosen_name, DEFAULT_PROFILE_KEY)

        # TỰ ĐỘNG HÓA 100%: Nếu cấu hình yêu cầu CUDA nhưng máy chưa có PyTorch CUDA
        hw = HardwareService.get_hardware_info()
        if "cuda" in profile_key.lower() and not hw.get("cuda_available"):
            AppLogger.info("Cấu hình GPU được chọn nhưng chưa có PyTorch CUDA. Tự động chuyển sang quy trình tải & cài đặt...", source="Settings")
            self._show_sec2_cuda_card()
            self._start_cuda_installation(source_section=2)
            return

        self.btn_apply_config.configure(state="disabled", text="⏳ Đang nạp lại Engine...")
        self.engine_log_box.show_loading(
            title="Đang nạp cấu hình Engine",
            message=f"Đang khởi tạo cấu hình: {chosen_name}..."
        )
        self.engine_log_box.append_log(f"Profile: {profile_key} | Đang nạp trọng số mạng...")
        AppLogger.info(f"Áp dụng cấu hình mới: {profile_key}", source="Settings")

        self.tts_engine.load_model_async(
            profile_key,
            on_complete=lambda: UIDispatcher.post(self._on_engine_reloaded),
            on_error=lambda err_msg, exc: UIDispatcher.post(self._on_engine_reload_error, err_msg, exc, profile_key)
        )

    def _on_engine_reloaded(self):
        self.btn_apply_config.configure(state="normal", text="🔄 Áp dụng cấu hình & Nạp lại Engine")
        chosen_name = self.profile_menu.get()
        profile_key = self._profiles_map.get(chosen_name, DEFAULT_PROFILE_KEY)
        self.engine_log_box.show_success(
            title="Cấu hình Engine đã sẵn sàng",
            message=f"✅ Đã nạp thành công mô hình với cấu hình '{chosen_name}'!",
            details="Hệ thống đã sẵn sàng tổng hợp giọng nói tiếng Việt."
        )
        if self.on_profile_reloaded:
            self.on_profile_reloaded(profile_key)
        self._refresh_model_cache_info()

    def _on_engine_reload_error(self, err_msg: str, exc: Optional[BaseException], profile_key: str):
        self.btn_apply_config.configure(state="normal", text="🔄 Áp dụng cấu hình & Nạp lại Engine")
        import traceback
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else None

        err_lower = (err_msg + " " + (str(exc) or "")).lower()
        if "cuda" in profile_key.lower() or "cuda" in err_lower or "torch" in err_lower:
            # Hiển thị ngay khung cài đặt trực tiếp tại Mục 2
            self._show_sec2_cuda_card()
            suggestion = "Môi trường hiện tại chưa có PyTorch CUDA. Hãy kiểm tra 'Folder cài' ở khung ngay bên trên và bấm nút '🚀 Bắt đầu cài đặt PyTorch CUDA vào Folder này' để cài trực tiếp, hoặc chuyển sang cấu hình CPU (fp32 hoặc int8) để sử dụng ngay."
        elif "connection" in err_lower or "timeout" in err_lower or "huggingface" in err_lower:
            suggestion = "Không thể kết nối đến máy chủ Hugging Face. Vui lòng kiểm tra lại kết nối mạng Internet của bạn."
        else:
            suggestion = "Vui lòng thử chọn cấu hình Tiêu chuẩn CPU (fp32) hoặc khởi động lại ứng dụng."

        self.engine_log_box.show_error(
            title="Lỗi nạp cấu hình Engine",
            message=f"Không thể khởi chạy cấu hình: {err_msg}",
            traceback_str=tb_str,
            suggestion=suggestion
        )

    def _install_cuda_click(self):
        self._start_cuda_installation(source_section=1)

    def _install_cuda_sec2_click(self):
        self._start_cuda_installation(source_section=2)

    def _start_cuda_installation(self, source_section: int = 1):
        target_folder = self.install_folder_var.get().strip()
        if not target_folder:
            target_folder = os.path.abspath(sys.prefix)
            self.install_folder_var.set(target_folder)

        os.makedirs(target_folder, exist_ok=True)

        self.btn_install_cuda.configure(state="disabled", text="⏳ Đang cài đặt PyTorch CUDA...")
        self.btn_install_cuda_sec2.configure(state="disabled", text="⏳ Đang cài đặt PyTorch CUDA...")

        if source_section == 2:
            progress_tracker = self.sec2_cuda_progress
            log_box = self.engine_log_box
        else:
            progress_tracker = self.cuda_progress
            log_box = self.cuda_log_box

        progress_tracker.update(5.0, message="Khởi tạo quá trình cài đặt PyTorch CUDA...", stage="CUDA")
        log_box.show_loading(
            title="Đang cài đặt PyTorch CUDA cho GPU",
            message=f"Đang chuẩn bị cài đặt vào Folder: {target_folder}..."
        )
        log_box.append_log(f"Folder cài chỉ định: {target_folder}")
        AppLogger.info(f"Bắt đầu cài đặt PyTorch CUDA vào Folder: {target_folder}", source="CUDA_Installer")

        def _install_worker():
            scripts_py = os.path.join(target_folder, "Scripts", "python.exe")
            bin_py = os.path.join(target_folder, "bin", "python")
            python_exe = scripts_py if os.path.exists(scripts_py) else (bin_py if os.path.exists(bin_py) else None)

            if python_exe:
                target_opt = f'--python "{python_exe}"'
            elif os.path.exists(os.path.join(target_folder, "pyvenv.cfg")) or os.path.abspath(target_folder) == os.path.abspath(sys.prefix):
                target_opt = f'--python "{target_folder}"'
            else:
                target_opt = f'--target "{target_folder}"'

            commands = [
                f'uv pip install {target_opt} torch torchaudio --index-url https://download.pytorch.org/whl/cu128',
                f'uv pip install {target_opt} "transformers==4.57.6"'
            ]

            try:
                progress_tracker.update(15.0, message="Đang tải và cài đặt Torch & Torchaudio CUDA (~2.5GB)...", stage="CUDA")
                for cmd in commands:
                    UIDispatcher.post(log_box.append_log, f"Chạy: {cmd[:65]}...")
                    proc = subprocess.Popen(
                        cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    for line in proc.stdout:
                        clean_l = line.strip()
                        if clean_l:
                            AppLogger.info(clean_l, source="CUDA_Installer")
                            UIDispatcher.post(log_box.append_log, clean_l)
                            if "Downloading" in clean_l:
                                progress_tracker.step(1.5, message=clean_l[:50])
                            elif "Installed" in clean_l:
                                progress_tracker.step(5.0, message=clean_l[:50])

                    proc.wait()
                    if proc.returncode != 0:
                        err = f"Lệnh thoát với mã lỗi: {proc.returncode}"
                        progress_tracker.error(err)
                        AppLogger.error(err, source="CUDA_Installer")
                        UIDispatcher.post(self._on_cuda_install_done, False, err, source_section)
                        return

                if target_folder not in sys.path:
                    sys.path.insert(0, target_folder)
                sp = os.path.join(target_folder, "Lib", "site-packages")
                if os.path.isdir(sp) and sp not in sys.path:
                    sys.path.insert(0, sp)

                progress_tracker.complete("Cài đặt PyTorch CUDA hoàn tất!")
                AppLogger.success("Cài đặt PyTorch CUDA hoàn tất!", source="CUDA_Installer")
                UIDispatcher.post(self._on_cuda_install_done, True, "", source_section)
            except Exception as e:
                progress_tracker.error(str(e))
                AppLogger.exception("Lỗi trong quá trình cài đặt CUDA", exc=e, source="CUDA_Installer")
                UIDispatcher.post(self._on_cuda_install_done, False, str(e), source_section)

        threading.Thread(target=_install_worker, daemon=True).start()

    def _on_cuda_install_done(self, success: bool, error: str = "", source_section: int = 1):
        self.btn_install_cuda.configure(state="normal", text="🚀 Bắt đầu cài đặt PyTorch CUDA cho GPU (Tự động)")
        self.btn_install_cuda_sec2.configure(state="normal", text="🚀 Bắt đầu cài đặt PyTorch CUDA vào Folder này")

        if success:
            self.cuda_status_badge.configure(text="✅ PyTorch CUDA: ĐÃ SẴN SÀNG (GPU Acceleration)", text_color=COLORS["secondary"])
            self._refresh_hardware_info()
            self.sec2_cuda_card.pack_forget()

            if source_section == 2:
                self.engine_log_box.show_success(
                    title="Cài đặt PyTorch CUDA thành công",
                    message="✅ Đã hoàn tất cài đặt PyTorch CUDA vào Folder!",
                    details="Đang tự động áp dụng cấu hình và nạp lại Engine GPU..."
                )
                self.after(600, self._apply_engine_config)
            else:
                self.cuda_log_box.show_success(
                    title="Cài đặt PyTorch CUDA thành công",
                    message="Đã hoàn tất cài đặt PyTorch CUDA! Bạn có thể chọn cấu hình 'GPU NVIDIA - PyTorch (CUDA)' ở Mục 2."
                )
        else:
            self.cuda_status_badge.configure(text=f"❌ Cài đặt thất bại: {error}", text_color=COLORS["danger"])
            target_log_box = self.engine_log_box if source_section == 2 else self.cuda_log_box
            target_log_box.show_error(
                title="Cài đặt PyTorch CUDA thất bại",
                message=f"Quá trình tải hoặc cài đặt gặp sự cố: {error}",
                suggestion=f"Hãy kiểm tra kết nối mạng hoặc thử chạy lệnh trong Terminal: uv pip install --python \"{self.install_folder_var.get()}\" torch torchaudio --index-url https://download.pytorch.org/whl/cu128"
            )

    def _start_benchmark_click(self):
        if not self.tts_engine.is_ready():
            err = "Mô hình TTS chưa sẵn sàng hoặc đang gặp lỗi. Vui lòng nạp mô hình ở Mục 2 trước khi chạy benchmark!"
            AppLogger.warning(err, source="Benchmark")
            self.bench_progress.error(err)
            self.bench_log_box.show_error(
                title="Chưa thể chạy Benchmark",
                message=err,
                suggestion="Hãy chọn cấu hình CPU tại Mục 2 và bấm 'Áp dụng cấu hình & Nạp lại Engine' trước."
            )
            return

        self.btn_run_benchmark.configure(state="disabled", text="⏳ Đang đo...")
        self.bench_progress.update(10.0, message="Bắt đầu chạy benchmark...", stage="Benchmark")
        self.bench_log_box.show_loading(
            title="Đang thực hiện Benchmark",
            message="Chuẩn bị câu thử nghiệm mẫu và gửi vào mô hình AI..."
        )
        self.bench_log_box.append_log("Đang tổng hợp câu mẫu 15 từ...")

        def _bench_worker():
            res = HardwareService.run_benchmark(self.tts_engine, progress_tracker=self.bench_progress)
            UIDispatcher.post(self._on_benchmark_finish, res)

        threading.Thread(target=_bench_worker, daemon=True).start()

    def _on_benchmark_finish(self, res: dict):
        self.btn_run_benchmark.configure(state="normal", text="🚀 Bắt đầu Benchmark")
        if not res.get("success"):
            self.bench_log_box.show_error(
                title="Benchmark thất bại",
                message=res.get("error", "Lỗi không xác định"),
                suggestion="Kiểm tra lại trạng thái của Engine tại Mục 2."
            )
            return

        self.bench_log_box.show_success(
            title="Benchmark hoàn tất",
            message=f"Đạt {res['speed_multiplier']}x real-time (RTF: {res['rtf']}) • Đánh giá: {res['rating']}",
            details=f"Thời gian xử lý: {res['process_time']}s | Độ dài audio: {res['duration']}s"
        )

        result_text = (
            f"🏆 Đánh giá: {res['rating']}  ({res['speed_multiplier']}x real-time)\n"
            f"⏱️ Thời gian xử lý: {res['process_time']}s  •  🎵 Độ dài âm thanh: {res['duration']}s\n"
            f"📊 Chỉ số RTF: {res['rtf']} (Càng nhỏ càng nhanh)  •  Tần số: {res['sample_rate']} Hz\n"
            f"⚙️ Chế độ đang chạy: {res['backend']}"
        )
        self.bench_result_text.configure(text=result_text)
        self.bench_results_card.pack(fill="x", padx=14, pady=(4, 12))
