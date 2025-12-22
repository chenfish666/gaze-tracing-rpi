"""pc_app/ui/ghost_ui.py
Transparent overlay UI that renders gaze dot and triggers AI via dwell.

Responsibilities:
- UI rendering (dot/grid/optional debug window)
- Read SharedState, fuse gaze coords, smoothing
- Orchestrate Calibration + DwellTrigger + AIController
"""

from __future__ import annotations

import tkinter as tk
import time
from typing import Optional, Tuple

import config
from pc_app.backend.state import SharedState
from pc_app.ui.calibration import Calibrator
from pc_app.ui.dwell import DwellTrigger
from pc_app.ui.debug_view import DebugView
from pc_app.ai import AIController


class GhostUI:
    def __init__(self, shared: SharedState) -> None:
        self.shared = shared
        self.calibrator = Calibrator()
        self.dwell = DwellTrigger()

        self.root = tk.Tk()
        self.root.title("Ghost Gaze UI")
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.overrideredirect(True)
        self.root.configure(bg="black")

        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.sw}x{self.sh}+0+0")

        self.canvas = tk.Canvas(self.root, width=self.sw, height=self.sh, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.dot = self.canvas.create_oval(0, 0, 0, 0, fill="red", outline="")
        self._draw_grid()

        self.debug: Optional[DebugView] = None
        if config.SHOW_DEBUG_VIEW:
            self.debug = DebugView(self.root)

        self.ai = AIController(self.root)

        # Calibration UI state
        self.is_calibrating = False
        self.calib_step = 0
        self.calib_timer = 0.0
        self.calib_msg = self.canvas.create_text(
            self.sw // 2, self.sh // 2, text="", fill="yellow", font=("Arial", 30, "bold")
        )
        self.calib_target = self.canvas.create_oval(
            0, 0, 0, 0, fill="cyan", outline="white", width=3, state="hidden"
        )
        self.calib_coords = [(50, 50), (self.sw - 50, 50), (50, self.sh - 50), (self.sw - 50, self.sh - 50)]

        # Smoothed cursor
        self.cur_x = 0.5
        self.cur_y = 0.5

        # Dwell indicator
        self.dwell_indicator = None

        # Bind keys
        self.root.bind("c", self.start_calibration)
        self.root.bind("C", self.start_calibration)
        self.root.bind("<Escape>", self._quit)
        self.root.focus_force()

        self.root.after(config.FRAME_DELAY_MS, self._update_loop)
        print("[UI] Ghost UI started.")

    # ---------------- UI Drawing ----------------
    def _draw_grid(self) -> None:
        cw = self.sw / config.GRID_COLS
        ch = self.sh / config.GRID_ROWS
        color = "#404040"
        for i in range(1, config.GRID_COLS):
            self.canvas.create_line(i * cw, 0, i * cw, self.sh, fill=color, dash=(4, 4))
        for j in range(1, config.GRID_ROWS):
            self.canvas.create_line(0, j * ch, self.sw, j * ch, fill=color, dash=(4, 4))

    def _draw_dot(self, x_norm: float, y_norm: float, *, visible: bool) -> Tuple[int, int]:
        if not visible:
            self.canvas.itemconfig(self.dot, state="hidden")
            return int(self.sw * 0.5), int(self.sh * 0.5)

        self.canvas.itemconfig(self.dot, state="normal")
        px = int(x_norm * self.sw)
        py = int(y_norm * self.sh)
        r = config.DOT_RADIUS
        self.canvas.coords(self.dot, px - r, py - r, px + r, py + r)
        return px, py

    # ---------------- Shared State Read ----------------
    def _read_state(self):
        with self.shared.lock:
            active = self.shared.pi_connected
            pi_ok = self.shared.pi_has_face
            pc_ok = self.shared.pc_has_face
            pi_pos = (self.shared.pi_target_x, self.shared.pi_target_y)
            pc_pos = (self.shared.pc_target_x, self.shared.pc_target_y)
            pi_frame = self.shared.pi_frame.copy() if self.shared.pi_frame is not None else None
            pc_frame = self.shared.pc_frame.copy() if self.shared.pc_frame is not None else None
            pi_fps = self.shared.pi_fps
            pc_fps = self.shared.pc_fps
        return active, pi_ok, pc_ok, pi_pos, pc_pos, pi_frame, pc_frame, pi_fps, pc_fps

    def _fuse_gaze(self, pi_ok, pc_ok, pi_pos, pc_pos) -> Tuple[float, float, bool]:
        if pi_ok and pc_ok:
            return (pi_pos[0] + pc_pos[0]) / 2.0, (pi_pos[1] + pc_pos[1]) / 2.0, True
        if pi_ok:
            return pi_pos[0], pi_pos[1], True
        if pc_ok:
            return pc_pos[0], pc_pos[1], True
        return self.cur_x, self.cur_y, False

    # ---------------- Main Loop ----------------
    def _update_loop(self) -> None:
        if not self.shared.running:
            return

        active, pi_ok, pc_ok, pi_pos, pc_pos, pi_frame, pc_frame, pi_fps, pc_fps = self._read_state()

        if self.debug is not None:
            status = "Connected" if active else "Waiting for Wake Word..."
            self.debug.update_status(f"Status: {status} | Pi FPS: {pi_fps} | PC FPS: {pc_fps}", ok=active)
            self.debug.update_frames(pi_frame, pc_frame)

        if not active:
            # Hide dot, reset dwell state to avoid accidental trigger on reconnect
            self._draw_dot(self.cur_x, self.cur_y, visible=False)
            self.dwell.reset()
            if self.dwell_indicator:
                self.canvas.delete(self.dwell_indicator)
                self.dwell_indicator = None
            self.root.after(config.FRAME_DELAY_MS, self._update_loop)
            return

        raw_x, raw_y, has_face = self._fuse_gaze(pi_ok, pc_ok, pi_pos, pc_pos)

        if self.is_calibrating:
            self._handle_calibration(raw_x, raw_y)
            self.root.after(config.FRAME_DELAY_MS, self._update_loop)
            return

        # Calibration mapping + smoothing
        target_x, target_y = self.calibrator.map(raw_x, raw_y)
        self.cur_x += (target_x - self.cur_x) * config.SMOOTHING_FACTOR
        self.cur_y += (target_y - self.cur_y) * config.SMOOTHING_FACTOR

        px, py = self._draw_dot(self.cur_x, self.cur_y, visible=True)

        # Dwell trigger logic (only if a face is detected somewhere)
        triggered = self.dwell.update(self.cur_x, self.cur_y, face_detected=has_face)
        self._update_dwell_indicator(px, py, has_face)

        if triggered:
            self._trigger_ai()

        self.root.after(config.FRAME_DELAY_MS, self._update_loop)

    def _update_dwell_indicator(self, px: int, py: int, has_face: bool) -> None:
        if not has_face:
            if self.dwell_indicator:
                self.canvas.delete(self.dwell_indicator)
                self.dwell_indicator = None
            return

        prog = self.dwell.progress()
        if prog > 0.25 and self.dwell_indicator is None:
            self.dwell_indicator = self.canvas.create_oval(px - 30, py - 30, px + 30, py + 30, outline="yellow", width=3)
        if prog < 0.05 and self.dwell_indicator is not None:
            # cell changed; reset indicator
            self.canvas.delete(self.dwell_indicator)
            self.dwell_indicator = None

    # ---------------- Calibration Flow ----------------
    def start_calibration(self, event=None) -> None:
        print("[Calibration] Starting calibration...")
        self.is_calibrating = True
        self.calib_step = 0
        self.calibrator.points = []
        self.canvas.itemconfig(self.dot, state="hidden")
        self.canvas.itemconfig(self.calib_target, state="normal")
        self._next_calib_step()

    def _next_calib_step(self) -> None:
        if self.calib_step >= 4:
            self.is_calibrating = False
            self.calibrator.update_from_points(self.calibrator.points)
            self.canvas.itemconfig(self.calib_msg, text="Done!", fill="green")
            self.canvas.itemconfig(self.calib_target, state="hidden")
            self.canvas.itemconfig(self.dot, state="normal")
            self.root.after(1500, lambda: self.canvas.itemconfig(self.calib_msg, text=""))
            return

        tx, ty = self.calib_coords[self.calib_step]
        self.canvas.coords(self.calib_target, tx - 20, ty - 20, tx + 20, ty + 20)
        msg = ["Look Top-Left", "Look Top-Right", "Look Bottom-Left", "Look Bottom-Right"][self.calib_step]
        self.canvas.itemconfig(self.calib_msg, text=msg, fill="yellow")
        self.calib_timer = time.time()

    def _handle_calibration(self, raw_x: float, raw_y: float) -> None:
        if time.time() - self.calib_timer >= config.CALIBRATION_DWELL_SEC:
            print(f"[Calibration] Recorded step {self.calib_step}: {raw_x:.4f}, {raw_y:.4f}")
            self.calibrator.points.append((raw_x, raw_y))
            self.calib_step += 1
            self._next_calib_step()

    # ---------------- AI Trigger ----------------
    def _trigger_ai(self) -> None:
        print("\n" + "=" * 40)
        print(">>> [AI] Dwell triggered. Analyzing screenshot... <<<")
        print("=" * 40)

        # Visual feedback
        self.canvas.itemconfig(self.dot, fill="#00FF00")
        self.root.update()

        self.ai.trigger_screenshot_analysis(self._on_ai_result)

    def _on_ai_result(self, text: str) -> None:
        print("\n" + "-" * 40)
        print("[Gemini result]:")
        print(text)
        print("-" * 40 + "\n")

        self.canvas.itemconfig(self.dot, fill="red")

    def _quit(self, event=None) -> None:
        print("[System] Exiting...")
        self.shared.running = False
        self.root.quit()
        import os
        os._exit(0)
