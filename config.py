# config.py
# ================= CONFIGURATION =================
# AI Settings
GEMINI_API_KEY = "AIzaSyDUvWk1YshlTV8DXChhxcLS8lJehhpNTKo" # 請填入你的 Key

# Network
TCP_IP = "0.0.0.0"  # Listen on all interfaces
TCP_PORT = 4242
RECV_BUFFER_SIZE = 65536

# Camera Selection
PC_CAMERA_ID = 0    # Try 0, if fails try 1

# MediaPipe / AI
PROCESS_EVERY_N_FRAMES = 2
CONFIDENCE = 0.5

# UI Settings
SMOOTHING_FACTOR = 0.08
DOT_RADIUS = 12
FRAME_DELAY_MS = 16  # ~60 FPS

# Grid Settings
GRID_ROWS = 8
GRID_COLS = 8
GRID_ALPHA = 0.3

# Dwell Trigger
DWELL_THRESHOLD = 2.0
TRIGGER_COOLDOWN = 3.0

# Debugging
SHOW_DEBUG_VIEW = True  # Set to False for production