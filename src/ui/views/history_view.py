"""
Generated Voice Library & History View (Tab: Các giọng đã tạo).
Features pagination (phân trang), search, voice filtering, card list,
and an integrated YouTube-style audio scrubber player bar at the bottom.
"""
import math
import os
import subprocess
from typing import Callable, Optional, List
import customtkinter as ctk

from ..styles import COLORS, FONTS
from ...database.history_manager import HistoryManager, HistoryRecord
from ...core.audio_player import AudioPlayer
from ...core.logger import AppLogger
from ..components.player_bar import PlayerBar
from ...config import OUTPUTS_DIR


class HistoryView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        history_manager: HistoryManager,
        audio_player: AudioPlayer,
        on_load_text_request: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.history_manager = history_manager
        self.audio_player = audio_player
        self.on_load_text_request = on_load_text_request

        # Trạng thái phân trang
        self.current_page = 1
        self.page_size = 6
        self.total_pages = 1
        self.total_records = 0
        self.current_voice_filter = "all"
        self.current_search = ""

        # Trạng thái card & xem lại
        self.active_record_id: Optional[int] = None
        self.expanded_records: dict = {}
        self._cached_records: List[HistoryRecord] = []

        self._create_widgets()
        self.refresh_data()

    def _create_widgets(self):
        # 1. Header Toolbar
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="🎵 CÁC GIỌNG ĐÃ TẠO (THƯ VIỆN BẢN THU)",
            font=("Segoe UI", 16, "bold"),
            text_color=COLORS["primary"]
        )
        title_label.pack(side="left")

        # Nút Mở thư mục & Xóa hết
        btn_open_folder = ctk.CTkButton(
            header_frame,
            text="📁 Mở thư mục lưu",
            width=130,
            height=28,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._open_folder
        )
        btn_open_folder.pack(side="right", padx=(6, 0))

        btn_clear_all = ctk.CTkButton(
            header_frame,
            text="🗑 Xóa hết lịch sử",
            width=120,
            height=28,
            font=FONTS["caption"],
            fg_color="transparent",
            text_color=COLORS["danger"],
            border_width=1,
            border_color=COLORS["danger"],
            hover_color=COLORS["card_bg_dark"],
            command=self._clear_all
        )
        btn_clear_all.pack(side="right")

        # 2. Filter & Search Controls Row
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.pack(fill="x", pady=(0, 8))

        # Ô tìm kiếm
        self.search_entry = ctk.CTkEntry(
            filter_bar,
            placeholder_text="🔍 Tìm kiếm nội dung văn bản hoặc tên giọng...",
            height=32,
            font=FONTS["body"]
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search_change())

        # Dropdown lọc theo giọng
        self.voice_filter_menu = ctk.CTkOptionMenu(
            filter_bar,
            values=["Tất cả giọng"],
            width=150,
            height=32,
            command=self._on_voice_filter_change
        )
        self.voice_filter_menu.pack(side="left", padx=(0, 10))

        # Dropdown số lượng bản ghi mỗi trang
        self.page_size_menu = ctk.CTkOptionMenu(
            filter_bar,
            values=["6 / trang", "10 / trang", "20 / trang"],
            width=110,
            height=32,
            command=self._on_page_size_change
        )
        self.page_size_menu.set(f"{self.page_size} / trang")
        self.page_size_menu.pack(side="left")

        # 3. Main Scrollable Container for Cards
        self.cards_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.cards_scroll.pack(fill="both", expand=True, pady=(0, 8))

        # 4. Pagination Bar (Thanh chuyển trang)
        self.pagination_frame = ctk.CTkFrame(self, fg_color=COLORS["card_bg_dark"], height=38, corner_radius=6)
        self.pagination_frame.pack(fill="x", pady=(0, 8))

        self.btn_first_page = ctk.CTkButton(
            self.pagination_frame,
            text="⏮ Đầu",
            width=60,
            height=26,
            font=FONTS["caption"],
            command=lambda: self._go_to_page(1)
        )
        self.btn_first_page.pack(side="left", padx=(8, 4), pady=6)

        self.btn_prev_page = ctk.CTkButton(
            self.pagination_frame,
            text="◀ Trước",
            width=66,
            height=26,
            font=FONTS["caption"],
            command=lambda: self._go_to_page(self.current_page - 1)
        )
        self.btn_prev_page.pack(side="left", padx=(0, 8), pady=6)

        self.page_info_label = ctk.CTkLabel(
            self.pagination_frame,
            text="Trang 1 / 1  (0 bản thu)",
            font=FONTS["body"]
        )
        self.page_info_label.pack(side="left", expand=True)

        self.btn_next_page = ctk.CTkButton(
            self.pagination_frame,
            text="Sau ▶",
            width=66,
            height=26,
            font=FONTS["caption"],
            command=lambda: self._go_to_page(self.current_page + 1)
        )
        self.btn_next_page.pack(side="right", padx=(4, 8), pady=6)

        self.btn_last_page = ctk.CTkButton(
            self.pagination_frame,
            text="Cuối ⏭",
            width=60,
            height=26,
            font=FONTS["caption"],
            command=lambda: self._go_to_page(self.total_pages)
        )
        self.btn_last_page.pack(side="right", padx=(0, 4), pady=6)

        # 5. Master YouTube-style Player Bar at the bottom of the Library
        self.master_player = PlayerBar(self, audio_player=self.audio_player)
        self.master_player.pack(fill="x")

    def refresh_data(self):
        """Lấy dữ liệu theo trang hiện tại và hiển thị lên danh sách."""
        # 1. Cập nhật danh sách giọng cho dropdown filter
        voices = self.history_manager.get_distinct_voices()
        filter_options = ["Tất cả giọng"] + voices
        self.voice_filter_menu.configure(values=filter_options)

        # 2. Truy vấn dữ liệu có phân trang
        v_filter = "all" if self.current_voice_filter == "Tất cả giọng" else self.current_voice_filter
        records, total_count = self.history_manager.get_records_paginated(
            page=self.current_page,
            page_size=self.page_size,
            search_query=self.current_search,
            voice_filter=v_filter
        )

        self.total_records = total_count
        self.total_pages = max(1, math.ceil(total_count / self.page_size)) if total_count > 0 else 1

        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            records, total_count = self.history_manager.get_records_paginated(
                page=self.current_page,
                page_size=self.page_size,
                search_query=self.current_search,
                voice_filter=v_filter
            )

        # 3. Cập nhật thanh phân trang
        start_idx = (self.current_page - 1) * self.page_size + 1 if total_count > 0 else 0
        end_idx = min(total_count, self.current_page * self.page_size)
        self.page_info_label.configure(
            text=f"Trang {self.current_page} / {self.total_pages}  (Bản ghi {start_idx}–{end_idx} trên tổng số {total_count})"
        )

        self.btn_prev_page.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_first_page.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next_page.configure(state="normal" if self.current_page < self.total_pages else "disabled")
        self.btn_last_page.configure(state="normal" if self.current_page < self.total_pages else "disabled")

        # 4. Lưu cache và vẽ danh sách cards
        self._cached_records = records
        self._rerender_cards_only()

        # Nạp bản ghi đầu tiên vào thanh phát YouTube bên dưới (ở trạng thái Sẵn sàng) nếu chưa nạp file nào
        if records and self.master_player.current_audio_path is None:
            first_rec = records[0]
            self.active_record_id = first_rec.id
            res = {
                "audio_path": first_rec.audio_path,
                "duration": first_rec.duration,
                "process_time": first_rec.process_time,
                "rtf": first_rec.rtf,
                "voice": first_rec.voice_name,
                "text": first_rec.text
            }
            self.master_player.set_audio_result(res, auto_play=False)

    def _rerender_cards_only(self):
        """Vẽ lại các card mà không cần truy vấn lại SQLite."""
        for widget in self.cards_scroll.winfo_children():
            widget.destroy()

        if not self._cached_records:
            ctk.CTkLabel(
                self.cards_scroll,
                text="Không có bản thu nào phù hợp với bộ lọc hiện tại.",
                font=FONTS["body"],
                text_color="gray"
            ).pack(pady=40)
            return

        for record in self._cached_records:
            self._create_record_card(record)

    def _create_record_card(self, record: HistoryRecord):
        is_active = (self.active_record_id == record.id)
        border_color = COLORS["primary"] if is_active else COLORS["border_dark"]
        border_width = 2 if is_active else 1

        card = ctk.CTkFrame(
            self.cards_scroll,
            corner_radius=8,
            border_width=border_width,
            border_color=border_color,
            fg_color=COLORS["card_bg_dark"]
        )
        card.pack(fill="x", pady=5, padx=2)

        # 1. Header Toolbar Row: Chứa TOÀN BỘ nút chức năng (Luôn hiển thị trên cùng!)
        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 4))

        # Nút Nghe lại (Lớn, Nổi bật, ở ngay góc trên bên trái)
        is_playing_this = (is_active and self.audio_player.is_playing())
        btn_play_text = "⏸ Tạm dừng" if is_playing_this else "▶ Nghe lại"
        btn_play_color = COLORS["primary"] if is_active else COLORS["secondary"]
        btn_play = ctk.CTkButton(
            top_row,
            text=btn_play_text,
            width=96,
            height=28,
            font=("Segoe UI", 11, "bold"),
            fg_color=btn_play_color,
            command=lambda r=record: self._play_in_master_player(r)
        )
        btn_play.pack(side="left", padx=(0, 10))

        # Badge giọng
        ctk.CTkLabel(
            top_row,
            text=f"🎙 {record.voice_name}",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["primary"]
        ).pack(side="left", padx=(0, 8))

        # Badge thời lượng
        mins = int(record.duration // 60)
        secs = int(record.duration % 60)
        time_formatted = f"{mins:02d}:{secs:02d}"
        ctk.CTkLabel(
            top_row,
            text=f"⏱ {time_formatted} ({record.duration:.1f}s)",
            font=FONTS["caption"],
            text_color=COLORS["secondary"]
        ).pack(side="left", padx=(0, 8))

        # Cấu hình engine
        ctk.CTkLabel(
            top_row,
            text=f"⚙️ {record.profile_name}",
            font=FONTS["caption"],
            text_color="gray"
        ).pack(side="left")

        # Nút Xóa (Góc trên bên phải)
        btn_del = ctk.CTkButton(
            top_row,
            text="✕",
            width=28,
            height=26,
            font=("Segoe UI", 11),
            fg_color="transparent",
            text_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=lambda r_id=record.id: self._delete_record(r_id)
        )
        btn_del.pack(side="right")

        # Nút Mở file
        btn_file = ctk.CTkButton(
            top_row,
            text="📂 File",
            width=58,
            height=26,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda p=record.audio_path: self._select_file(p)
        )
        btn_file.pack(side="right", padx=(4, 6))

        # Nút Nạp văn bản vào ô soạn thảo
        btn_load = ctk.CTkButton(
            top_row,
            text="📋 Dùng lại text",
            width=95,
            height=26,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=lambda t=record.text: self._load_text(t)
        )
        btn_load.pack(side="right", padx=(4, 4))

        # Timestamp
        ctk.CTkLabel(
            top_row,
            text=record.timestamp,
            font=FONTS["caption"],
            text_color="gray"
        ).pack(side="right", padx=(0, 8))

        # 2. Nội dung văn bản (Có rút gọn thông minh + Nút Xem thêm / Thu gọn)
        content_frame = ctk.CTkFrame(card, fg_color="transparent")
        content_frame.pack(fill="x", padx=12, pady=(2, 6))

        is_long = len(record.text) > 160 or "\n" in record.text
        is_expanded = self.expanded_records.get(record.id, False)

        display_text = record.text if (not is_long or is_expanded) else (record.text[:140].strip() + "...")

        text_label = ctk.CTkLabel(
            content_frame,
            text=f'"{display_text}"',
            font=FONTS["body"],
            wraplength=760,
            justify="left"
        )
        text_label.pack(side="left", anchor="w")

        if is_long:
            toggle_text = "▲ Thu gọn" if is_expanded else "▼ Xem thêm"
            btn_toggle = ctk.CTkButton(
                content_frame,
                text=toggle_text,
                width=75,
                height=22,
                font=FONTS["caption"],
                fg_color="transparent",
                text_color=COLORS["primary"],
                hover_color=COLORS["card_bg_dark"],
                command=lambda r_id=record.id: self._toggle_expand_record(r_id)
            )
            btn_toggle.pack(side="left", padx=(8, 0), anchor="center")

        # 3. Dòng thông tin file và chỉ số hiệu năng
        sub_row = ctk.CTkFrame(card, fg_color="transparent")
        sub_row.pack(fill="x", padx=12, pady=(0, 8))

        filename = os.path.basename(record.audio_path)
        file_exists = os.path.exists(record.audio_path)
        stats_str = f"🎵 {filename}  •  ⏱ Tạo trong {record.process_time:.2f}s  •  RTF: {record.rtf:.2f}"
        if not file_exists:
            stats_str += "  ⚠️ (Tệp âm thanh không tồn tại trên đĩa)"

        ctk.CTkLabel(
            sub_row,
            text=stats_str,
            font=FONTS["caption"],
            text_color=COLORS["secondary"] if file_exists else COLORS["danger"]
        ).pack(side="left")

        # Cho phép click vào toàn bộ thanh header để phát
        top_row.bind("<Button-1>", lambda e, r=record: self._play_in_master_player(r))

    def _toggle_expand_record(self, record_id: int):
        """Đóng/Mở văn bản dài của bản ghi."""
        self.expanded_records[record_id] = not self.expanded_records.get(record_id, False)
        self._rerender_cards_only()

    def _play_in_master_player(self, record: HistoryRecord):
        """Nạp bài thu được chọn vào thanh tua YouTube bên dưới và bắt đầu phát/tạm dừng."""
        if not os.path.exists(record.audio_path):
            AppLogger.warning(f"File âm thanh không tồn tại: {record.audio_path}", source="History")
            self.master_player.stats_label.configure(
                text=f"❌ Tệp âm thanh không tồn tại: {os.path.basename(record.audio_path)}",
                text_color=COLORS["danger"]
            )
            return

        # Nếu đang chọn bài này và đang phát -> tạm dừng
        if self.active_record_id == record.id and self.audio_player.is_playing():
            self.master_player._play_click()
            self._rerender_cards_only()
            return
        elif self.active_record_id == record.id and self.audio_player.is_paused():
            self.master_player._play_click()
            self._rerender_cards_only()
            return

        self.active_record_id = record.id
        AppLogger.info(f"Phát bản ghi #{record.id} ({record.voice_name}) trên trình phát YouTube Scrubber", source="History")
        res = {
            "audio_path": record.audio_path,
            "duration": record.duration,
            "process_time": record.process_time,
            "rtf": record.rtf,
            "voice": record.voice_name,
            "text": record.text
        }
        self.master_player.set_audio_result(res, auto_play=True)
        self._rerender_cards_only()

    def _load_text(self, text: str):
        if self.on_load_text_request:
            self.on_load_text_request(text)

    def _delete_record(self, record_id: int):
        try:
            self.history_manager.delete_record(record_id)
            AppLogger.info(f"Đã xóa bản ghi #{record_id} khỏi thư viện.", source="History")
        except Exception as e:
            AppLogger.exception(f"Lỗi khi xóa bản ghi #{record_id}", exc=e, source="History")
        self.refresh_data()

    def _clear_all(self):
        try:
            self.history_manager.clear_all()
            AppLogger.info("Đã dọn dẹp sạch toàn bộ lịch sử bản thu.", source="History")
        except Exception as e:
            AppLogger.exception("Lỗi khi xóa toàn bộ lịch sử", exc=e, source="History")
        self.refresh_data()

    def _select_file(self, audio_path: str):
        if os.path.exists(audio_path):
            subprocess.Popen(f'explorer /select,"{os.path.abspath(audio_path)}"')

    def _open_folder(self):
        subprocess.Popen(f'explorer "{os.path.abspath(OUTPUTS_DIR)}"')

    def _go_to_page(self, page: int):
        self.current_page = max(1, min(self.total_pages, page))
        self.refresh_data()

    def _on_search_change(self):
        self.current_search = self.search_entry.get().strip()
        self.current_page = 1
        self.refresh_data()

    def _on_voice_filter_change(self, chosen_voice: str):
        self.current_voice_filter = chosen_voice
        self.current_page = 1
        self.refresh_data()

    def _on_page_size_change(self, val_str: str):
        try:
            self.page_size = int(val_str.split()[0])
        except Exception:
            self.page_size = 6
        self.current_page = 1
        self.refresh_data()
