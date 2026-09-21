"""
Global logging system for VieNeu-TTS Studio.
Provides static logging methods (info, success, warning, error, exception)
callable from anywhere in the application with thread-safe observer dispatch.
"""
import sys
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

if sys.platform == "win32":
    try:
        if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass



@dataclass
class LogEntry:
    timestamp: str
    level: str  # "INFO", "SUCCESS", "WARNING", "ERROR"
    message: str
    source: str
    traceback_str: Optional[str] = None

    def format_line(self) -> str:
        tag = f"[{self.timestamp}] [{self.level.upper()}] [{self.source}]"
        if self.traceback_str:
            return f"{tag} {self.message}\n{self.traceback_str}"
        return f"{tag} {self.message}"


class AppLogger:
    """
    Centralized logger callable from anywhere in the app.
    Example:
        AppLogger.info("Mô hình đang nạp...", source="TTSEngine")
        AppLogger.exception("Lỗi xử lý audio", exc=e, source="AudioPlayer")
    """
    _lock = threading.Lock()
    _listeners: List[Callable[[LogEntry], None]] = []
    _history: List[LogEntry] = []
    _max_history = 500

    @classmethod
    def subscribe(cls, listener: Callable[[LogEntry], None]) -> None:
        """Đăng ký nhận log thời gian thực (dùng cho UI Log Console)."""
        with cls._lock:
            if listener not in cls._listeners:
                cls._listeners.append(listener)

    @classmethod
    def unsubscribe(cls, listener: Callable[[LogEntry], None]) -> None:
        with cls._lock:
            if listener in cls._listeners:
                cls._listeners.remove(listener)

    @classmethod
    def get_history(cls) -> List[LogEntry]:
        with cls._lock:
            return list(cls._history)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._history.clear()

    @classmethod
    def log(
        cls,
        level: str,
        message: str,
        source: str = "App",
        exc: Optional[BaseException] = None
    ) -> LogEntry:
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        tb_str = None

        if exc is not None:
            tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        elif level == "ERROR" and sys.exc_info()[0] is not None:
            tb_str = traceback.format_exc()

        entry = LogEntry(
            timestamp=timestamp_str,
            level=level,
            message=str(message),
            source=source,
            traceback_str=tb_str
        )

        with cls._lock:
            cls._history.append(entry)
            if len(cls._history) > cls._max_history:
                cls._history.pop(0)
            listeners = list(cls._listeners)

        # In ra console/terminal một cách an toàn tránh lỗi UnicodeEncodeError trên Windows cp1252
        try:
            print(entry.format_line(), flush=True)
        except UnicodeEncodeError:
            try:
                enc = sys.stdout.encoding or "utf-8"
                safe_text = entry.format_line().encode(enc, errors="replace").decode(enc)
                print(safe_text, flush=True)
            except Exception:
                pass
        except Exception:
            pass

        # Gửi sự kiện log tới tất cả các thành phần UI đang lắng nghe
        for listener in listeners:
            try:
                listener(entry)
            except Exception as e:
                pass

        return entry

    @classmethod
    def info(cls, message: str, source: str = "System") -> LogEntry:
        return cls.log("INFO", message, source=source)

    @classmethod
    def success(cls, message: str, source: str = "System") -> LogEntry:
        return cls.log("SUCCESS", message, source=source)

    @classmethod
    def warning(cls, message: str, source: str = "System") -> LogEntry:
        return cls.log("WARNING", message, source=source)

    @classmethod
    def error(cls, message: str, exc: Optional[BaseException] = None, source: str = "System") -> LogEntry:
        return cls.log("ERROR", message, source=source, exc=exc)

    @classmethod
    def exception(cls, message: str, exc: Optional[BaseException] = None, source: str = "System") -> LogEntry:
        """Tự động bắt toàn bộ Exception Stack Trace và thông báo lên UI."""
        if exc is None and sys.exc_info()[1] is not None:
            exc = sys.exc_info()[1]
        return cls.log("ERROR", message, source=source, exc=exc)
