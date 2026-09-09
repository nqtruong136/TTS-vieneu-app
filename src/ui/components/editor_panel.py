"""
Editor Panel component for text input, emotion tag insertion, and synthesis trigger.
Integrated with ProgressDisplay for percentage and stage visibility.
"""
from typing import Callable, Optional
import customtkinter as ctk

from ...config import EMOTION_TAGS, DEFAULT_SAMPLE_TEXT
from ..styles import COLORS, FONTS
from .progress_bar import ProgressDisplay
from .action_log_box import ActionLogBox
from ...core.progress import ProgressTracker


class EditorPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_generate: Optional[Callable[[str], None]] = None,
        progress_tracker: Optional[ProgressTracker] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.on_generate = on_generate
        self._progress_tracker = progress_tracker
        self._create_widgets()

    def _create_widgets(self):
        # 1. Header with character count and quick action buttons
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 6))

        title_label = ctk.CTkLabel(
            header_frame,
            text="📝 SOẠN THẢO VĂN BẢN TIẾNG VIỆT",
            font=FONTS["header"]
        )
        title_label.pack(side="left")

        self.char_count_label = ctk.CTkLabel(
            header_frame,
            text="0 ký tự",
            font=FONTS["caption"],
            text_color="gray"
        )
        self.char_count_label.pack(side="left", padx=12)

        # Quick action buttons in header
        btn_sample = ctk.CTkButton(
            header_frame,
            text="📄 Đoạn mẫu",
            width=80,
            height=26,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._load_sample_text
        )
        btn_sample.pack(side="right", padx=(4, 0))

        btn_clear = ctk.CTkButton(
            header_frame,
            text="✕ Xóa hết",
            width=70,
            height=26,
            font=FONTS["caption"],
            fg_color="transparent",
            text_color=COLORS["danger"],
            border_width=1,
            border_color=COLORS["danger"],
            hover_color=COLORS["card_bg_dark"],
            command=self._clear_text
        )
        btn_clear.pack(side="right", padx=(4, 0))

        # 2. Multiline Textbox
        self.textbox = ctk.CTkTextbox(
            self,
            font=("Segoe UI", 13),
            wrap="word",
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"]
        )
        self.textbox.pack(fill="both", expand=True, pady=(0, 8))
        self.textbox.bind("<KeyRelease>", self._on_text_change)

        # 3. Emotion Tags Toolbar
        emotion_frame = ctk.CTkFrame(self, fg_color="transparent")
        emotion_frame.pack(fill="x", pady=(0, 10))

        tag_label = ctk.CTkLabel(
            emotion_frame,
            text="Chèn cảm xúc:",
            font=FONTS["caption"],
            text_color="gray"
        )
        tag_label.pack(side="left", padx=(0, 8))

        for item in EMOTION_TAGS:
            btn_tag = ctk.CTkButton(
                emotion_frame,
                text=f"+ {item['label']}",
                height=28,
                font=FONTS["caption"],
                fg_color=COLORS["card_bg_dark"],
                hover_color=COLORS["accent_badge"],
                border_width=1,
                border_color=COLORS["border_dark"],
                command=lambda t=item["tag"]: self._insert_tag(t)
            )
            btn_tag.pack(side="left", padx=3)

        # 4. Action and Progress Bar with Percentage
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 4))

        self.btn_generate = ctk.CTkButton(
            action_frame,
            text="🔊 BẮT ĐẦU TẠO GIỌNG NÓI  (Ctrl + Enter)",
            height=44,
            font=("Segoe UI", 13, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=8,
            command=self._handle_generate_click
        )
        self.btn_generate.pack(fill="x")

        # Dynamic Percentage Progress Display
        self.progress_display = ProgressDisplay(
            self,
            tracker=self._progress_tracker
        )
        self.progress_display.pack(fill="x", pady=(6, 0))

        # Contextual Action Log Box at Trigger
        self.action_log_box = ActionLogBox(
            self,
            title="Trạng thái sinh giọng nói"
        )

        # Nạp văn bản mẫu ban đầu
        self._load_sample_text()

    def _insert_tag(self, tag: str):
        """Chèn thẻ cảm xúc vào vị trí con trỏ hiện tại."""
        try:
            self.textbox.insert("insert", f" {tag} ")
            self.textbox.focus_set()
            self._update_char_count()
        except Exception as e:
            print(f"Error inserting tag: {e}")

    def _on_text_change(self, event=None):
        self._update_char_count()

    def _update_char_count(self):
        text = self.get_text()
        count = len(text.strip())
        word_count = len(text.strip().split()) if count > 0 else 0
        self.char_count_label.configure(text=f"{count} ký tự • {word_count} từ")

    def _load_sample_text(self):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", DEFAULT_SAMPLE_TEXT)
        self._update_char_count()

    def _clear_text(self):
        self.textbox.delete("1.0", "end")
        self._update_char_count()

    def set_text(self, text: str):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        self._update_char_count()

    def get_text(self) -> str:
        return self.textbox.get("1.0", "end-1c")

    def _handle_generate_click(self):
        text = self.get_text().strip()
        if self.on_generate:
            self.on_generate(text)

    def set_generating_state(self, is_generating: bool):
        if is_generating:
            self.btn_generate.configure(
                state="disabled",
                text="⏳ Đang tổng hợp giọng nói...",
                fg_color="gray"
            )
        else:
            self.btn_generate.configure(
                state="normal",
                text="🔊 BẮT ĐẦU TẠO GIỌNG NÓI  (Ctrl + Enter)",
                fg_color=COLORS["primary"]
            )

    def set_status(self, message: str, is_error: bool = False):
        if is_error:
            self.progress_display.msg_label.configure(text=message, text_color=COLORS["danger"])
        else:
            color = COLORS["secondary"] if ("Hoàn thành" in message or "thành công" in message.lower()) else "#D1D5DB"
            self.progress_display.msg_label.configure(text=message, text_color=color)
