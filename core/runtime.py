from __future__ import annotations

import random
import threading


class CancelledError(InterruptedError):
    """Raised when the user requests cancellation."""


class RuntimeControl:
    def __init__(self, stop_event: threading.Event, logger):
        self.stop_event = stop_event
        self.log = logger

    def check_stop(self) -> None:
        if self.stop_event.is_set():
            raise CancelledError("User stopped")

    def sleep(self, seconds: float) -> None:
        if seconds <= 0:
            self.check_stop()
            return
        if self.stop_event.wait(seconds):
            raise CancelledError("User stopped")

    def sleep_random(self, minimum: float, maximum: float) -> None:
        self.sleep(random.uniform(minimum, maximum))
