"""pc_app/backend/fps.py
Small utility to compute FPS without duplicating timer code.
"""

import time
from typing import Optional


class FPSCounter:
    def __init__(self, interval_sec: float = 1.0) -> None:
        self.interval_sec = interval_sec
        self._count = 0
        self._last = time.time()

    def tick(self) -> Optional[int]:
        """Call once per processed frame. Returns FPS once per interval."""
        self._count += 1
        now = time.time()
        if now - self._last >= self.interval_sec:
            fps = self._count
            self._count = 0
            self._last = now
            return fps
        return None
