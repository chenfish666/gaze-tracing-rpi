"""pc_app/ui/debug_view.py
Optional debug window showing Pi and PC frames.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import Toplevel
from typing import Optional

import cv2
from PIL import Image, ImageTk


class DebugView:
    def __init__(self, root: tk.Tk) -> None:
        self.win = Toplevel(root)
        self.win.title("Debug View")
        self.win.geometry("700x420")
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#202020")

        self.info_label = tk.Label(self.win, text="", fg="white", bg="#202020")
        self.info_label.pack(side=tk.TOP, fill=tk.X, pady=4)

        body = tk.Frame(self.win, bg="#202020")
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg="#202020")
        left.pack(side=tk.LEFT, padx=10, pady=10)
        tk.Label(left, text="Raspberry Pi", fg="white", bg="#202020").pack()
        self.pi_canvas = tk.Canvas(left, width=320, height=240, bg="black", highlightthickness=0)
        self.pi_canvas.pack()

        right = tk.Frame(body, bg="#202020")
        right.pack(side=tk.LEFT, padx=10, pady=10)
        tk.Label(right, text="PC Webcam", fg="white", bg="#202020").pack()
        self.pc_canvas = tk.Canvas(right, width=320, height=240, bg="black", highlightthickness=0)
        self.pc_canvas.pack()

        self._pi_img_ref: Optional[ImageTk.PhotoImage] = None
        self._pc_img_ref: Optional[ImageTk.PhotoImage] = None

    def update_status(self, text: str, ok: bool) -> None:
        self.info_label.config(text=text, fg="#00FF00" if ok else "#FFFF00")

    def update_frames(self, pi_frame_bgr, pc_frame_bgr) -> None:
        self._update_canvas(self.pi_canvas, pi_frame_bgr, is_pi=True)
        self._update_canvas(self.pc_canvas, pc_frame_bgr, is_pi=False)

    def _update_canvas(self, canvas: tk.Canvas, frame_bgr, *, is_pi: bool) -> None:
        canvas.delete("all")
        if frame_bgr is None:
            return
        try:
            prev = cv2.resize(frame_bgr, (320, 240))
            rgb = cv2.cvtColor(prev, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(image=Image.fromarray(rgb))
            canvas.create_image(0, 0, image=img, anchor=tk.NW)
            if is_pi:
                self._pi_img_ref = img
            else:
                self._pc_img_ref = img
        except Exception:
            pass
