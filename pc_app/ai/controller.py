"""pc_app/ai/controller.py
Background AI task runner (threaded) with UI-safe callbacks.

Usage:
    ai = AIController(root)
    ai.trigger_screenshot_analysis(on_result)
"""

from __future__ import annotations
import threading
from typing import Callable

from PIL import ImageGrab
import tkinter as tk

from .gemini_agent import GeminiAgent


class AIController:
    def __init__(self, tk_root: tk.Tk) -> None:
        self._root = tk_root
        self._agent = GeminiAgent()

    def trigger_screenshot_analysis(self, on_result: Callable[[str], None]) -> None:
        """Capture screenshot and analyze in a daemon thread."""
        threading.Thread(
            target=self._worker,
            args=(on_result,),
            daemon=True,
        ).start()

    def _worker(self, on_result: Callable[[str], None]) -> None:
        try:
            screenshot = ImageGrab.grab()
            prompt = (
                "This is a screenshot the user is staring at. "
                "Identify what the user is looking at (code/video/article/etc.) "
                "and give one short helpful suggestion."
            )
            text = self._agent.analyze(screenshot, prompt=prompt)
            self._root.after(0, lambda: on_result(text))
        except Exception as e:
            self._root.after(0, lambda: on_result(f"Error: {e}"))
