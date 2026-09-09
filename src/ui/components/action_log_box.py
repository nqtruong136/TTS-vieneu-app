"""
ActionLogBox component for CustomTkinter GUI.
Renders contextual logs and status right at the action/trigger location:
- Visual state badge (Loading, Success, Warning, Error)
- Friendly user-facing explanation and troubleshooting suggestions
- Mini log stream of the specific triggered action
- Collapsible Technical Details / Exception Traceback with 1-click Copy
"""
from datetime import datetime
from typing import Optional, List
import customtkinter as ctk

from ..styles import COLORS, FONTS


class ActionLogBox(ctk.CTkFrame):
    """
    Contextual Action Log & Status Box placed right where user triggers an action.
    """
    def __init__(
        self,
        master,
        title: str = "Trạng thái",
        auto_hide_on_start: bool = True,
        **kwargs
    ):
        super().__init__(
            master,
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border_dark"],
            fg_color=COLORS["card_bg_dark"],
            **kwargs
        )

        self.default_title = title
        self._current_traceback: Optional[str] = None
        self._is_traceback_visible = False
        self._log_lines: List[str] = []

        self._create_widgets()
        # Mặc định ẩn cho đến khi có hành động
        self.pack_forget()

    def _create_widgets(self):
        # 1. Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=12, pady=(8, 4))

        self.icon_label = ctk.CTkLabel(
            self.header_frame,
            text="ℹ️",
            font=("Segoe UI", 13, "bold"),
            width=24
        )
        self.icon_label.pack(side="left", padx=(0, 6))

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=self.default_title,
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["primary"],
            anchor="w"
        )
        self.title_label.pack(side="left", fill="x", expand=True)

        self.time_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=FONTS["caption"],
            text_color="gray"
        )
        self.time_label.pack(side="left", padx=8)

        # Nút đóng
        self.btn_close = ctk.CTkButton(
            self.header_frame,
            text="✕",
            width=22,
            height=22,
            font=("Segoe UI", 10, "bold"),
            fg_color="transparent",
            text_color="gray",
            hover_color=COLORS["border_dark"],
            command=self.hide
        )
        self.btn_close.pack(side="right")

        # 2. Main Message Label
        self.msg_label = ctk.CTkLabel(
            self,
            text="",
            font=FONTS["body"],
            text_color="#E5E7EB",
            wraplength=650,
            justify="left",
            anchor="w"
        )
        self.msg_label.pack(fill="x", padx=14, pady=(2, 4))

        # 3. Suggestion Box (Gợi ý khắc phục khi gặp lỗi)
        self.suggestion_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=6, border_width=1, border_color="#334155")
        self.suggestion_label = ctk.CTkLabel(
            self.suggestion_frame,
            text="",
            font=FONTS["caption"],
            text_color="#38BDF8",
            wraplength=630,
            justify="left",
            anchor="w"
        )
        self.suggestion_label.pack(fill="x", padx=10, pady=6)

        # 4. Mini Log Stream Box (Hiển thị các bước chạy của action)
        self.stream_box = ctk.CTkTextbox(
            self,
            height=65,
            font=("Consolas", 10),
            wrap="none",
            corner_radius=6,
            fg_color="#0F172A",
            border_width=0
        )

        # 5. Technical Details Toolbar (Toggle Traceback + Copy)
        self.details_toolbar = ctk.CTkFrame(self, fg_color="transparent")

        self.btn_toggle_traceback = ctk.CTkButton(
            self.details_toolbar,
            text="🔍 Xem chi tiết ngoại lệ (Traceback) ▼",
            height=24,
            font=FONTS["caption"],
            fg_color="transparent",
            text_color="gray",
            hover_color="#1E293B",
            command=self._toggle_traceback
        )
        self.btn_toggle_traceback.pack(side="left")

        self.btn_copy_traceback = ctk.CTkButton(
            self.details_toolbar,
            text="📋 Sao chép lỗi",
            width=80,
            height=24,
            font=FONTS["caption"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border_dark"],
            command=self._copy_traceback
        )
        self.btn_copy_traceback.pack(side="right")

        # 6. Traceback Textbox (ẩn mặc định)
        self.traceback_box = ctk.CTkTextbox(
            self,
            height=120,
            font=("Consolas", 10),
            wrap="none",
            corner_radius=6,
            fg_color="#020617",
            border_width=1,
            border_color="#991B1B"
        )

    def show(self):
        if not self.winfo_ismapped():
            self.pack(fill="x", padx=14, pady=6)

    def hide(self):
        self.pack_forget()

    def clear(self):
        self._log_lines.clear()
        self.stream_box.delete("1.0", "end")
        self.stream_box.pack_forget()
        self.suggestion_frame.pack_forget()
        self.details_toolbar.pack_forget()
        self.traceback_box.pack_forget()
        self._current_traceback = None
        self._is_traceback_visible = False

    def show_loading(self, title: str, message: str):
        """Hiển thị trạng thái đang xử lý tại trigger."""
        self.clear()
        self.show()
        now_str = datetime.now().strftime("%H:%M:%S")

        self.configure(border_color=COLORS["primary"])
        self.icon_label.configure(text="⏳")
        self.title_label.configure(text=title, text_color=COLORS["primary"])
        self.time_label.configure(text=now_str)
        self.msg_label.configure(text=message, text_color="#E5E7EB")

    def append_log(self, text: str):
        """In thêm 1 dòng log vào stream của tác vụ này."""
        self.show()
        now_str = datetime.now().strftime("%H:%M:%S")
        line = f"[{now_str}] {text.strip()}\n"
        self._log_lines.append(line)

        if not self.stream_box.winfo_ismapped():
            self.stream_box.pack(fill="x", padx=14, pady=(4, 6))

        self.stream_box.insert("end", line)
        self.stream_box.see("end")

    def show_success(self, title: str, message: str, details: Optional[str] = None):
        """Hiển thị thông báo thành công."""
        self.show()
        now_str = datetime.now().strftime("%H:%M:%S")

        self.configure(border_color=COLORS["secondary"])
        self.icon_label.configure(text="✅")
        self.title_label.configure(text=title, text_color=COLORS["secondary"])
        self.time_label.configure(text=now_str)
        self.msg_label.configure(text=message, text_color="#A7F3D0")

        self.suggestion_frame.pack_forget()
        self.details_toolbar.pack_forget()
        self.traceback_box.pack_forget()

        if details:
            self.append_log(details)

    def show_warning(self, title: str, message: str, suggestion: Optional[str] = None):
        """Hiển thị thông báo cảnh báo."""
        self.show()
        now_str = datetime.now().strftime("%H:%M:%S")

        self.configure(border_color="#F59E0B")
        self.icon_label.configure(text="⚠️")
        self.title_label.configure(text=title, text_color="#F59E0B")
        self.time_label.configure(text=now_str)
        self.msg_label.configure(text=message, text_color="#FDE68A")

        if suggestion:
            self.suggestion_label.configure(text=f"💡 GỢI Ý: {suggestion}")
            self.suggestion_frame.pack(fill="x", padx=14, pady=(4, 6))
        else:
            self.suggestion_frame.pack_forget()

        self.details_toolbar.pack_forget()
        self.traceback_box.pack_forget()

    def show_error(
        self,
        title: str,
        message: str,
        traceback_str: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        """Hiển thị thông báo lỗi nổi bật kèm gợi ý và traceback kỹ thuật."""
        self.show()
        now_str = datetime.now().strftime("%H:%M:%S")

        self.configure(border_color=COLORS["danger"])
        self.icon_label.configure(text="❌")
        self.title_label.configure(text=title, text_color=COLORS["danger"])
        self.time_label.configure(text=now_str)
        self.msg_label.configure(text=message, text_color="#FCA5A5")

        # Suggestion box
        if suggestion:
            self.suggestion_label.configure(text=f"💡 HƯỚNG DẪN KHẮC PHỤC: {suggestion}")
            self.suggestion_frame.pack(fill="x", padx=14, pady=(4, 6))
        else:
            self.suggestion_frame.pack_forget()

        # Traceback
        if traceback_str:
            self._current_traceback = traceback_str
            self.traceback_box.delete("1.0", "end")
            self.traceback_box.insert("1.0", traceback_str)
            self.details_toolbar.pack(fill="x", padx=14, pady=(4, 6))
        else:
            self.details_toolbar.pack_forget()
            self.traceback_box.pack_forget()

    def _toggle_traceback(self):
        if self._is_traceback_visible:
            self.traceback_box.pack_forget()
            self.btn_toggle_traceback.configure(text="🔍 Xem chi tiết ngoại lệ (Traceback) ▼")
            self._is_traceback_visible = False
        else:
            self.traceback_box.pack(fill="x", padx=14, pady=(0, 6))
            self.btn_toggle_traceback.configure(text="▲ Thu gọn chi tiết ngoại lệ")
            self._is_traceback_visible = True

    def _copy_traceback(self):
        content = self._current_traceback or self.msg_label.cget("text")
        self.clipboard_clear()
        self.clipboard_append(content)
        self.btn_copy_traceback.configure(text="✅ Đã chép!")
        self.after(1500, lambda: self.btn_copy_traceback.configure(text="📋 Sao chép lỗi"))

