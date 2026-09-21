"""
Persistent configuration manager for VieNeu-TTS Studio.
Manages user preferences stored in user_settings.json.
"""
import os
import json
import threading
from pathlib import Path
from typing import Dict, Any

from ..config import BASE_DIR, OUTPUTS_DIR, DEFAULT_PROFILE_KEY, DEFAULT_VOICE


DEFAULT_SETTINGS: Dict[str, Any] = {
    # Cấu hình Engine khởi động
    "default_profile": DEFAULT_PROFILE_KEY,
    "precision": "fp32",
    "auto_load_on_startup": True,

    # Giọng đọc & Trải nghiệm
    "default_voice": DEFAULT_VOICE,
    "auto_play_audio": True,
    "appearance_mode": "Dark",

    # Lưu trữ & Thư mục tệp âm thanh
    "audio_output_dir": str(OUTPUTS_DIR),

    # Chế độ Realtime Streaming
    "realtime_clipboard_trigger": False,
    "realtime_prebuffer_chunks": 2,
}


class ConfigManager:
    """Quản lý đọc/ghi cấu hình người dùng vào tệp JSON bền vững."""
    _instance = None
    _lock = threading.Lock()

    def __init__(self, config_path: str = None):
        if config_path is None:
            self.config_path = BASE_DIR / "user_settings.json"
        else:
            self.config_path = Path(config_path)

        self._config: Dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.load()

    @classmethod
    def get_instance(cls) -> "ConfigManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ConfigManager()
            return cls._instance

    def load(self) -> Dict[str, Any]:
        """Đọc cấu hình từ tệp user_settings.json."""
        with self._lock:
            if self.config_path.exists():
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        # Cập nhật các trường đã lưu, giữ lại giá trị mặc định cho trường còn thiếu
                        for k, v in data.items():
                            if k in DEFAULT_SETTINGS:
                                self._config[k] = v
                except Exception as e:
                    # Nếu file lỗi, dùng mặc định
                    pass
            return dict(self._config)

    def save(self, new_settings: Dict[str, Any] = None) -> bool:
        """Lưu cấu hình hiện tại hoặc cấu hình mới vào tệp JSON."""
        with self._lock:
            if new_settings:
                self._config.update(new_settings)

            # Đảm bảo thư mục đầu ra tồn tại nếu có thay đổi
            out_dir = Path(self._config.get("audio_output_dir", str(OUTPUTS_DIR)))
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self._config, f, ensure_ascii=False, indent=2)
                return True
            except Exception:
                return False

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any, auto_save: bool = False):
        with self._lock:
            self._config[key] = value
        if auto_save:
            self.save()

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def reset_defaults(self) -> Dict[str, Any]:
        """Khôi phục toàn bộ cấu hình về mặc định ban đầu."""
        with self._lock:
            self._config = dict(DEFAULT_SETTINGS)
        self.save()
        return dict(self._config)
