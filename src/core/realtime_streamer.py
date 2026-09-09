"""
Real-time audio streaming player using sounddevice with Jitter-Buffer architecture.
Features:
- Separate Producer-Consumer threads with Queue to prevent buffer underrun / stutter.
- Pre-buffering phase (2 chunks, ~0.5s) to guarantee gapless, smooth audio output.
- Instant thread-safe cancellation / abort (< 15ms).
- Callbacks for chunk progress, latency measurement, and completion.
"""
import queue
import threading
import time
from typing import Generator, Optional, Callable
import numpy as np
import sounddevice as sd

from .logger import AppLogger


class RealtimeAudioStreamer:
    def __init__(self, sample_rate: int = 48000, prebuffer_chunks: int = 2):
        self.sample_rate = sample_rate
        self.prebuffer_chunks = prebuffer_chunks

        self._stop_requested = threading.Event()
        self._is_playing = False
        self._lock = threading.Lock()
        self._stream: Optional[sd.OutputStream] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=100)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def stop(self):
        """Dừng phát âm thanh ngay lập tức trong < 15ms."""
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

        # Dọn sạch hàng đợi âm thanh
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except Exception:
                break

    def play_stream(
        self,
        chunk_generator: Generator[np.ndarray, None, None],
        on_chunk_received: Optional[Callable[[int, float, float], None]] = None,
        on_finished: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Chạy phát âm thanh với cơ chế bộ đệm chống giật (Jitter Buffer).
        Producer (luồng tính toán AI) đẩy mẩu âm thanh vào Queue.
        Consumer (luồng phát âm thanh) đọc mẩu âm thanh từ Queue ra loa.
        """
        self.stop()
        self._stop_requested.clear()
        self._is_playing = True

        # Làm rỗng queue trước khi bắt đầu
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except Exception:
                break

        t_start = time.time()
        first_chunk_latency = None

        # Thread 1: Producer (Luồng sinh âm thanh ngầm từ AI model)
        def _producer():
            nonlocal first_chunk_latency
            total_samples = 0
            chunk_idx = 0
            try:
                for chunk in chunk_generator:
                    if self._stop_requested.is_set():
                        break

                    if chunk is None or len(chunk) == 0:
                        continue

                    now = time.time()
                    if first_chunk_latency is None:
                        first_chunk_latency = (now - t_start) * 1000.0

                    if chunk.dtype != np.float32:
                        audio_data = chunk.astype(np.float32)
                    else:
                        audio_data = chunk

                    if audio_data.ndim > 1:
                        audio_data = audio_data.squeeze()

                    chunk_idx += 1
                    total_samples += len(audio_data)

                    if on_chunk_received:
                        try:
                            on_chunk_received(chunk_idx, total_samples / self.sample_rate, first_chunk_latency)
                        except Exception:
                            pass

                    self._audio_queue.put(audio_data)

            except Exception as e:
                if not self._stop_requested.is_set():
                    AppLogger.exception(f"Lỗi producer infer_stream: {e}", exc=e, source="Streamer")
                    if on_error:
                        on_error(str(e))
            finally:
                # Gửi sentinel kết thúc luồng
                self._audio_queue.put(None)

        producer_thread = threading.Thread(target=_producer, daemon=True, name="StreamProducer")
        producer_thread.start()

        # Consumer Logic (Phát liên tục ra loa với lớp đệm chống rớt âm)
        buffered_chunks = []
        try:
            # 1. Giai đoạn Pre-buffering: Gom trước 2 chunk để tạo lớp đệm chống giật
            while len(buffered_chunks) < self.prebuffer_chunks and not self._stop_requested.is_set():
                try:
                    item = self._audio_queue.get(timeout=3.5)
                    if item is None:
                        break
                    buffered_chunks.append(item)
                except queue.Empty:
                    break

            if self._stop_requested.is_set():
                return

            # 2. Khởi tạo OutputStream và phát mượt mà
            with self._lock:
                self._stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32',
                    blocksize=2048,
                )
                self._stream.start()

            # Phát các mẩu đã đệm trước
            for chunk in buffered_chunks:
                if self._stop_requested.is_set():
                    return
                with self._lock:
                    if self._stream is not None:
                        self._stream.write(chunk)

            # Tiếp tục phát các mẩu tiếp theo từ queue
            while not self._stop_requested.is_set():
                try:
                    item = self._audio_queue.get(timeout=3.5)
                    if item is None:
                        break
                    with self._lock:
                        if self._stream is not None and not self._stop_requested.is_set():
                            self._stream.write(item)
                except queue.Empty:
                    # Timeout
                    break

            # Chờ phát xong các mẫu cuối cùng trong buffer
            if not self._stop_requested.is_set() and self._stream is not None:
                time.sleep(0.15)

        except Exception as e:
            if not self._stop_requested.is_set():
                AppLogger.exception(f"Lỗi consumer phát audio stream: {e}", exc=e, source="Streamer")
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
