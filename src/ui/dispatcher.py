"""
Thread-safe UI Event Dispatcher for CustomTkinter.
Enables any worker thread (AI inference, model download, subprocesses)
to safely schedule execution on the main Tkinter thread without hitting
'RuntimeError: main thread is not in main loop'.
"""
import queue
from typing import Callable, Any


class UIDispatcher:
    _queue: queue.Queue = queue.Queue()

    @classmethod
    def post(cls, callback: Callable, *args: Any, **kwargs: Any) -> None:
        """Post a callback to be safely executed on the main Tkinter thread."""
        cls._queue.put((callback, args, kwargs))

    @classmethod
    def process_pending(cls) -> None:
        """Pumps and executes all pending queued UI callbacks on the main thread."""
        while not cls._queue.empty():
            try:
                callback, args, kwargs = cls._queue.get_nowait()
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Error in UIDispatcher callback: {e}")

