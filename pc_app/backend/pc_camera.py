"""pc_app/backend/pc_camera.py
Captures frames from the Windows PC webcam and updates SharedState.
Only runs when `shared.pi_connected` is True.
"""

from __future__ import annotations

import time
import cv2
import config

from .state import SharedState
from .eye_processor import EyeProcessor
from .fps import FPSCounter


def run_pc_camera(shared: SharedState) -> None:
    processor = EyeProcessor()
    fps = FPSCounter()
    cap = None

    print("[Backend] PC camera thread ready (waiting for Pi trigger)...")

    while shared.running:
        # Start/stop based on Pi connection
        with shared.lock:
            active = shared.pi_connected

        if not active:
            if cap is not None:
                print("[Backend] Pi disconnected -> stopping PC camera.")
                cap.release()
                cap = None
                with shared.lock:
                    shared.pc_frame = None
                    shared.pc_has_face = False
            time.sleep(0.5)
            continue

        if cap is None:
            print("[Backend] Pi signal detected -> starting PC camera...")
            cap = cv2.VideoCapture(config.PC_CAMERA_ID, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("[Backend] Failed to open PC camera.")
                time.sleep(2.0)
                continue

        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        frame = cv2.flip(frame, 1)

        tx, ty, detected, debug_frame = processor.process(frame, source="pc", draw_debug=True)

        with shared.lock:
            shared.pc_has_face = detected
            if detected:
                shared.pc_target_x = tx
                shared.pc_target_y = ty
            shared.pc_frame = debug_frame

        maybe_fps = fps.tick()
        if maybe_fps is not None:
            with shared.lock:
                shared.pc_fps = maybe_fps

    if cap is not None:
        cap.release()
