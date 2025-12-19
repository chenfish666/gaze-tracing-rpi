# ai_agent.py
import google.generativeai as genai
from PIL import Image
import numpy as np
import cv2
import config

class GeminiAgent:
    def __init__(self):
        if not config.GEMINI_API_KEY:
            print("[AI] Warning: No API Key provided in config.py")
            self.model = None
            return
            
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        print("[AI] Gemini Agent Initialized.")

    def analyze(self, image_input, prompt="請簡短說明你看到了什麼，以及使用者可能在做什麼。"):
        if not self.model:
            return "Error: No API Key"

        try:
            # 格式轉換：確保是 PIL Image
            img = image_input
            if isinstance(image_input, np.ndarray):
                # 如果是 OpenCV (BGR)，轉成 RGB 再轉 PIL
                rgb = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
            
            print("[AI] Sending request to Gemini...")
            response = self.model.generate_content([prompt, img])
            print("[AI] Response received.")
            return response.text
        except Exception as e:
            print(f"[AI] Error: {e}")
            return "Analysis Failed."