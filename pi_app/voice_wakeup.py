"""pi_app/voice_wakeup.py
Voice wake-up loop:
- VAD record -> wav
- Google SpeechRecognition -> text
- If wake word detected: state.streaming = True
"""

from __future__ import annotations

import time
import speech_recognition as sr

import pyMicVoiceDetection  # uses your existing module on Pi

from .state import SystemState
from . import config


def run_voice_loop(state: SystemState) -> None:
    recognizer = sr.Recognizer()

    print("\n" + "=" * 40)
    print(" Voice Assistant Started!")
    print(f" Say '{config.WAKE_WORD}' to start eye tracking")
    print("=" * 40 + "\n")

    while state.running:
        try:
            if state.streaming:
                # Pause VAD while streaming (reduce audio interference)
                time.sleep(1.0)
                continue

            wav_path = pyMicVoiceDetection.record(
                filename=config.WAV_FILENAME,
                threshold=config.VOICE_SENSITIVITY,
                max_duration=config.MAX_VOICE_DURATION_SEC,
            )
            if not wav_path:
                continue

            print("[Voice] Analyzing audio...")
            with sr.AudioFile(config.WAV_FILENAME) as source:
                audio_data = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio_data, language="en-US")
                print(f"[Voice] You said: {text}")

                if config.WAKE_WORD.lower() in text.lower():
                    print("[Voice] Wake word detected -> start streaming.")
                    state.streaming = True

            except sr.UnknownValueError:
                print("[Voice] Could not understand audio.")
            except sr.RequestError:
                print("[Voice] Network error (Google API).")

        except KeyboardInterrupt:
            print("[System] Stopping...")
            state.running = False
            state.streaming = False
            break
        except Exception as e:
            print(f"[Voice] Error: {e}")
            time.sleep(1.0)
