"""pc_app/ai/gemini_agent.py
Gemini client wrapper.

Keep this module small so you can swap to another LLM later.
"""

from __future__ import annotations
from typing import Union, Optional

import numpy as np
import cv2
from PIL import Image

import config

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None


class GeminiAgent:
    def __init__(self) -> None:
        if not config.GEMINI_API_KEY:
            print("[AI] Warning: GEMINI_API_KEY not set. AI features disabled.")
            self._model = None
            return

        if genai is None:
            print("[AI] Warning: google-generativeai not installed. AI features disabled.")
            self._model = None
            return

        genai.configure(api_key=config.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(config.GEMINI_MODEL)
        print(f"[AI] Gemini agent initialized (model={config.GEMINI_MODEL}).")

    def analyze(
        self,
        image_input: Union[Image.Image, np.ndarray],
        prompt: str = "Describe what you see briefly and what the user might be doing.",
    ) -> str:
        if not self._model:
            return "Error: AI is not configured."

        try:
            img = image_input
            if isinstance(image_input, np.ndarray):
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)

            print("[AI] Sending request to Gemini...")
            response = self._model.generate_content([prompt, img])
            print("[AI] Response received.")
            return getattr(response, "text", "") or ""
        except Exception as e:
            print(f"[AI] Error: {e}")
            return "Analysis failed."
