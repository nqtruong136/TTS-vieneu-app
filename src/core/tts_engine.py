"""
TTS Engine Service wrapping the VieNeu SDK.
Integrated with AppLogger for exception tracking and ProgressTracker for percentage reporting.
"""
import os
import sys
import io
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Dict, Any

# Tắt terminal progress bar của Hugging Face / tqdm để tránh lỗi 'NoneType' write trên Windows pythonw
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = sys.stdout
if getattr(sys, "__stdout__", None) is None:
    sys.__stdout__ = sys.stdout
if getattr(sys, "__stderr__", None) is None:
    sys.__stderr__ = sys.stderr

import soundfile as sf
from vieneu import Vieneu

from ..config import OUTPUTS_DIR, PROFILES, DEFAULT_PROFILE_KEY, DEFAULT_VOICE
from .logger import AppLogger
from .progress import ProgressTracker


class TTSEngine:
    def __init__(
        self,
        on_status_change: Optional[Callable[[str, bool, bool, Optional[str]], None]] = None,
        output_dir: Optional[str] = None
    ):
        self._engine = None
        self._current_profile_key = None
        self._current_config = None
        self._lock = threading.Lock()
        self._is_loading = False
        self._is_ready = False
        self._on_status_change = on_status_change
        self.output_dir = Path(output_dir) if output_dir else OUTPUTS_DIR
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Global progress tracker cho Engine
        self.progress = ProgressTracker()

    def set_output_dir(self, path: str):
        """Thay đổi thư mục lưu trữ file âm thanh sinh ra."""
        try:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            self.output_dir = p
            AppLogger.info(f"Đã cập nhật thư mục lưu âm thanh: {p}", source="TTSEngine")
        except Exception as e:
            AppLogger.warning(f"Không thể tạo thư mục âm thanh '{path}': {e}", source="TTSEngine")

        self.progress = ProgressTracker()

    def notify_status(self, message: str, is_ready: bool = False, is_loading: bool = False, error: Optional[str] = None):
        if self._on_status_change:
            self._on_status_change(message, is_ready, is_loading, error)

    def is_ready(self) -> bool:
        return self._is_ready and self._engine is not None

    def is_loading(self) -> bool:
        return self._is_loading

    def load_model_async(
        self,
        profile_key: str = DEFAULT_PROFILE_KEY,
        on_complete: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str, Optional[BaseException]], None]] = None,
        progress_tracker: Optional[ProgressTracker] = None
    ):
        """Khởi chạy luồng nạp mô hình bất đồng bộ với tiến trình phần trăm và ghi log."""
        self._is_loading = True
        tracker = progress_tracker or self.progress
        thread = threading.Thread(
            target=self._load_model_worker,
            args=(profile_key, on_complete, on_error, tracker),
            daemon=True,
            name="VieNeu-ModelLoader"
        )
        thread.start()

    def _load_model_worker(
        self,
        profile_key: str,
        on_complete: Optional[Callable[[], None]],
        on_error: Optional[Callable[[str, Optional[BaseException]], None]],
        tracker: ProgressTracker
    ):
        with self._lock:
            try:
                if self._current_profile_key == profile_key and self._engine is not None:
                    AppLogger.info(f"Mô hình {profile_key} đã có sẵn trong bộ nhớ RAM.", source="TTSEngine")
                    tracker.complete("Mô hình đã sẵn sàng")
                    self.notify_status("✅ Mô hình đã sẵn sàng", is_ready=True, is_loading=False)
                    if on_complete:
                        on_complete()
                    return

                self._is_ready = False
                config = PROFILES.get(profile_key, PROFILES[DEFAULT_PROFILE_KEY])
                profile_name = config["name"]

                AppLogger.info(f"Bắt đầu khởi tạo mô hình: {profile_name}...", source="TTSEngine")
                tracker.update(15.0, message="Đang giải phóng tài nguyên cũ...", stage="Init")

                self.notify_status(
                    f"⏳ Đang tải mô hình ({profile_name}). Vui lòng chờ giây lát...",
                    is_ready=False,
                    is_loading=True
                )

                # Đóng engine cũ nếu có
                if self._engine is not None and hasattr(self._engine, "close"):
                    try:
                        self._engine.close()
                    except Exception as e:
                        AppLogger.warning(f"Lỗi đóng engine cũ: {e}", source="TTSEngine")
                    self._engine = None

                tracker.update(35.0, message="Kiểm tra bộ nhớ Cache Hugging Face...", stage="Cache")

                mode = config.get("mode", "v3turbo")
                backend = config.get("backend", "onnx")
                precision = config.get("precision", "fp32")
                device = config.get("device", "cpu")

                init_kwargs = {"mode": mode}
                if mode == "v3turbo":
                    init_kwargs["backend"] = backend
                    if backend == "onnx":
                        init_kwargs["precision"] = precision
                    init_kwargs["device"] = device

                tracker.update(60.0, message=f"Đang nạp trọng số mạng {backend.upper()} ({precision})...", stage="Loading")

                engine = Vieneu(**init_kwargs)
                self._engine = engine
                self._current_profile_key = profile_key
                self._current_config = config
                self._is_ready = True

                tracker.complete(f"Đã tải xong: {profile_name}")
                AppLogger.success(f"Nạp thành công mô hình: {profile_name} (Backend: {backend}, Device: {device})", source="TTSEngine")

                self.notify_status(
                    f"✅ Đã tải xong: {profile_name}",
                    is_ready=True,
                    is_loading=False
                )
                if on_complete:
                    on_complete()

            except Exception as e:
                self._is_ready = False
                error_msg = f"Lỗi tải mô hình {profile_name}: {str(e)}"
                AppLogger.exception(error_msg, exc=e, source="TTSEngine")
                tracker.error(f"Lỗi: {e}")
                self.notify_status(error_msg, is_ready=False, is_loading=False, error=str(e))
                if on_error:
                    on_error(error_msg, e)
            finally:
                self._is_loading = False

    def infer_stream(self, text: str, voice: str = DEFAULT_VOICE, **kwargs):
        """Trả về generator sinh từng chunk âm thanh theo thời gian thực (48kHz)."""
        if not self.is_ready():
            raise RuntimeError("Mô hình chưa sẵn sàng. Vui lòng nạp mô hình trước!")
        clean_text = text.strip()
        if not clean_text:
            return iter([])
        return self._engine.infer_stream(clean_text, voice=voice, **kwargs)

    def generate_speech_async(
        self,
        text: str,
        voice: str = DEFAULT_VOICE,
        ref_audio: Optional[str] = None,
        denoise: bool = True,
        use_ref_codes: bool = True,
        on_success: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[..., None]] = None,
        progress_tracker: Optional[ProgressTracker] = None,
    ):
        """Khởi chạy luồng sinh giọng nói với báo cáo tiến trình % và ghi log."""
        tracker = progress_tracker or self.progress
        thread = threading.Thread(
            target=self._generate_speech_worker,
            args=(text, voice, ref_audio, denoise, use_ref_codes, on_success, on_error, tracker),
            daemon=True,
            name="VieNeu-InferenceWorker"
        )
        thread.start()

    def _generate_speech_worker(
        self,
        text: str,
        voice: str,
        ref_audio: Optional[str],
        denoise: bool,
        use_ref_codes: bool,
        on_success: Optional[Callable[[Dict[str, Any]], None]],
        on_error: Optional[Callable[..., None]],
        tracker: ProgressTracker,
    ):
        def _dispatch_error(msg: str, exc: Optional[BaseException] = None):
            if not on_error:
                return
            try:
                import inspect
                sig = inspect.signature(on_error)
                if len(sig.parameters) >= 2:
                    on_error(msg, exc)
                else:
                    on_error(msg)
            except Exception:
                try:
                    on_error(msg)
                except Exception:
                    pass

        if not self.is_ready():
            err = "Mô hình chưa được nạp hoặc đang tải. Vui lòng chờ mô hình sẵn sàng!"
            AppLogger.warning(err, source="TTSEngine")
            tracker.error(err)
            _dispatch_error(err, None)
            return

        clean_text = text.strip()
        if not clean_text:
            err = "Văn bản nhập vào không được để trống!"
            AppLogger.warning(err, source="TTSEngine")
            tracker.error(err)
            _dispatch_error(err, None)
            return

        try:
            tracker.update(10.0, message="Đang tiền xử lý văn bản tiếng Việt...", stage="Preprocess")
            AppLogger.info(f"Bắt đầu tổng hợp giọng nói ({len(clean_text)} ký tự) | Giọng: {voice if not ref_audio else 'Clone'}", source="TTSEngine")

            self.notify_status("🔊 Đang tổng hợp giọng nói...", is_ready=True, is_loading=True)
            start_time = time.time()

            # Chuẩn bị tham số infer
            infer_kwargs = {"text": clean_text}
            if ref_audio and os.path.exists(ref_audio):
                tracker.update(25.0, message="Đang trích xuất speaker embedding từ clip mẫu...", stage="Cloning")
                AppLogger.info(f"Trích xuất âm sắc từ: {os.path.basename(ref_audio)} (Denoise={denoise}, use_ref_codes={use_ref_codes})", source="VoiceCloner")
                infer_kwargs["ref_audio"] = ref_audio
                infer_kwargs["denoise"] = denoise
                infer_kwargs["use_ref_codes"] = use_ref_codes
            else:
                infer_kwargs["voice"] = voice

            tracker.update(45.0, message="Mô hình AI đang suy luận âm thanh (48kHz)...", stage="Inference")

            # Gọi hàm infer của SDK
            audio = self._engine.infer(**infer_kwargs)
            process_time = time.time() - start_time

            tracker.update(85.0, message="Đang hậu xử lý và xuất file WAV...", stage="Postprocess")

            sample_rate = getattr(self._engine, "sample_rate", 48000)
            duration = len(audio) / sample_rate if sample_rate > 0 else 0.0
            rtf = process_time / duration if duration > 0 else 0.0

            # Tạo tên file lưu kết quả có timestamp
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_voice = voice.replace(" ", "_") if not ref_audio else "Cloned"
            filename = f"vieneu_{safe_voice}_{timestamp_str}.wav"
            out_path = str(self.output_dir / filename)

            # Lưu file âm thanh
            if hasattr(self._engine, "save"):
                self._engine.save(audio, out_path)
            else:
                sf.write(out_path, audio, sample_rate)

            tracker.complete(f"Đã hoàn thành! RTF: {rtf:.3f} ({duration:.1f}s)")
            AppLogger.success(
                f"Tổng hợp thành công! Thời gian: {process_time:.2f}s | Độ dài audio: {duration:.2f}s | RTF: {rtf:.3f} | File: {filename}",
                source="TTSEngine"
            )

            result = {
                "audio_path": out_path,
                "duration": duration,
                "process_time": process_time,
                "rtf": rtf,
                "sample_rate": sample_rate,
                "text": clean_text,
                "voice": voice if not ref_audio else f"Clone ({os.path.basename(ref_audio)})",
                "profile_name": self._current_config["name"] if self._current_config else "Default",
            }

            self.notify_status(
                f"🎉 Hoàn thành trong {process_time:.2f}s (RTF: {rtf:.2f})",
                is_ready=True,
                is_loading=False
            )

            if on_success:
                on_success(result)

        except Exception as e:
            error_str = f"Lỗi trong quá trình sinh âm thanh: {str(e)}"
            AppLogger.exception(error_str, exc=e, source="TTSEngine")
            tracker.error(f"Lỗi: {e}")
            self.notify_status(error_str, is_ready=True, is_loading=False, error=str(e))
            _dispatch_error(error_str, e)
