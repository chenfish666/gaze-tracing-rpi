# backend.py
import cv2
import socket
import struct
import threading
import time
import numpy as np
import mediapipe as mp
import config  # Import our config file

# ============ SHARED STATE ============
class SharedState:
    def __init__(self):
        self.lock = threading.Lock()
        self.running = True
        
        # 連線狀態旗標 (用於同步啟動)
        self.pi_connected = False 
        
        # Pi Data
        self.pi_frame = None
        self.pi_has_face = False
        self.pi_target_x = 0.5
        self.pi_target_y = 0.5
        self.pi_fps = 0
        
        # PC Data
        self.pc_frame = None
        self.pc_has_face = False
        self.pc_target_x = 0.5
        self.pc_target_y = 0.5
        self.pc_fps = 0

# ============ PROCESSING LOGIC ============
class EyeProcessor:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=config.CONFIDENCE,
            min_tracking_confidence=config.CONFIDENCE
        )

    def process(self, frame, is_pi=False):
        if frame is None: return 0.5, 0.5, False, None

        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        target_x, target_y = 0.5, 0.5
        detected = False
        debug_frame = frame.copy()

        if results.multi_face_landmarks:
            detected = True
            landmarks = results.multi_face_landmarks[0]
            
            # 取得左眼虹膜中心 (點 468)
            pt = landmarks.landmark[468]
            cx, cy = int(pt.x * w), int(pt.y * h)
            cv2.circle(debug_frame, (cx, cy), 4, (0, 255, 0), -1)
            
            # ============ 視角參數分離區 ============
            if is_pi:
                # [針對 Pi (仰視) 的設定]
                # 仰視時 Y 軸變化較小，需要較靈敏 (範圍較窄)
                # 仰視時眼球位置偏上，Y 軸區間可能需要偏上
                x_min, x_max = 0.1, 0.9     # X 軸保持保守
                y_min, y_max = 0.40, 0.60   # Y 軸靈敏度調高 (區間 0.2)
            else:
                # [針對 PC (平視) 的設定]
                # 標準視角，範圍可以正常
                x_min, x_max = 0.2, 0.8
                y_min, y_max = 0.42, 0.58 

            # ============ 座標映射 ============
            norm_x = (pt.x - x_min) / (x_max - x_min)
            norm_y = (pt.y - y_min) / (y_max - y_min)
            
            # 限制在 0.0 ~ 1.0
            target_x = max(0.0, min(1.0, norm_x))
            target_y = max(0.0, min(1.0, norm_y))

        return target_x, target_y, detected, debug_frame

# ============ NETWORK HELPER ============
def recv_exact(sock, n_bytes):
    data = b""
    while len(data) < n_bytes:
        try:
            chunk = sock.recv(n_bytes - len(data))
            if not chunk: return None
            data += chunk
        except socket.timeout:
            continue
        except OSError:
            return None
    return data

# ============ THREAD 1: PI RECEIVER ============
def pi_thread_func(shared):
    processor = EyeProcessor()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_sock.bind((config.TCP_IP, config.TCP_PORT))
        server_sock.listen(1)
        print(f"[Backend] 📡 Waiting for Pi connection on port {config.TCP_PORT}...")
    except Exception as e:
        print(f"[Backend] Bind Error: {e}")
        return

    conn = None
    payload_size = struct.calcsize(">L")
    
    frame_count = 0
    fps_counter = 0
    fps_timer = time.time()

    while shared.running:
        # --- 1. 等待連線 ---
        if conn is None:
            if shared.pi_connected:
                with shared.lock: shared.pi_connected = False
                print("[Backend] Pi Status: Disconnected (Waiting...)")

            server_sock.settimeout(1.0)
            try:
                conn, addr = server_sock.accept()
                print(f"[Backend] ✅ Pi Connected from: {addr}")
                
                with shared.lock:
                    shared.pi_connected = True # 通知 PC 開啟鏡頭
                
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                conn.settimeout(5.0)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[Backend] Accept Error: {e}")
                continue
        
        # --- 2. 接收數據 ---
        try:
            size_data = recv_exact(conn, payload_size)
            if not size_data: raise ConnectionResetError()

            msg_size = struct.unpack(">L", size_data)[0]
            if msg_size > 5_000_000: continue

            frame_data = recv_exact(conn, msg_size)
            if not frame_data: raise ConnectionResetError()

            frame_arr = np.frombuffer(frame_data, dtype=np.uint8)
            frame = cv2.imdecode(frame_arr, cv2.IMREAD_COLOR)
            
            if frame is None: continue
            
            frame_count += 1
            if frame_count % config.PROCESS_EVERY_N_FRAMES == 0:
                # 呼叫 Process，指定 is_pi=True
                tx, ty, detected, debug_frame = processor.process(frame, is_pi=True)
                fps_counter += 1
                
                with shared.lock:
                    shared.pi_has_face = detected
                    if detected:
                        shared.pi_target_x = tx
                        shared.pi_target_y = ty
                    shared.pi_frame = debug_frame

            if time.time() - fps_timer >= 1.0:
                with shared.lock: shared.pi_fps = fps_counter
                fps_counter = 0
                fps_timer = time.time()

        except (ConnectionResetError, BrokenPipeError, socket.timeout):
            print("[Backend] Pi Disconnected.")
            if conn: conn.close()
            conn = None
            with shared.lock: shared.pi_connected = False
            
        except Exception as e:
            print(f"[Backend] Stream Error: {e}")
            if conn: conn.close()
            conn = None
            with shared.lock: shared.pi_connected = False

    if conn: conn.close()
    server_sock.close()

# ============ THREAD 2: PC WEBCAM ============
def pc_thread_func(shared):
    processor = EyeProcessor()
    cap = None
    
    print("[Backend] PC Camera Thread Ready (Waiting for Pi Trigger)...")
    
    frame_count = 0
    fps_counter = 0
    fps_timer = time.time()

    while shared.running:
        # 檢查 Pi 連線狀態
        if not shared.pi_connected:
            if cap is not None:
                print("[Backend] Pi disconnected -> Stopping PC Camera.")
                cap.release()
                cap = None
                with shared.lock: shared.pc_frame = None
            time.sleep(0.5)
            continue

        # 啟動相機
        if cap is None:
            print(f"[Backend] ✅ Pi Signal Detected -> Starting PC Camera...")
            cap = cv2.VideoCapture(config.PC_CAMERA_ID, cv2.CAP_DSHOW)
            if not cap.isOpened(): cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("[Backend] ❌ Failed to open PC Camera.")
                time.sleep(2)
                continue
        
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1); continue
        
        frame = cv2.flip(frame, 1)
        
        # 呼叫 Process，指定 is_pi=False
        tx, ty, detected, debug_frame = processor.process(frame, is_pi=False)
        
        fps_counter += 1
        with shared.lock:
            shared.pc_has_face = detected
            if detected:
                shared.pc_target_x = tx
                shared.pc_target_y = ty
            shared.pc_frame = debug_frame

        if time.time() - fps_timer >= 1.0:
            with shared.lock: shared.pc_fps = fps_counter
            fps_counter = 0
            fps_timer = time.time()
            
    if cap: cap.release()