"""
Real-time audio streaming player using sounddevice.
Consumes 48kHz float32 audio chunks yielded by infer_stream and writes directly to sound card.
Supports sub-second response and instant stop/cancellation.
"""
import threading
import time
from typing import Generator, Optional, Callable
import numpy as np
import sounddevice as sd

from .logger import AppLogger


class RealtimeAudioStreamer:
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self._stop_requested = threading.Event()
        self._is_playing = False
        self._lock = threading.Lock()
        self._stream: Optional[sd.OutputStream] = None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def stop(self):
        """Dừng phát âm thanh ngay lập tức trong < 20ms."""
        self._stop_requested.set()
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.abort()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self._is_playing = False

    def play_stream(
        self,
        chunk_generator: Generator[np.ndarray, None, None],
        on_chunk_received: Optional[Callable[[int, float], None]] = None,
        on_finished: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Chạy trong worker thread: lặp qua chunk_generator và phát từng chunk ra loa ngay khi tới.
        """
        self.stop()
        self._stop_requested.clear()
        self._is_playing = True

        total_samples = 0
        chunk_count = 0

        try:
            with self._lock:
                self._stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32',
                    blocksize=2048,
                )
                self._stream.start()

            for chunk in chunk_generator:
                if self._stop_requested.is_set():
                    break

                if chunk is None or len(chunk) == 0:
                    continue

                # Đảm bảo kiểu dữ liệu float32 chuẩn 48kHz
                if chunk.dtype != np.float32:
                    audio_data = chunk.astype(np.float32)
                else:
                    audio_data = chunk

                if audio_data.ndim > 1:
                    audio_data = audio_data.squeeze()

                total_samples += len(audio_data)
                chunk_count += 1

                if on_chunk_received:
                    current_duration = total_samples / self.sample_rate
                    try:
                        on_chunk_received(chunk_count, current_duration)
                    except Exception:
                        pass

                # Ghi vào luồng phát trực tiếp ra loa
                with self._lock:
                    if self._stream is not None and not self._stop_requested.is_set():
                        self._stream.write(audio_data)

            # Chờ âm thanh phát hết mẩu cuối
            if not self._stop_requested.is_set():
                time.sleep(0.1)

        except Exception as e:
            if not self._stop_requested.is_set():
                AppLogger.exception(f"Lỗi phát âm thanh stream: {e}", exc=e, source="Streamer")
                if on_error:
                    on_error(str(e))
        finally:
            with self._lock:
                if self._stream is not None:
                    try:
                        self._stream.stop()
                        self._stream.close()
                    except Exception:
                        pass
                    self._stream = None
                self._is_playing = False

            if on_finished and not self._stop_requested.is_set():
                try:
                    on_finished()
                except Exception:
                    pass

