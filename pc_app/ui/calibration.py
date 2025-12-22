"""pc_app/ui/calibration.py
Calibration mapping (raw gaze -> normalized screen coords) with persistence.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple
import json
import os

import config


@dataclass
class Calibrator:
    calib_file: str = config.CALIBRATION_FILE
    x_min: float = 0.3
    x_max: float = 0.7
    y_min: float = 0.35
    y_max: float = 0.60
    points: List[Tuple[float, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.load()

    def map(self, raw_x: float, raw_y: float) -> Tuple[float, float]:
        """Map raw normalized gaze values into [0, 1] range using calibration bounds."""
        norm_x = (raw_x - self.x_min) / (self.x_max - self.x_min)
        norm_y = (raw_y - self.y_min) / (self.y_max - self.y_min)
        return self._clip01(norm_x), self._clip01(norm_y)

    def update_from_points(self, points: List[Tuple[float, float]]) -> None:
        if len(points) < 4:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        buf = config.CALIBRATION_BUFFER
        self.x_min = min(xs) + buf
        self.x_max = max(xs) - buf
        self.y_min = min(ys) + buf
        self.y_max = max(ys) - buf
        print(f"[Calibration] Updated range: X({self.x_min:.3f}-{self.x_max:.3f}), Y({self.y_min:.3f}-{self.y_max:.3f})")
        self.save()

    def save(self) -> None:
        data = {"x_min": self.x_min, "x_max": self.x_max, "y_min": self.y_min, "y_max": self.y_max}
        with open(self.calib_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> None:
        if not os.path.exists(self.calib_file):
            return
        try:
            with open(self.calib_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.x_min = float(data["x_min"])
            self.x_max = float(data["x_max"])
            self.y_min = float(data["y_min"])
            self.y_max = float(data["y_max"])
            print("[Calibration] Loaded existing profile.")
        except Exception:
            pass

    @staticmethod
    def _clip01(v: float) -> float:
        return max(0.0, min(1.0, v))
