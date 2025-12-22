"""backend.py (compat wrapper)
Kept for backwards compatibility with your original imports.

New modules live under:
    pc_app/backend/
"""

from pc_app.backend import SharedState, run_pi_receiver as pi_thread_func, run_pc_camera as pc_thread_func

__all__ = ["SharedState", "pi_thread_func", "pc_thread_func"]
