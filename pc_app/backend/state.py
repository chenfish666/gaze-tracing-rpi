"""pc_app/backend/state.py
Thread-safe shared state for backend threads and UI thread.
"""

from __future__ import annotations
import threading
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class SharedState:
    """Shared state between:
    - Pi receiver thread (TCP)
    - PC webcam thread
    - UI thread (Tkinter)

    All reads/writes must be protected with `lock`.
    """

    lock: threading.Lock = field(default_factory=threading.Lock)
    running: bool = True

    # ---- Connection Status ----
    pi_connected: bool = False

    # ---- Raspberry Pi Tracking Data ----
    pi_frame: Optional[np.ndarray] = None   # debug frame
    pi_has_face: bool = False
    pi_target_x: float = 0.5
    pi_target_y: float = 0.5
    pi_fps: int = 0

    # ---- PC Webcam Tracking Data ----
    pc_frame: Optional[np.ndarray] = None
    pc_has_face: bool = False
    pc_target_x: float = 0.5
    pc_target_y: float = 0.5
    pc_fps: int = 0
