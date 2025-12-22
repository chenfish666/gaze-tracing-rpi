"""pc_app/backend/transport.py
TCP framing helpers for receiving JPEG frames.

Protocol:
- 4-byte big-endian unsigned length
- followed by JPEG bytes
"""

import socket
import struct
from typing import Optional
import config


def recv_exact(sock: socket.socket, n_bytes: int) -> Optional[bytes]:
    data = b""
    while len(data) < n_bytes:
        try:
            chunk = sock.recv(n_bytes - len(data))
            if not chunk:
                return None
            data += chunk
        except socket.timeout:
            continue
        except OSError:
            return None
    return data


def recv_jpeg_frame(sock: socket.socket) -> Optional[bytes]:
    header_size = struct.calcsize(">L")
    size_data = recv_exact(sock, header_size)
    if not size_data:
        return None

    msg_size = struct.unpack(">L", size_data)[0]
    if msg_size <= 0 or msg_size > config.MAX_JPEG_BYTES:
        # Skip invalid or too-large payload
        return None

    frame_data = recv_exact(sock, msg_size)
    return frame_data
