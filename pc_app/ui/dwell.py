"""pc_app/ui/dwell.py
Dwell-trigger state machine (grid-based).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import time

import config


@dataclass
class DwellTrigger:
    threshold_sec: float = config.DWELL_THRESHOLD
    cooldown_sec: float = config.TRIGGER_COOLDOWN

    current_cell: Optional[Tuple[int, int]] = None
    dwell_start: float = 0.0
    last_trigger: float = 0.0

    def reset(self) -> None:
        self.current_cell = None
        self.dwell_start = 0.0

    def update(self, x_norm: float, y_norm: float, face_detected: bool) -> bool:
        """Update dwell state and return True if action should be triggered."""
        if not face_detected:
            self.reset()
            return False

        col = int(x_norm * config.GRID_COLS)
        row = int(y_norm * config.GRID_ROWS)
        cell = (row, col)
        now = time.time()

        if cell != self.current_cell:
            self.current_cell = cell
            self.dwell_start = now
            return False

        duration = now - self.dwell_start
        if duration >= self.threshold_sec and (now - self.last_trigger) >= self.cooldown_sec:
            self.last_trigger = now
            self.dwell_start = now  # restart
            return True

        return False

    def progress(self) -> float:
        """0..1 progress of dwell timer (for UI indicator)."""
        if self.current_cell is None:
            return 0.0
        now = time.time()
        return max(0.0, min(1.0, (now - self.dwell_start) / max(0.001, self.threshold_sec)))
