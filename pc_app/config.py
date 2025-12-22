"""pc_app/config.py
Central configuration for the Windows PC side.

Notes:
- Prefer environment variables for secrets (e.g., GEMINI_API_KEY) instead of hardcoding.
- This module is imported by backend/ui/ai modules.
"""

import os

# ================= AI Settings =================
# Prefer: set GEMINI_API_KEY in your environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # e.g., setx GEMINI_API_KEY "YOUR_KEY"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ================= Network =================
TCP_IP = "0.0.0.0"      # Listen on all interfaces
TCP_PORT = 4242
RECV_BUFFER_SIZE = 65536
MAX_JPEG_BYTES = 5_000_000

# ================= Camera Selection =================
PC_CAMERA_ID = 0        # Try 0, if fails try 1

# ================= MediaPipe / Tracking =================
PROCESS_EVERY_N_FRAMES = 2
CONFIDENCE = 0.5
IRIS_LANDMARK_INDEX = 468

# Normalization ranges (tune per device angle)
# NOTE: These are raw MediaPipe landmark coords in normalized space.
PI_X_MIN, PI_X_MAX = 0.10, 0.90
PI_Y_MIN, PI_Y_MAX = 0.40, 0.60

PC_X_MIN, PC_X_MAX = 0.20, 0.80
PC_Y_MIN, PC_Y_MAX = 0.42, 0.58

# ================= UI Settings =================
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

# Calibration
CALIBRATION_FILE = "calibration.json"
CALIBRATION_DWELL_SEC = 2.0
CALIBRATION_BUFFER = 0.02

# Debugging
SHOW_DEBUG_VIEW = True  # Set to False for production
