"""
Audio player service using Pygame mixer.
Provides YouTube-style controls: Play, Pause, Resume, Stop, Scrubbing Seek, Jump -5s / +5s, and Volume.
"""
import os
from pathlib import Path
from typing import Optional, Callable
import soundfile as sf
import pygame


class AudioPlayer:
    def __init__(self):
        self._initialized = False
        self._current_file: Optional[str] = None
        self._total_duration: float = 0.0
        self._start_offset: float = 0.0
        self._is_paused = False
        self._volume: float = 0.8
        self._on_finish_callback: Optional[Callable[[], None]] = None

        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=48000, size=-16, channels=2, buffer=1024)
            pygame.mixer.music.set_volume(self._volume)
            self._initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize Pygame mixer: {e}")
            self._initialized = False

    def load_and_play(self, audio_path: str, start_sec: float = 0.0, on_finish: Optional[Callable[[], None]] = None) -> bool:
        if not self._initialized:
            self._init_mixer()
            if not self._initialized:
                return False

        if not os.path.exists(audio_path):
            return False

        try:
            # Lấy thông tin thời lượng từ soundfile
            try:
                info = sf.info(audio_path)
                self._total_duration = float(info.duration)
            except Exception:
                self._total_duration = 0.0

            start_sec = max(0.0, min(self._total_duration, start_sec))
            self._start_offset = start_sec

            pygame.mixer.music.stop()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play(0, start=start_sec)
            self._current_file = audio_path
            self._is_paused = False
            self._on_finish_callback = on_finish
            return True
        except Exception as e:
            print(f"Error loading and playing audio: {e}")
            return False

    def seek(self, target_sec: float) -> bool:
        """Tua đến vị trí giây cụ thể (Scrubbing / Seek bar)."""
        if not self._initialized or not self._current_file or not os.path.exists(self._current_file):
            return False

        target_sec = max(0.0, min(self._total_duration, target_sec))
        was_paused = self._is_paused

        try:
            self._start_offset = target_sec
            pygame.mixer.music.play(0, start=target_sec)
            if was_paused:
                pygame.mixer.music.pause()
                self._is_paused = True
            else:
                self._is_paused = False
            return True
        except Exception as e:
            print(f"Error seeking audio: {e}")
            return False

    def seek_relative(self, delta_sec: float) -> bool:
        """Tua nhanh tới (+delta) hoặc lùi (-delta) theo số giây (ví dụ: -5s, +5s như YouTube)."""
        current_pos = self.get_elapsed_seconds()
        return self.seek(current_pos + delta_sec)

    def toggle_pause(self) -> bool:
        """Tạm dừng hoặc tiếp tục phát."""
        if not self._initialized or not self._current_file:
            return False

        if self._is_paused:
            pygame.mixer.music.unpause()
            self._is_paused = False
        else:
            pygame.mixer.music.pause()
            self._is_paused = True
        return self._is_paused

    def pause(self) -> None:
        if self._initialized and not self._is_paused:
            pygame.mixer.music.pause()
            self._is_paused = True

    def resume(self) -> None:
        if self._initialized and self._is_paused:
            pygame.mixer.music.unpause()
            self._is_paused = False

    def stop(self) -> None:
        if self._initialized:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._is_paused = False
        self._start_offset = 0.0

    def set_volume(self, volume: float) -> None:
        """Volume từ 0.0 đến 1.0"""
        self._volume = max(0.0, min(1.0, volume))
        if self._initialized:
            try:
                pygame.mixer.music.set_volume(self._volume)
            except Exception:
                pass

    def get_volume(self) -> float:
        return self._volume

    def is_playing(self) -> bool:
        if not self._initialized:
            return False
        return pygame.mixer.music.get_busy() and not self._is_paused

    def is_paused(self) -> bool:
        return self._is_paused

    def get_elapsed_seconds(self) -> float:
        """Lấy số giây đã phát thực tế (đã tính vị trí bắt đầu tua)."""
        if not self._initialized or not self._current_file:
            return 0.0
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return self._start_offset
        elapsed = self._start_offset + (pos_ms / 1000.0)
        return min(self._total_duration, elapsed)

    def get_total_duration(self) -> float:
        return self._total_duration

    def get_current_file(self) -> Optional[str]:
        return self._current_file
