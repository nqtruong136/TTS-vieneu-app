"""
Main Application Window for VieNeu-TTS Studio.
Coordinates NavRail (Left Sidebar) and the 4 Main Views:
- PresetView (Giọng có sẵn)
- CloneVoiceView (Clone Voice)
- SettingsView (Cài đặt, CPU/GPU Readiness, Benchmark, Model Cache)
- HistoryView (Các giọng đã tạo)
Integrated with AppLogger and ProgressTracker across the entire application.
"""
from typing import Optional, Dict, Any
import customtkinter as ctk

from ..config import (
    APP_TITLE, APP_GEOMETRY, APP_MINSIZE,
    DEFAULT_PROFILE_KEY, DEFAULT_VOICE
)
from ..core.tts_engine import TTSEngine
from ..core.audio_player import AudioPlayer
from ..core.logger import AppLogger
from ..core.progress import ProgressTracker
from ..database.history_manager import HistoryManager
from .components.nav_rail import NavRail
from .components.log_console import LogConsole
from .dispatcher import UIDispatcher
from .views.preset_view import PresetView
from .views.clone_view import CloneVoiceView
from .views.realtime_view import RealtimeView
from .views.settings_view import SettingsView
from .views.history_view import HistoryView


class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Khởi tạo cửa sổ
        self.title(APP_TITLE)
        self.geometry(APP_GEOMETRY)
        self.minsize(*APP_MINSIZE)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # 2. Khởi tạo Core Services & Database
        self.audio_player = AudioPlayer()
        self.history_manager = HistoryManager()
        self.tts_engine = TTSEngine(on_status_change=self._on_engine_status_change)
        self._log_window: Optional[ctk.CTkToplevel] = None

        AppLogger.info("Khởi động ứng dụng VieNeu-TTS Studio...", source="App")

        # 3. Setup Layout
        self._setup_layout()
        self._bind_shortcuts()
        self._poll_ui_dispatcher()

        # 4. Hiển thị view mặc định (Preset Voices)
        self._switch_view("preset")

        # 5. Tải mô hình ngầm ngay khi app mở
        self.after(300, self._initial_model_load)

    def _poll_ui_dispatcher(self):
        UIDispatcher.process_pending()
        self.after(20, self._poll_ui_dispatcher)

    def update(self):
        UIDispatcher.process_pending()
        super().update()

    def _setup_layout(self):
        # Cột 0: NavRail (Width cố định ~195px)
        # Cột 1: View Container (Expand toàn bộ phần còn lại)
        self.grid_columnconfigure(0, weight=0, minsize=195)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Nav Rail (Bên trái ngoài cùng)
        self.nav_rail = NavRail(
            self,
            on_nav_change=self._switch_view,
            on_open_log=self._open_log_popup
        )
        self.nav_rail.grid(row=0, column=0, sticky="nsew")

        # 2. Main View Container
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Khởi tạo các Views
        self.views: Dict[str, ctk.CTkFrame] = {}

        # View 1: Giọng có sẵn
        self.preset_view = PresetView(
            self.content_container,
            audio_player=self.audio_player,
            on_generate_request=self._handle_preset_generate,
            progress_tracker=self.tts_engine.progress
        )
        self.views["preset"] = self.preset_view

        # View 2: Clone Voice
        self.clone_view = CloneVoiceView(
            self.content_container,
            audio_player=self.audio_player,
            on_clone_request=self._handle_clone_generate,
            progress_tracker=self.tts_engine.progress
        )
        self.views["clone"] = self.clone_view

        # View 3: Realtime Streaming Reader (Tự động đọc khi Copy Clipboard & Quick History)
        self.realtime_view = RealtimeView(
            self.content_container,
            tts_engine=self.tts_engine
        )
        self.views["realtime"] = self.realtime_view

        # View 4: Settings & Diagnostics (Có kèm Live Log Console và các Progress Bars)
        self.settings_view = SettingsView(
            self.content_container,
            tts_engine=self.tts_engine,
            on_profile_reloaded=self._on_profile_reloaded
        )
        self.views["settings"] = self.settings_view

        # View 4: History View (Các giọng đã tạo kèm phân trang & YouTube Scrubber)
        self.history_view = HistoryView(
            self.content_container,
            history_manager=self.history_manager,
            audio_player=self.audio_player,
            on_load_text_request=self._handle_history_load_text
        )
        self.views["history"] = self.history_view

    def _open_log_popup(self):
        """Mở cửa sổ Log Console độc lập nổi lên trên."""
        if self._log_window is None or not self._log_window.winfo_exists():
            self._log_window = ctk.CTkToplevel(self)
            self._log_window.title("📜 VieNeu-TTS Studio - Log Console")
            self._log_window.geometry("800x480")
            self._log_window.minsize(600, 350)
            
            console = LogConsole(self._log_window)
            console.pack(fill="both", expand=True, padx=12, pady=12)
            AppLogger.info("Đã mở cửa sổ Log Console độc lập.", source="App")
        else:
            self._log_window.focus()

    def _switch_view(self, view_key: str):
        # Ẩn tất cả views
        for key, view in self.views.items():
            view.grid_forget()

        # Hiển thị view được chọn
        if view_key in self.views:
            target_view = self.views[view_key]
            target_view.grid(row=0, column=0, sticky="nsew")

            if view_key == "history":
                self.history_view.refresh_data()
            elif view_key == "settings":
                self.settings_view._refresh_all()

    def _bind_shortcuts(self):
        # Ctrl + Enter để bắt đầu sinh giọng nói nhanh
        self.bind("<Control-Return>", lambda event: self._trigger_current_generate())

    def _trigger_current_generate(self):
        curr = self.nav_rail.current_view
        if curr == "preset":
            self.preset_view.editor_panel._handle_generate_click()
        elif curr == "clone":
            self.clone_view.editor_panel._handle_generate_click()

    def _initial_model_load(self):
        self.tts_engine.load_model_async(DEFAULT_PROFILE_KEY)

    def _on_profile_reloaded(self, profile_key: str):
        self._on_engine_status_change(f"✅ Đã đổi sang cấu hình: {profile_key}", is_ready=True, is_loading=False, error=None)

    def _on_engine_status_change(self, message: str, is_ready: bool, is_loading: bool, error: Optional[str]):
        UIDispatcher.post(self._update_ui_status, message, is_ready, is_loading, error)

    def _update_ui_status(self, message: str, is_ready: bool, is_loading: bool, error: Optional[str]):
        self.nav_rail.set_engine_status(is_ready, is_loading, error)
        is_error = error is not None
        self.preset_view.editor_panel.set_status(message, is_error=is_error)
        self.clone_view.editor_panel.set_status(message, is_error=is_error)

    def _handle_preset_generate(self, text: str, voice_name: str):
        if not self.tts_engine.is_ready():
            warn = "Mô hình chưa sẵn sàng hoặc đang gặp sự cố nạp. Vui lòng kiểm tra Tab Cài đặt!"
            AppLogger.warning(warn, source="App")
            self.preset_view.editor_panel.action_log_box.show_warning(
                title="Mô hình chưa sẵn sàng",
                message=warn,
                suggestion="Hãy mở Tab 'Cài đặt & Máy' để kiểm tra cấu hình Engine hoặc chọn cấu hình CPU (fp32)."
            )
            return

        self.preset_view.editor_panel.set_generating_state(True)
        self.preset_view.editor_panel.action_log_box.show_loading(
            title="Đang tổng hợp giọng nói",
            message=f"Đang sinh giọng '{voice_name}' cho {len(text.strip())} ký tự văn bản..."
        )
        self.tts_engine.generate_speech_async(
            text=text,
            voice=voice_name,
            ref_audio=None,
            on_success=lambda res: UIDispatcher.post(self._on_preset_success, res),
            on_error=lambda err, exc=None: UIDispatcher.post(self._on_preset_error, err, exc),
            progress_tracker=self.tts_engine.progress
        )

    def _on_preset_success(self, result: Dict[str, Any]):
        self.preset_view.editor_panel.set_generating_state(False)

        # 1. Lưu SQLite
        self.history_manager.add_record(
            text=result["text"],
            voice_name=result["voice"],
            profile_name=result["profile_name"],
            audio_path=result["audio_path"],
            duration=result["duration"],
            process_time=result["process_time"],
            rtf=result["rtf"]
        )

        # 2. Cập nhật player và phát audio
        self.preset_view.player_bar.set_audio_result(result)

        # 3. In log trạng thái thành công tại chỗ trigger
        self.preset_view.editor_panel.action_log_box.show_success(
            title="Tổng hợp thành công",
            message=f"Đã tạo giọng '{result['voice']}' ({result['duration']:.1f}s) trong {result['process_time']:.2f}s (RTF: {result['rtf']:.2f})",
            details=f"Audio đã lưu tại: {os.path.basename(result['audio_path'])}"
        )

    def _on_preset_error(self, error_msg: str, exc: Optional[BaseException] = None):
        self.preset_view.editor_panel.set_generating_state(False)
        self.preset_view.editor_panel.set_status(f"❌ Lỗi: {error_msg}", is_error=True)
        import traceback
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else None
        self.preset_view.editor_panel.action_log_box.show_error(
            title="Không thể tổng hợp giọng nói",
            message=error_msg,
            traceback_str=tb_str,
            suggestion="Kiểm tra cấu hình mô hình ở Tab Cài đặt hoặc thử với đoạn văn bản ngắn hơn."
        )

    
    def _handle_clone_generate(self, text: str, ref_audio_path: str, denoise: bool = True, clean_timbre: bool = True):
        if not self.tts_engine.is_ready():
            warn = "Mô hình chưa sẵn sàng hoặc đang gặp sự cố nạp. Vui lòng kiểm tra Tab Cài đặt!"
            AppLogger.warning(warn, source="App")
            self.clone_view.editor_panel.action_log_box.show_warning(
                title="Mô hình chưa sẵn sàng",
                message=warn,
                suggestion="Hãy mở Tab 'Cài đặt & Máy' để kiểm tra cấu hình Engine hoặc chọn cấu hình CPU (fp32)."
            )
            return

        self.clone_view.editor_panel.set_generating_state(True)
        mode_desc = "trong trẻo (lọc vang & dội phòng)" if clean_timbre else "sao chép đầy đủ âm sắc mẫu"
        self.clone_view.editor_panel.action_log_box.show_loading(
            title="Đang nhân bản giọng nói (Cloning)",
            message=f"Đang trích xuất đặc trưng giọng [{mode_desc}] và tổng hợp câu đọc mới (48kHz)..."
        )
        use_ref_codes = not clean_timbre
        self.tts_engine.generate_speech_async(
            text=text,
            voice=DEFAULT_VOICE,
            ref_audio=ref_audio_path,
            denoise=denoise,
            use_ref_codes=use_ref_codes,
            on_success=lambda res: UIDispatcher.post(self._on_clone_success, res),
            on_error=lambda err, exc=None: UIDispatcher.post(self._on_clone_error, err, exc),
            progress_tracker=self.tts_engine.progress
        )

    def _on_clone_success(self, result: Dict[str, Any]):
        self.clone_view.editor_panel.set_generating_state(False)

        # 1. Lưu SQLite
        self.history_manager.add_record(
            text=result["text"],
            voice_name=result["voice"],
            profile_name=result["profile_name"],
            audio_path=result["audio_path"],
            duration=result["duration"],
            process_time=result["process_time"],
            rtf=result["rtf"]
        )

        # 2. Cập nhật player clone
        self.clone_view.player_bar.set_audio_result(result)

        # 3. In log trạng thái thành công tại chỗ trigger
        self.clone_view.editor_panel.action_log_box.show_success(
            title="Nhân bản giọng nói thành công",
            message=f"Đã sao chép âm sắc ({result['duration']:.1f}s) trong {result['process_time']:.2f}s (RTF: {result['rtf']:.2f})",
            details=f"Audio đã lưu tại: {os.path.basename(result['audio_path'])}"
        )

    def _on_clone_error(self, error_msg: str, exc: Optional[BaseException] = None):
        self.clone_view.editor_panel.set_generating_state(False)
        self.clone_view.editor_panel.set_status(f"❌ Lỗi: {error_msg}", is_error=True)
        import traceback
        tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)) if exc else None
        self.clone_view.editor_panel.action_log_box.show_error(
            title="Không thể nhân bản giọng nói",
            message=error_msg,
            traceback_str=tb_str,
            suggestion="Hãy kiểm tra lại tệp âm thanh mẫu (đảm bảo độ dài 3-8 giây, rõ tiếng, không chứa tạp âm quá lớn)."
        )

    def _handle_history_load_text(self, text: str):
        self.preset_view.editor_panel.set_text(text)
        self._switch_view("preset")
        self.nav_rail._handle_click("preset")
        self.preset_view.editor_panel.set_status("📋 Đã nạp lại văn bản từ lịch sử.")
        AppLogger.info("Đã nạp văn bản từ lịch sử vào ô soạn thảo.", source="App")

    def on_closing(self):
        try:
            self.audio_player.stop()
        except Exception:
            pass
        AppLogger.info("Đang thoát ứng dụng...", source="App")
        self.destroy()
