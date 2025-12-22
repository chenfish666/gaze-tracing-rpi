"""
pc_app/backend/eye_processor.py
MediaPipe Face Landmarker (Tasks API) based iris tracking and normalization.

This module does NOT:
- manage sockets
- manage cameras
- manage UI
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

import config


@dataclass(frozen=True)
class NormalizeRange:
    x_min: float
    x_max: float
    y_min: float
    y_max: float


class EyeProcessor:
    """
    EyeProcessor encapsulates MediaPipe Face Landmarker and
    converts iris landmark position into normalized gaze coordinates.
    """

    def __init__(self) -> None:
        # ---- MediaPipe Tasks Face Landmarker ----
        base_options = python.BaseOptions(
            model_asset_path=None  # use default bundled model
        )

        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )

        self._detector = vision.FaceLandmarker.create_from_options(options)

        # ---- Normalization ranges ----
        self._range_pi = NormalizeRange(
            config.PI_X_MIN,
            config.PI_X_MAX,
            config.PI_Y_MIN,
            config.PI_Y_MAX,
        )
        self._range_pc = NormalizeRange(
            config.PC_X_MIN,
            config.PC_X_MAX,
            config.PC_Y_MIN,
            config.PC_Y_MAX,
        )

    def process(
        self,
        frame_bgr: Optional[np.ndarray],
        *,
        source: str,
        draw_debug: bool = True,
    ) -> Tuple[float, float, bool, Optional[np.ndarray]]:
        """
        Process a BGR frame and return (x, y, detected, debug_frame).

        Args:
            frame_bgr: OpenCV BGR frame.
            source: "pi" or "pc" (affects normalization range).
            draw_debug: If True, draws a marker at iris center.

        Returns:
            target_x, target_y in [0, 1], face_detected, debug_frame (or None)
        """
        if frame_bgr is None:
            return 0.5, 0.5, False, None

        h, w = frame_bgr.shape[:2]

        # ---- Convert to MediaPipe Image ----
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

        # ---- Face landmark detection ----
        result = self._detector.detect(mp_image)

        target_x, target_y = 0.5, 0.5
        detected = False
        debug_frame = frame_bgr.copy() if draw_debug else None

        if result.face_landmarks:
            detected = True
            landmarks = result.face_landmarks[0]

            # Iris center landmark (same index as before)
            pt = landmarks[config.IRIS_LANDMARK_INDEX]

            # Select normalization range
            r = self._range_pi if source == "pi" else self._range_pc

            # Normalize to [0, 1]
            norm_x = (pt.x - r.x_min) / (r.x_max - r.x_min)
            norm_y = (pt.y - r.y_min) / (r.y_max - r.y_min)

            target_x = max(0.0, min(1.0, norm_x))
            target_y = max(0.0, min(1.0, norm_y))

            if debug_frame is not None:
                cx, cy = int(pt.x * w), int(pt.y * h)
                cv2.circle(debug_frame, (cx, cy), 4, (0, 255, 0), -1)

        return target_x, target_y, detected, debug_frame
