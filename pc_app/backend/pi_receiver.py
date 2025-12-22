"""pc_app/backend/pi_receiver.py
Receives JPEG frames from Raspberry Pi via TCP and updates SharedState.
"""

from __future__ import annotations

import socket
import time
from typing import Optional, Tuple

import cv2
import numpy as np
import config

from .state import SharedState
from .eye_processor import EyeProcessor
from .transport import recv_jpeg_frame
from .fps import FPSCounter


def _decode_jpeg(jpeg_bytes: bytes) -> Optional[np.ndarray]:
    arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return frame


def run_pi_receiver(shared: SharedState) -> None:
    """Thread entry: TCP server waiting for Pi connection and receiving frames."""
    processor = EyeProcessor()
    fps = FPSCounter()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind((config.TCP_IP, config.TCP_PORT))
        server_sock.listen(1)
        print(f"[Backend] Waiting for Pi connection on port {config.TCP_PORT}...")
    except Exception as e:
        print(f"[Backend] Bind error: {e}")
        return

    conn: Optional[socket.socket] = None

    while shared.running:
        if conn is None:
            # accept
            server_sock.settimeout(1.0)
            try:
                conn, addr = server_sock.accept()
                print(f"[Backend] Pi connected from: {addr}")
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(5.0)
                with shared.lock:
                    shared.pi_connected = True
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Backend] Accept error: {e}")
                continue

        try:
            jpeg = recv_jpeg_frame(conn)
            if not jpeg:
                raise ConnectionResetError()

            frame = _decode_jpeg(jpeg)
            if frame is None:
                continue

            # Throttle processing
            # Keep it simple: process every N frames by counting at receiver level
            # (To avoid storing counter in shared, store local)
            run_pi_receiver._frame_count = getattr(run_pi_receiver, "_frame_count", 0) + 1  # type: ignore[attr-defined]
            if run_pi_receiver._frame_count % config.PROCESS_EVERY_N_FRAMES != 0:  # type: ignore[attr-defined]
                continue

            tx, ty, detected, debug_frame = processor.process(frame, source="pi", draw_debug=True)

            with shared.lock:
                shared.pi_has_face = detected
                if detected:
                    shared.pi_target_x = tx
                    shared.pi_target_y = ty
                shared.pi_frame = debug_frame

            maybe_fps = fps.tick()
            if maybe_fps is not None:
                with shared.lock:
                    shared.pi_fps = maybe_fps

        except (ConnectionResetError, BrokenPipeError, socket.timeout):
            print("[Backend] Pi disconnected.")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            conn = None
            with shared.lock:
                shared.pi_connected = False
        except Exception as e:
            print(f"[Backend] Pi stream error: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            conn = None
            with shared.lock:
                shared.pi_connected = False

    if conn:
        try:
            conn.close()
        except Exception:
            pass
    try:
        server_sock.close()
    except Exception:
        pass
