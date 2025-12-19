"""
Raspberry Pi Main Controller
Integrates:
1. WM8960 Voice Wake-up (VAD + Google Speech API)
2. Camera Streaming (Picamera2 -> TCP)
"""

import socket
import struct
import time
import threading
import cv2
import speech_recognition as sr
import pyMicVoiceDetection  # The VAD module we just wrote
from picamera2 import Picamera2
import os

# ============ CONFIG ============
# Network (PC IP)
PC_IP = "192.168.6.141"  # Please confirm this is your PC's IP
PC_PORT = 4242

# Camera Settings
RES_W, RES_H = 640, 480
JPEG_QUALITY = 70

# Voice Settings
# Changed to English to avoid non-ASCII characters in the return value
WAKE_WORD = "hello"      # Trigger word
WAV_FILENAME = "wake.wav"
VOICE_SENSITIVITY = 0.05 # Adjust based on environmental noise (0.02 ~ 0.1)

# System State
class SystemState:
    def __init__(self):
        self.streaming = False # Whether video is currently streaming
        self.running = True    # Whether the program is running

state = SystemState()

# ============ CAMERA THREAD ============
def camera_streaming_thread():
    """
    Thread responsible for video streaming.
    It monitors state.streaming. If True, it starts the camera and sends data; if False, it waits.
    """
    print("[Camera] Thread Started. Waiting for activation...")
    
    while state.running:
        # 1. Standby mode (not streaming)
        if not state.streaming:
            time.sleep(0.5)
            continue

        # 2. Active mode
        try:
            print("[Camera] Initializing Picamera2...")
            picam2 = Picamera2()
            config = picam2.create_video_configuration(main={"size": (RES_W, RES_H), "format": "RGB888"})
            picam2.configure(config)
            picam2.start()

            print(f"[Camera] Connecting to PC {PC_IP}:{PC_PORT}...")
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client_socket.settimeout(5.0) # Connection timeout setting
            
            try:
                client_socket.connect((PC_IP, PC_PORT))
                print("[Camera] Connected! Streaming Video.")
                
                while state.running and state.streaming:
                    # Capture
                    frame = picam2.capture_array()
                    # RGB -> BGR for OpenCV encoding
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # Encode JPEG
                    _, encoded = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                    data = encoded.tobytes()
                    
                    # Send: Header (4 bytes) + Data
                    msg_size = struct.pack(">L", len(data))
                    client_socket.sendall(msg_size + data)
                    
            except (BrokenPipeError, ConnectionResetError, socket.timeout) as e:
                print(f"[Camera] Connection Lost: {e}")
            finally:
                client_socket.close()
                picam2.stop()
                picam2.close() # Release resources
                print("[Camera] Stopped/Disconnected.")
                
                # If disconnected unexpectedly, we can choose to reconnect or go back to standby.
                # Here: If state.streaming is still True, the outer loop will try to reconnect.
                time.sleep(2) 

        except Exception as e:
            print(f"[Camera] Error: {e}")
            time.sleep(2)

# ============ MAIN (VOICE LOOP) ============
def main():
    # 1. Start Camera Thread (Background)
    t_cam = threading.Thread(target=camera_streaming_thread, daemon=True)
    t_cam.start()

    # 2. Voice Recognition Setup
    recognizer = sr.Recognizer()
    
    print("\n" + "="*40)
    print(f" Voice Assistant Started!")
    print(f" Please say: '{WAKE_WORD}' to start eye tracking")
    print("="*40 + "\n")

    while state.running:
        try:
            # If already streaming, should we keep listening?
            # Option A: Keep listening (e.g., to say "Stop")
            # Option B: Pause listening (avoid noise interference from camera operation)
            # We use Option B: Pause VAD during streaming. Use Ctrl+C to stop.
            if state.streaming:
                time.sleep(1)
                continue

            # --- VAD Detection ---
            # This blocks until recording is finished
            saved_file = pyMicVoiceDetection.record(
                filename=WAV_FILENAME,
                threshold=VOICE_SENSITIVITY,
                max_duration=5 # Voice commands are usually short
            )

            if not saved_file:
                continue

            # --- Google Speech Recognition ---
            print("[Voice] Analyzing audio...")
            with sr.AudioFile(WAV_FILENAME) as source:
                audio_data = recognizer.record(source)
            
            try:
                # Requires Internet. 
                # Changed to 'en-US' to ensure the returned 'text' is ASCII compatible.
                text = recognizer.recognize_google(audio_data, language='en-US')
                print(f" You said: {text}")

                # Case insensitive comparison
                if WAKE_WORD.lower() in text.lower():
                    print("\n>>> Wake up successful! Starting eye tracking system... <<<\n")
                    state.streaming = True # This triggers the Camera Thread to start working
                
            except sr.UnknownValueError:
                print("[Voice] Could not understand audio")
            except sr.RequestError:
                print("[Voice] Network error (Google API)")

        except KeyboardInterrupt:
            print("\n[System] Stopping...")
            state.running = False
            state.streaming = False
            break
        except Exception as e:
            print(f"[Error] {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()