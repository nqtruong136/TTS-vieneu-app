"""
Realtime Streaming Reader View (Tab: Đọc Realtime).
Listens to Windows Clipboard (Ctrl+C trigger) to read news, books, articles instantly.
Features sub-second streaming audio playback via sounddevice, instant stop,
and a sleek Quick History Preview pane on the right.
"""
from datetime import datetime
import os
import threading
import time
from typing import List, Dict, Any, Optional
import customtkinter as ctk
import pyperclip

from ..styles import COLORS, FONTS
from ..dispatcher import UIDispatcher
from ...config import DEFAULT_VOICE, AVAILABLE_VOICES
from ...core.tts_engine import TTSEngine
from ...core.realtime_streamer import RealtimeAudioStreamer
from ...core.clipboard_watcher import ClipboardWatcher
from ...core.logger import AppLogger


class RealtimeView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        tts_engine: TTSEngine,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.tts_engine = tts_engine
        self.streamer = RealtimeAudioStreamer()
        self.watcher = ClipboardWatcher(on_new_text=self._on_clipboard_text)

        # Trạng thái
        self.current_text = ""
        self.quick_history: List[Dict[str, Any]] = []
        self._is_streaming = False
        self._current_worker_thread: Optional[threading.Thread] = None

        self._create_widgets()
        self.watcher.start()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=340)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # 1. CỘT BÊN TRÁI: KHÔNG GIAN ĐỌC CHÍNH
        # ==========================================
        left_container = ctk.CTkFrame(self, fg_color="transparent")
        left_container.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=0)
        left_container.grid_rowconfigure(2, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        # 1.1 Header Bar
        header_card = ctk.CTkFrame(
            left_container,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        header_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        h_layout = ctk.CTkFrame(header_card, fg_color="transparent")
        h_layout.pack(fill="x", padx=16, pady=12)

        ctk.CTkLabel(
            h_layout,
            text="⚡ ĐỌC REALTIME (STREAMING CLIPBOARD READER)",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS["primary"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            h_layout,
            text="Tự động đọc bài báo, tài liệu, sách tức thì khi bạn bôi đen và bấm Copy (Ctrl + C)",
            font=FONTS["caption"],
            text_color="gray"
        ).pack(anchor="w", pady=(2, 0))

        # 1.2 Control Card (Trigger Switch, Giọng đọc, Nút Dừng, Trạng thái)
        control_card = ctk.CTkFrame(
            left_container,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        control_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ctrl_inner = ctk.CTkFrame(control_card, fg_color="transparent")
        ctrl_inner.pack(fill="x", padx=16, pady=12)

        # Hàng 1: Switch Bật/Tắt + Chọn Giọng + Nút Dừng/Đọc lại
        top_ctrl = ctk.CTkFrame(ctrl_inner, fg_color="transparent")
        top_ctrl.pack(fill="x", pady=(0, 10))

        self.trigger_switch = ctk.CTkSwitch(
            top_ctrl,
            text="📡 Tự động đọc khi Copy (Ctrl + C)",
            font=("Segoe UI", 13, "bold"),
            progress_color=COLORS["primary"],
            command=self._on_toggle_trigger
        )
        self.trigger_switch.pack(side="left", padx=(0, 16))

        # Chọn giọng
        ctk.CTkLabel(top_ctrl, text="🎙 Giọng:", font=FONTS["body"]).pack(side="left", padx=(0, 6))
        self.voice_menu = ctk.CTkOptionMenu(
            top_ctrl,
            values=AVAILABLE_VOICES,
            width=135,
            height=30,
            font=FONTS["body"]
        )
        self.voice_menu.set(DEFAULT_VOICE)
        self.voice_menu.pack(side="left", padx=(0, 14))

        # Nút Dừng đọc ngay
        self.btn_stop = ctk.CTkButton(
            top_ctrl,
            text="⏹ Dừng đọc",
            width=90,
            height=30,
            font=("Segoe UI", 11, "bold"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            state="disabled",
            command=self._handle_stop_click
        )
        self.btn_stop.pack(side="right", padx=(6, 0))

        # Nút Đọc lại đoạn này
        self.btn_replay = ctk.CTkButton(
            top_ctrl,
            text="🔄 Đọc lại",
            width=85,
            height=30,
            font=("Segoe UI", 11),
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            state="disabled",
            command=self._handle_replay_click
        )
        self.btn_replay.pack(side="right")

        # Hàng 2: Banner trạng thái trực quan
        self.status_banner = ctk.CTkFrame(
            ctrl_inner,
            corner_radius=6,
            fg_color="#1E222B",
            border_width=1,
            border_color=COLORS["border_dark"]
        )
        self.status_banner.pack(fill="x")

        self.status_indicator = ctk.CTkLabel(
            self.status_banner,
            text="⚪ Đang tắt chế độ tự động. Bật công tắc bên trên để bắt đầu lắng nghe khay nhớ tạm (Clipboard).",
            font=FONTS["body"],
            text_color="gray",
            wraplength=600,
            justify="left"
        )
        self.status_indicator.pack(anchor="w", padx=12, pady=8)

        # 1.3 Card hiển thị văn bản đang đọc trực tiếp
        reading_card = ctk.CTkFrame(
            left_container,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        reading_card.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        reading_card.grid_rowconfigure(1, weight=1)
        reading_card.grid_columnconfigure(0, weight=1)

        read_top = ctk.CTkFrame(reading_card, fg_color="transparent")
        read_top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            read_top,
            text="📖 NỘI DUNG ĐANG ĐỌC (TRỰC TIẾP TỪ CLIPBOARD):",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["primary"]
        ).pack(side="left")

        self.stream_stats_label = ctk.CTkLabel(
            read_top,
            text="",
            font=FONTS["code"],
            text_color=COLORS["secondary"]
        )
        self.stream_stats_label.pack(side="right")

        # Khung Textbox hiển thị câu đang đọc (Font chữ 14 to rõ, dễ theo dõi)
        self.reading_textbox = ctk.CTkTextbox(
            reading_card,
            font=("Segoe UI", 14),
            wrap="word",
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color="#13161C"
        )
        self.reading_textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))
        self.reading_textbox.insert("1.0", "Chưa có nội dung. Hãy bật công tắc phía trên rồi bôi đen và nhấn Ctrl + C trên trình duyệt hoặc tài liệu bất kỳ...")
        self.reading_textbox.configure(state="disabled")

        # 1.4 Hộp nhập thủ công dưới cùng
        manual_card = ctk.CTkFrame(
            left_container,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        manual_card.grid(row=3, column=0, sticky="ew")

        manual_inner = ctk.CTkFrame(manual_card, fg_color="transparent")
        manual_inner.pack(fill="x", padx=16, pady=10)

        self.manual_entry = ctk.CTkEntry(
            manual_inner,
            placeholder_text="✍️ Hoặc dán/gõ nội dung vào đây rồi bấm Đọc Ngay...",
            height=34,
            font=FONTS["body"]
        )
        self.manual_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.manual_entry.bind("<Return>", lambda e: self._handle_manual_trigger())

        self.btn_manual_read = ctk.CTkButton(
            manual_inner,
            text="⚡ Đọc ngay",
            width=100,
            height=34,
            font=("Segoe UI", 12, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._handle_manual_trigger
        )
        self.btn_manual_read.pack(side="right")

        # ==========================================
        # 2. CỘT BÊN PHẢI: QUICK HISTORY PREVIEW PANE
        # ==========================================
        right_container = ctk.CTkFrame(
            self,
            width=340,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"]
        )
        right_container.grid(row=0, column=1, sticky="nsew")
        right_container.grid_propagate(False)
        right_container.grid_rowconfigure(1, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        # Header của Quick History
        q_header = ctk.CTkFrame(right_container, fg_color="transparent")
        q_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        ctk.CTkLabel(
            q_header,
            text="📋 LỊCH SỬ COPY NHANH",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["primary"]
        ).pack(side="left")

        self.history_count_label = ctk.CTkLabel(
            q_header,
            text="(0)",
            font=FONTS["caption"],
            text_color="gray"
        )
        self.history_count_label.pack(side="left", padx=4)

        btn_clear_quick = ctk.CTkButton(
            q_header,
            text="✕ Xóa",
            width=48,
            height=22,
            font=FONTS["caption"],
            fg_color="transparent",
            text_color=COLORS["danger"],
            hover_color=COLORS["card_bg_dark"],
            command=self._clear_quick_history
        )
        btn_clear_quick.pack(side="right")

        # Danh sách cuộn các bản copy gọn gàng
        self.history_scroll = ctk.CTkScrollableFrame(
            right_container,
            fg_color="transparent",
            corner_radius=0
        )
        self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 10))

        self._render_empty_history()

    def _render_empty_history(self):
        for w in self.history_scroll.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.history_scroll,
            text="Chưa có đoạn văn nào.\n\nMỗi khi bạn bôi đen và bấm Copy,\nđoạn văn sẽ được lưu nhanh tại đây\nđể bạn nghe lại bất kỳ lúc nào!",
            font=FONTS["caption"],
            text_color="gray",
            justify="center"
        ).pack(pady=40)

    def _on_toggle_trigger(self):
        is_active = bool(self.trigger_switch.get())
        self.watcher.set_active(is_active)

        if is_active:
            self.status_banner.configure(fg_color="#0D2818", border_color="#10B981")
            self.status_indicator.configure(
                text="🟢 Đang lắng nghe Clipboard... Bạn chỉ cần bôi đen văn bản trên Chrome/PDF/Sách rồi bấm Ctrl+C là app tự đọc ngay!",
                text_color="#6EE7B7"
            )
        else:
            self.status_banner.configure(fg_color="#1E222B", border_color=COLORS["border_dark"])
            self.status_indicator.configure(
                text="⚪ Đang tạm dừng lắng nghe Clipboard. Bật công tắc bên trên để tiếp tục.",
                text_color="gray"
            )

    def _on_clipboard_text(self, text: str):
        """Được gọi từ ClipboardWatcher daemon thread khi có văn bản mới."""
        UIDispatcher.post(self._process_new_text, text, "clipboard")

    def _handle_manual_trigger(self):
        text = self.manual_entry.get().strip()
        if not text:
            return
        self.manual_entry.delete(0, "end")
        self._process_new_text(text, source="manual")

    def _process_new_text(self, text: str, source: str = "clipboard"):
        """Xử lý đoạn văn bản mới: nạp vào ô đọc, thêm vào lịch sử nhanh và kích hoạt stream."""
        if not text or len(text.strip()) < 2:
            return

        clean = text.strip()
        self.current_text = clean

        # 1. Cập nhật textbox hiển thị
        self.reading_textbox.configure(state="normal")
        self.reading_textbox.delete("1.0", "end")
        self.reading_textbox.insert("1.0", clean)
        self.reading_textbox.configure(state="disabled")

        # 2. Thêm vào danh sách lịch sử nhanh
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        record = {
            "id": int(time.time() * 1000),
            "text": clean,
            "timestamp": timestamp_str,
            "source": source
        }
        self.quick_history.insert(0, record)
        # Giới hạn tối đa 30 mục gần nhất
        if len(self.quick_history) > 30:
            self.quick_history.pop()
        self._render_quick_history()

        # 3. Kích hoạt phát âm thanh Realtime
        self.btn_replay.configure(state="normal")
        self.btn_stop.configure(state="normal")
        self._start_streaming(clean)

    def _start_streaming(self, text: str):
        """Khởi động luồng đọc theo thời gian thực (infer_stream)."""
        if not self.tts_engine.is_ready():
            warn_msg = "Mô hình AI chưa sẵn sàng. Vui lòng vào Tab Cài đặt để nạp mô hình!"
            AppLogger.warning(warn_msg, source="Realtime")
            self.status_banner.configure(fg_color="#2A1B1B", border_color=COLORS["danger"])
            self.status_indicator.configure(text=f"❌ {warn_msg}", text_color=COLORS["danger"])
            return

        # Dừng luồng đang phát trước đó (nếu có)
        self.streamer.stop()

        chosen_voice = self.voice_menu.get()
        self.status_banner.configure(fg_color="#0F2B38", border_color=COLORS["primary"])
        self.status_indicator.configure(
            text=f"🔊 ĐANG ĐỌC THEO THỜI GIAN THỰC... (Giọng: {chosen_voice})",
            text_color=COLORS["primary"]
        )
        self.stream_stats_label.configure(text="⚡ Đang bắt đầu...")
        self.btn_stop.configure(state="normal")

        # Chạy worker thread
        self._current_worker_thread = threading.Thread(
            target=self._stream_worker,
            args=(text, chosen_voice),
            daemon=True,
            name="RealtimeInferWorker"
        )
        self._current_worker_thread.start()

    def _stream_worker(self, text: str, voice: str):
        t0 = time.time()
        first_chunk_time: Optional[float] = None

        try:
            generator = self.tts_engine.infer_stream(text, voice=voice)

            def on_chunk(chunk_idx: int, duration_sec: float, latency_ms: float = 0.0):
                stat = f"⚡ Độ trễ: {latency_ms:.0f}ms • {chunk_idx} chunks ({duration_sec:.1f}s) • Đệm mượt mà"
                UIDispatcher.post(self.stream_stats_label.configure, text=stat)

            def on_finished():
                total_t = time.time() - t0
                UIDispatcher.post(self._on_stream_completed, total_t)

            def on_error(err_str: str):
                UIDispatcher.post(self._on_stream_error, err_str)

            self.streamer.play_stream(
                chunk_generator=generator,
                on_chunk_received=on_chunk,
                on_finished=on_finished,
                on_error=on_error
            )
        except Exception as e:
            AppLogger.exception(f"Lỗi khởi tạo infer_stream: {e}", exc=e, source="Realtime")
            UIDispatcher.post(self._on_stream_error, str(e))

    def _on_stream_completed(self, total_time: float):
        self.btn_stop.configure(state="disabled")
        self.stream_stats_label.configure(text=f"✓ Đã đọc xong ({total_time:.1f}s)")
        if self.trigger_switch.get():
            self.status_banner.configure(fg_color="#0D2818", border_color="#10B981")
            self.status_indicator.configure(
                text="🟢 Đang lắng nghe Clipboard... Bạn chỉ cần bôi đen văn bản trên Chrome/PDF/Sách rồi bấm Ctrl+C là app tự đọc ngay!",
                text_color="#6EE7B7"
            )
        else:
            self.status_banner.configure(fg_color="#1E222B", border_color=COLORS["border_dark"])
            self.status_indicator.configure(
                text="⚪ Đã đọc xong. Bật công tắc bên trên để lắng nghe Clipboard.",
                text_color="gray"
            )

    def _on_stream_error(self, err_msg: str):
        self.btn_stop.configure(state="disabled")
        self.status_banner.configure(fg_color="#2A1B1B", border_color=COLORS["danger"])
        self.status_indicator.configure(
            text=f"❌ Lỗi đọc âm thanh: {err_msg}",
            text_color=COLORS["danger"]
        )

    def _handle_stop_click(self):
        """Bấm nút Dừng đọc ngay."""
        self.streamer.stop()
        self.btn_stop.configure(state="disabled")
        self.stream_stats_label.configure(text="⏹ Đã dừng")
        self.status_banner.configure(fg_color="#1E222B", border_color=COLORS["border_dark"])
        self.status_indicator.configure(
            text="⏹ Đã dừng đọc. Bấm 'Đọc lại' hoặc copy đoạn mới để tiếp tục.",
            text_color="gray"
        )
        AppLogger.info("Người dùng đã bấm dừng đọc realtime.", source="Realtime")

    def _handle_replay_click(self):
        """Bấm nút Đọc lại đoạn văn vừa đọc."""
        if self.current_text:
            self._start_streaming(self.current_text)

    def _render_quick_history(self):
        """Vẽ danh sách các thẻ xem lại nhanh bên cột phải."""
        for w in self.history_scroll.winfo_children():
            w.destroy()

        self.history_count_label.configure(text=f"({len(self.quick_history)})")

        if not self.quick_history:
            self._render_empty_history()
            return

        for item in self.quick_history:
            self._create_history_item_card(item)

    def _create_history_item_card(self, item: Dict[str, Any]):
        card = ctk.CTkFrame(
            self.history_scroll,
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color="#171A21"
        )
        card.pack(fill="x", pady=4, padx=2)

        # Header của thẻ nhỏ: Giờ copy + Nút Nghe lại + Nút Copy lại
        h_row = ctk.CTkFrame(card, fg_color="transparent")
        h_row.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkLabel(
            h_row,
            text=f"⏱ {item['timestamp']}",
            font=FONTS["caption"],
            text_color="gray"
        ).pack(side="left")

        # Nút Copy lại
        btn_copy = ctk.CTkButton(
            h_row,
            text="📋",
            width=26,
            height=22,
            font=("Segoe UI", 10),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda t=item["text"]: self._copy_to_clipboard(t)
        )
        btn_copy.pack(side="right", padx=(4, 0))

        # Nút Nghe lại mini
        btn_play = ctk.CTkButton(
            h_row,
            text="▶ Nghe",
            width=54,
            height=22,
            font=("Segoe UI", 10, "bold"),
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            command=lambda t=item["text"]: self._replay_specific_text(t)
        )
        btn_play.pack(side="right")

        # Nội dung trích dẫn rút gọn (Tối đa 110 ký tự)
        snip = item["text"][:110].strip().replace("\n", " ")
        if len(item["text"]) > 110:
            snip += "..."

        snip_label = ctk.CTkLabel(
            card,
            text=f'"{snip}"',
            font=("Segoe UI", 11),
            text_color="#CBD5E1",
            wraplength=280,
            justify="left"
        )
        snip_label.pack(anchor="w", padx=8, pady=(2, 6))

        # Click vào toàn bộ thẻ để nghe lại
        card.bind("<Button-1>", lambda e, t=item["text"]: self._replay_specific_text(t))
        snip_label.bind("<Button-1>", lambda e, t=item["text"]: self._replay_specific_text(t))

    def _replay_specific_text(self, text: str):
        self.current_text = text
        self.reading_textbox.configure(state="normal")
        self.reading_textbox.delete("1.0", "end")
        self.reading_textbox.insert("1.0", text)
        self.reading_textbox.configure(state="disabled")
        self.btn_replay.configure(state="normal")
        self._start_streaming(text)

    def _copy_to_clipboard(self, text: str):
        try:
            pyperclip.copy(text)
            AppLogger.info("Đã sao chép lại đoạn văn vào Clipboard.", source="Realtime")
        except Exception:
            pass

    def _clear_quick_history(self):
        self.quick_history.clear()
        self._render_quick_history()

    def destroy(self):
        """Dọn dẹp tài nguyên khi đóng ứng dụng."""
        if hasattr(self, "streamer"):
            self.streamer.stop()
        if hasattr(self, "watcher"):
            self.watcher.stop()
        super().destroy()

