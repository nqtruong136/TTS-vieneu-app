"""
Progress tracking interface for percentage-based operations.
Provides thread-safe progress updates (0% - 100%) and stage descriptions
for model downloads, PyTorch CUDA installation, inference chunks, and benchmarks.
"""
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class ProgressState:
    percent: float  # 0.0 -> 100.0
    message: str
    stage: str = ""
    is_active: bool = False
    is_error: bool = False


class ProgressTracker:
    """
    Progress tracker interface.
    Allows worker threads to publish percentage updates (0-100%) and messages.
    UI components can subscribe to automatically update progress bars and labels.
    """
    def __init__(self, on_update: Optional[Callable[[ProgressState], None]] = None):
        self._lock = threading.Lock()
        self._listeners: List[Callable[[ProgressState], None]] = []
        if on_update:
            self._listeners.append(on_update)

        self._state = ProgressState(
            percent=0.0,
            message="Sẵn sàng",
            stage="",
            is_active=False,
            is_error=False
        )

    def subscribe(self, listener: Callable[[ProgressState], None]) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[ProgressState], None]) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def update(self, percent: float, message: str = "", stage: str = "") -> None:
        """Cập nhật phần trăm (0.0 -> 100.0) và thông điệp tiến trình."""
        percent = max(0.0, min(100.0, float(percent)))
        with self._lock:
            self._state = ProgressState(
                percent=percent,
                message=message or self._state.message,
                stage=stage or self._state.stage,
                is_active=percent < 100.0,
                is_error=False
            )
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(self._state)
            except Exception as e:
                print(f"Error in progress listener: {e}")

    def step(self, delta_percent: float, message: str = "") -> None:
        """Tăng thêm delta phần trăm."""
        new_val = self._state.percent + delta_percent
        self.update(new_val, message=message)

    def complete(self, message: str = "Hoàn thành!") -> None:
        """Đánh dấu hoàn thành 100%."""
        with self._lock:
            self._state = ProgressState(
                percent=100.0,
                message=message,
                stage="Done",
                is_active=False,
                is_error=False
            )
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(self._state)
            except Exception as e:
                print(f"Error in progress listener: {e}")

    def error(self, message: str = "Thất bại!") -> None:
        """Đánh dấu tiến trình gặp lỗi."""
        with self._lock:
            self._state = ProgressState(
                percent=self._state.percent,
                message=message,
                stage="Error",
                is_active=False,
                is_error=True
            )
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(self._state)
            except Exception as e:
                print(f"Error in progress listener: {e}")

    def reset(self, message: str = "Sẵn sàng") -> None:
        with self._lock:
            self._state = ProgressState(
                percent=0.0,
                message=message,
                stage="",
                is_active=False,
                is_error=False
            )
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(self._state)
            except Exception as e:
                print(f"Error in progress listener: {e}")

    def get_state(self) -> ProgressState:
        with self._lock:
            return self._state

