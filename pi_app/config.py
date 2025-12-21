"""pi_app/config.py
Raspberry Pi configuration.
"""

# Network (PC IP)
PC_IP = "192.168.6.141"  # TODO: set to your PC IP
PC_PORT = 4242

# Camera
RES_W, RES_H = 640, 480
JPEG_QUALITY = 70

# Voice
WAKE_WORD = "hello"
WAV_FILENAME = "wake.wav"
VOICE_SENSITIVITY = 0.05
MAX_VOICE_DURATION_SEC = 5
