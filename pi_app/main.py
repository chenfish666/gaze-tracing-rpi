"""pi_app/main.py
Raspberry Pi entrypoint.
"""

import threading

from .state import SystemState
from .camera_streamer import run_camera_streamer
from .voice_wakeup import run_voice_loop


def main() -> None:
    state = SystemState()

    t_cam = threading.Thread(target=run_camera_streamer, args=(state,), daemon=True)
    t_cam.start()

    run_voice_loop(state)


if __name__ == "__main__":
    main()
