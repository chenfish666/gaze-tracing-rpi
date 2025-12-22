"""pc_app/main.py
Windows PC entrypoint for Ghost Gaze.

Starts:
- Backend threads (Pi receiver + PC camera)
- UI overlay (Tkinter)
"""

import threading

from pc_app.backend import SharedState, run_pi_receiver, run_pc_camera
from pc_app.ui import GhostUI


def main() -> None:
    shared = SharedState()

    print("[Main] Starting backend threads...")
    t1 = threading.Thread(target=run_pi_receiver, args=(shared,), daemon=True)
    t2 = threading.Thread(target=run_pc_camera, args=(shared,), daemon=True)
    t1.start()
    t2.start()

    print("[Main] Starting UI...")
    ui = GhostUI(shared)
    try:
        ui.root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        shared.running = False
        print("[Main] Exiting...")


if __name__ == "__main__":
    main()
