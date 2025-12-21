"""pi_app/camera_streamer.py
Picamera2 -> JPEG -> TCP streaming.
"""

from __future__ import annotations

import socket
import struct
import time

import cv2
from picamera2 import Picamera2

from .state import SystemState
from . import config


def run_camera_streamer(state: SystemState) -> None:
    print("[Camera] Thread started. Waiting for activation...")

    while state.running:
        if not state.streaming:
            time.sleep(0.5)
            continue

        try:
            print("[Camera] Initializing Picamera2...")
            picam2 = Picamera2()
            cam_cfg = picam2.create_video_configuration(
                main={"size": (config.RES_W, config.RES_H), "format": "RGB888"}
            )
            picam2.configure(cam_cfg)
            picam2.start()

            print(f"[Camera] Connecting to PC {config.PC_IP}:{config.PC_PORT}...")
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client.settimeout(5.0)

            try:
                client.connect((config.PC_IP, config.PC_PORT))
                print("[Camera] Connected. Streaming video...")

                while state.running and state.streaming:
                    frame = picam2.capture_array()
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                    ok, enc = cv2.imencode(
                        ".jpg",
                        frame_bgr,
                        [int(cv2.IMWRITE_JPEG_QUALITY), int(config.JPEG_QUALITY)],
                    )
                    if not ok:
                        continue

                    data = enc.tobytes()
                    header = struct.pack(">L", len(data))
                    client.sendall(header + data)

            except (BrokenPipeError, ConnectionResetError, socket.timeout) as e:
                print(f"[Camera] Connection lost: {e}")
            finally:
                try:
                    client.close()
                except Exception:
                    pass
                try:
                    picam2.stop()
                    picam2.close()
                except Exception:
                    pass
                print("[Camera] Stopped/disconnected.")
                time.sleep(2)

        except Exception as e:
            print(f"[Camera] Error: {e}")
            time.sleep(2)
