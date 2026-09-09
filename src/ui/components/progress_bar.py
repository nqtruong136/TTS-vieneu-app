"""
Progress Display Widget for CustomTkinter GUI.
Binds to ProgressTracker to show exact percentage, progress bar animation, and stage text.
"""
from typing import Optional
import customtkinter as ctk

from ...core.progress import ProgressTracker, ProgressState
from ..styles import COLORS, FONTS
from ..dispatcher import UIDispatcher


class ProgressDisplay(ctk.CTkFrame):
    def __init__(
        self,
        master,
        tracker: Optional[ProgressTracker] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._tracker: Optional[ProgressTracker] = None
        self._create_widgets()

        if tracker:
            self.bind_tracker(tracker)

    def _create_widgets(self):
        # Header row: Status message (left) + Percentage label (right)
        info_row = ctk.CTkFrame(self, fg_color="transparent")
        info_row.pack(fill="x", pady=(0, 3))

        self.msg_label = ctk.CTkLabel(
            info_row,
            text="Sẵn sàng",
            font=FONTS["caption"],
            text_color="gray",
            anchor="w"
        )
        self.msg_label.pack(side="left", fill="x", expand=True)

        self.percent_label = ctk.CTkLabel(
            info_row,
            text="0%",
            font=("Segoe UI", 11, "bold"),
            text_color=COLORS["primary"],
            anchor="e"
        )
        self.percent_label.pack(side="right")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=6,
            corner_radius=3,
            progress_color=COLORS["primary"]
        )
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x")

    def bind_tracker(self, tracker: ProgressTracker) -> None:
        """Gắn với một ProgressTracker để tự động cập nhật UI."""
        if self._tracker:
            self._tracker.unsubscribe(self._on_tracker_update)
        self._tracker = tracker
        self._tracker.subscribe(self._on_tracker_update)
        self._render_state(self._tracker.get_state())

    def _on_tracker_update(self, state: ProgressState):
        UIDispatcher.post(self._render_state, state)

    def _render_state(self, state: ProgressState):
        percent_val = state.percent / 100.0
        self.progress_bar.set(percent_val)
        self.percent_label.configure(text=f"{int(state.percent)}%")

        msg = state.message
        if state.stage:
            msg = f"[{state.stage}] {msg}"

        if state.is_error:
            self.msg_label.configure(text=msg, text_color=COLORS["danger"])
            self.percent_label.configure(text_color=COLORS["danger"])
            self.progress_bar.configure(progress_color=COLORS["danger"])
        elif state.percent >= 100.0:
            self.msg_label.configure(text=msg, text_color=COLORS["secondary"])
            self.percent_label.configure(text_color=COLORS["secondary"])
            self.progress_bar.configure(progress_color=COLORS["secondary"])
        else:
            self.msg_label.configure(text=msg, text_color="#D1D5DB")
            self.percent_label.configure(text_color=COLORS["primary"])
            self.progress_bar.configure(progress_color=COLORS["primary"])

    def set_progress(self, percent: float, message: str = ""):
        """Cập nhật trực tiếp không qua tracker nếu muốn."""
        percent = max(0.0, min(100.0, percent))
        self.progress_bar.set(percent / 100.0)
        self.percent_label.configure(text=f"{int(percent)}%")
        if message:
            self.msg_label.configure(text=message)

