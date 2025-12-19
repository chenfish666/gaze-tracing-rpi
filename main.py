import tkinter as tk
from tkinter import Toplevel
from PIL import Image, ImageTk, ImageGrab
import threading
import time
import cv2
import sys
import os

# Import our modules
import config
import backend
import ai_agent  # 確保你有建立 ai_agent.py

# ============ CALIBRATION LOGIC ============
class Calibrator:
    def __init__(self):
        self.calib_file = "calibration.json"
        self.points = []
        self.x_min, self.x_max = 0.3, 0.7
        self.y_min, self.y_max = 0.35, 0.60
        self.load()

    def map(self, raw_x, raw_y):
        norm_x = (raw_x - self.x_min) / (self.x_max - self.x_min)
        norm_y = (raw_y - self.y_min) / (self.y_max - self.y_min)
        return max(0.0, min(1.0, norm_x)), max(0.0, min(1.0, norm_y))

    def update_from_points(self, points):
        if len(points) < 4: return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        buffer = 0.02
        self.x_min = min(xs) + buffer
        self.x_max = max(xs) - buffer
        self.y_min = min(ys) + buffer
        self.y_max = max(ys) - buffer
        print(f"[Calibration] New Range: X({self.x_min:.3f}-{self.x_max:.3f}), Y({self.y_min:.3f}-{self.y_max:.3f})")
        self.save()

    def save(self):
        data = {"x_min": self.x_min, "x_max": self.x_max, "y_min": self.y_min, "y_max": self.y_max}
        with open(self.calib_file, "w") as f:
            import json
            json.dump(data, f)

    def load(self):
        if os.path.exists(self.calib_file):
            try:
                import json
                with open(self.calib_file, "r") as f:
                    data = json.load(f)
                    self.x_min = data["x_min"]; self.x_max = data["x_max"]
                    self.y_min = data["y_min"]; self.y_max = data["y_max"]
                    print("[Calibration] Loaded existing profile.")
            except: pass

# ============ UI CLASS ============
class GhostUI:
    def __init__(self, shared_state):
        self.shared = shared_state
        self.calibrator = Calibrator()
        
        # --- UI Setup ---
        self.root = tk.Tk()
        self.root.title("Ghost UI")
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", "black")
        self.root.overrideredirect(True)
        self.root.configure(bg="black")
        
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.sw}x{self.sh}+0+0")
        
        self.canvas = tk.Canvas(self.root, width=self.sw, height=self.sh, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.dot = self.canvas.create_oval(0, 0, 0, 0, fill="red", outline="")
        self._draw_grid()
        
        # --- Debug Window ---
        self.debug_win = None
        self.pi_canvas = None
        self.pc_canvas = None
        self.pi_image_ref = None
        self.pc_image_ref = None
        if config.SHOW_DEBUG_VIEW:
            self._setup_debug_window()

        # --- AI Agent ---
        self.agent = ai_agent.GeminiAgent()

        # Calibration State
        self.is_calibrating = False
        self.calib_step = 0
        self.calib_timer = 0
        self.calib_msg = self.canvas.create_text(self.sw//2, self.sh//2, text="", fill="yellow", font=("Arial", 30, "bold"))
        self.calib_target = self.canvas.create_oval(0,0,0,0, fill="cyan", outline="white", width=3, state='hidden')
        self.calib_coords = [(50, 50), (self.sw-50, 50), (50, self.sh-50), (self.sw-50, self.sh-50)]

        # Dwell State
        self.current_cell = None
        self.dwell_start = 0
        self.last_trigger = 0
        self.dwell_indicator = None
        
        self.cur_screen_x = 0.5
        self.cur_screen_y = 0.5

        # Bind Keys
        self.root.bind("c", self.start_calibration)
        self.root.bind("C", self.start_calibration)
        self.root.bind("<Escape>", self._quit)
        self.root.focus_force()
        
        self.root.after(config.FRAME_DELAY_MS, self._update_loop)
        print("[UI] Ghost UI Started.")

    def _setup_debug_window(self):
        self.debug_win = Toplevel(self.root)
        self.debug_win.title("Debug View (Click to Calibrate)")
        self.debug_win.geometry("660x360")
        self.debug_win.attributes("-topmost", True)
        self.debug_win.configure(bg="#202020")
        
        self.debug_win.bind("c", self.start_calibration)
        self.debug_win.bind("C", self.start_calibration)
        self.debug_win.bind("<Escape>", self._quit)

        ctrl_frame = tk.Frame(self.debug_win, bg="#202020")
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        tk.Button(ctrl_frame, text="Start Calibration (C)", command=lambda: self.start_calibration(None), 
                  bg="#444", fg="white", font=("Arial", 10, "bold")).pack()
        
        f1 = tk.Frame(self.debug_win, bg="#202020")
        f1.pack(side=tk.LEFT, padx=10)
        tk.Label(f1, text="Raspberry Pi", fg="white", bg="#202020").pack()
        self.pi_canvas = tk.Canvas(f1, width=320, height=240, bg="black", highlightthickness=0)
        self.pi_canvas.pack()

        f2 = tk.Frame(self.debug_win, bg="#202020")
        f2.pack(side=tk.LEFT, padx=10)
        tk.Label(f2, text="PC Webcam", fg="white", bg="#202020").pack()
        self.pc_canvas = tk.Canvas(f2, width=320, height=240, bg="black", highlightthickness=0)
        self.pc_canvas.pack()

    def _draw_grid(self):
        cw = self.sw / config.GRID_COLS
        ch = self.sh / config.GRID_ROWS
        color = "#404040"
        for i in range(1, config.GRID_COLS):
            self.canvas.create_line(i*cw, 0, i*cw, self.sh, fill=color, dash=(4, 4))
        for j in range(1, config.GRID_ROWS):
            self.canvas.create_line(0, j*ch, self.sw, j*ch, fill=color, dash=(4, 4))

    def _update_canvas_image(self, canvas, cv_frame, is_pi=True):
        if cv_frame is None: 
            canvas.delete("all"); return
        try:
            prev = cv2.resize(cv_frame, (320, 240))
            rgb = cv2.cvtColor(prev, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(image=Image.fromarray(rgb))
            canvas.create_image(0, 0, image=img, anchor=tk.NW)
            if is_pi: self.pi_image_ref = img
            else: self.pc_image_ref = img
        except: pass

    # ============ LOGIC LOOP ============
    # ============ LOGIC LOOP (UI 更新與邏輯核心) ============
    def _update_loop(self):
        if not self.shared.running: return
        
        # 1. 讀取共享狀態
        with self.shared.lock:
            # 檢查 Pi 是否連線 (這是關鍵修正)
            is_active = self.shared.pi_connected
            
            # 讀取座標與影像
            pi_ok = self.shared.pi_has_face
            pc_ok = self.shared.pc_has_face
            pi_pos = (self.shared.pi_target_x, self.shared.pi_target_y)
            pc_pos = (self.shared.pc_target_x, self.shared.pc_target_y)
            
            frames = (self.shared.pi_frame.copy() if self.shared.pi_frame is not None else None,
                      self.shared.pc_frame.copy() if self.shared.pc_frame is not None else None)
            
            # 更新 Debug 視窗資訊
            if self.debug_win and hasattr(self, 'info_label'):
                try:
                    status = "Connected" if is_active else "Waiting for Wake Word..."
                    txt = f"Status: {status} | Pi FPS: {self.shared.pi_fps} | PC FPS: {self.shared.pc_fps}"
                    self.info_label.config(text=txt, fg="#00FF00" if is_active else "#FFFF00")
                except: pass

        # 2. 狀態控管：如果 Pi 沒連線，隱藏紅點並跳出，不執行後續運算
        if not is_active:
            self.canvas.itemconfig(self.dot, state='hidden') # 隱藏紅點
            
            # 清除注視計時，避免連線瞬間誤觸
            self.current_cell = None 
            self.dwell_start = 0
            if self.dwell_indicator:
                self.canvas.delete(self.dwell_indicator)
                self.dwell_indicator = None
            
            # 繼續下一幀迴圈，但不做任何事
            self.root.after(config.FRAME_DELAY_MS, self._update_loop)
            return

        # 3. 如果連線了，顯示紅點並開始計算
        self.canvas.itemconfig(self.dot, state='normal')

        # --- 以下是原本的座標融合與 Dwell 邏輯 ---
        
        # Fusion Logic
        if pi_ok and pc_ok:
            raw_x = (pi_pos[0] + pc_pos[0]) / 2
            raw_y = (pi_pos[1] + pc_pos[1]) / 2
        elif pi_ok:
            raw_x, raw_y = pi_pos
        elif pc_ok:
            raw_x, raw_y = pc_pos
        else:
            # 兩邊都沒偵測到人臉時，保持上一次的位置或置中，但不會觸發(因為沒人臉)
            # 為了保險，這裡可以設個 flag 暫停 dwell，但保持紅點顯示讓你知道系統還在運作
            raw_x, raw_y = self.cur_screen_x, self.cur_screen_y 

        if self.is_calibrating:
            self._handle_calibration(raw_x, raw_y)
        else:
            target_x, target_y = self.calibrator.map(raw_x, raw_y)
            # 平滑移動
            self.cur_screen_x += (target_x - self.cur_screen_x) * config.SMOOTHING_FACTOR
            self.cur_screen_y += (target_y - self.cur_screen_y) * config.SMOOTHING_FACTOR
            
            px = int(self.cur_screen_x * self.sw)
            py = int(self.cur_screen_y * self.sh)
            
            r = config.DOT_RADIUS
            self.canvas.coords(self.dot, px-r, py-r, px+r, py+r)
            
            # 只有在有人臉被偵測到時，才計算 Dwell (避免沒人時紅點亂飄觸發)
            if pi_ok or pc_ok:
                self._check_dwell(px, py)
            else:
                # 沒人看時，清除 Dwell 進度
                if self.dwell_indicator:
                    self.canvas.delete(self.dwell_indicator)
                    self.dwell_indicator = None
                self.current_cell = None

        if config.SHOW_DEBUG_VIEW and self.debug_win:
            self._update_canvas_image(self.pi_canvas, frames[0], True)
            self._update_canvas_image(self.pc_canvas, frames[1], False)

        self.root.after(config.FRAME_DELAY_MS, self._update_loop)

    # ============ CALIBRATION FLOW ============
    def start_calibration(self, event=None):
        print("Starting Calibration...")
        self.is_calibrating = True
        self.calib_step = 0
        self.calibrator.points = []
        self.canvas.itemconfig(self.dot, state='hidden')
        self.canvas.itemconfig(self.calib_target, state='normal')
        self._next_calib_step()

    def _next_calib_step(self):
        if self.calib_step >= 4:
            self.is_calibrating = False
            self.calibrator.update_from_points(self.calibrator.points)
            self.canvas.itemconfig(self.calib_msg, text="Done!", fill="green")
            self.canvas.itemconfig(self.calib_target, state='hidden')
            self.canvas.itemconfig(self.dot, state='normal')
            self.root.after(2000, lambda: self.canvas.itemconfig(self.calib_msg, text=""))
            return

        tx, ty = self.calib_coords[self.calib_step]
        self.canvas.coords(self.calib_target, tx-20, ty-20, tx+20, ty+20)
        msg = ["Look Top-Left", "Look Top-Right", "Look Bottom-Left", "Look Bottom-Right"][self.calib_step]
        self.canvas.itemconfig(self.calib_msg, text=msg)
        self.calib_timer = time.time()

    def _handle_calibration(self, raw_x, raw_y):
        if time.time() - self.calib_timer > 2.0:
            print(f"Recorded Step {self.calib_step}: {raw_x:.4f}, {raw_y:.4f}")
            self.calibrator.points.append((raw_x, raw_y))
            self.calib_step += 1
            self._next_calib_step()

    # ============ DWELL LOGIC & AI TRIGGER ============
    def _check_dwell(self, px, py):
        col = int(self.cur_screen_x * config.GRID_COLS)
        row = int(self.cur_screen_y * config.GRID_ROWS)
        cell = (row, col)
        now = time.time()
        
        if cell != self.current_cell:
            self.current_cell = cell
            self.dwell_start = now
            if self.dwell_indicator:
                self.canvas.delete(self.dwell_indicator)
                self.dwell_indicator = None
        else:
            duration = now - self.dwell_start
            
            # Loading Circle
            if duration > 0.5 and not self.dwell_indicator:
                self.dwell_indicator = self.canvas.create_oval(px-30, py-30, px+30, py+30, outline="yellow", width=3)
            
            # Trigger!
            if duration > config.DWELL_THRESHOLD and (now - self.last_trigger > config.TRIGGER_COOLDOWN):
                self._trigger_action()
                self.last_trigger = now
                self.dwell_start = now
                if self.dwell_indicator:
                    self.canvas.delete(self.dwell_indicator)
                    self.dwell_indicator = None

    def _trigger_action(self):
        # 1. Terminal 顯示「使用者開始了」
        print("\n" + "="*40)
        print(">>> [AI] 注視觸發！開始分析畫面... <<<")
        print("="*40)
        
        # 2. 視覺回饋 (紅點變綠，代表處理中)
        self.canvas.itemconfig(self.dot, fill="#00FF00")
        self.root.update()

        # 3. 啟動 AI 執行緒
        threading.Thread(target=self._run_ai_task, daemon=True).start()

    def _run_ai_task(self):
        try:
            # 截圖
            screenshot = ImageGrab.grab()
            
            # 呼叫 Gemini
            result_text = self.agent.analyze(screenshot, prompt="這是一張使用者正在注視的螢幕截圖。請判斷使用者正在看什麼內容（例如程式碼、影片、文章），並給出一句簡短的輔助建議或摘要。")
            
            # 完成後呼叫回調 (Callback)
            self.root.after(0, lambda: self._handle_ai_result(result_text))
            
        except Exception as e:
            print(f"[AI Error] {e}")
            self.root.after(0, lambda: self._handle_ai_result("Error occurred."))

    def _handle_ai_result(self, text):
        # 4. Terminal 顯示 API 回傳的文字
        print("\n" + "-"*40)
        print("[Gemini API 回傳結果]:")
        print(text)
        print("-"*40 + "\n")
        
        # 5. 紅點變回紅色
        self.canvas.itemconfig(self.dot, fill="red")

    def _quit(self, event=None):
        self.shared.running = False
        self.root.quit()
        import os; os._exit(0)

def main():
    shared = backend.SharedState()
    print("[Main] Starting Backend Threads...")
    t1 = threading.Thread(target=backend.pi_thread_func, args=(shared,), daemon=True)
    t2 = threading.Thread(target=backend.pc_thread_func, args=(shared,), daemon=True)
    t1.start(); t2.start()
    
    print("[Main] Starting UI...")
    ui = GhostUI(shared)
    try:
        ui.root.mainloop()
    except KeyboardInterrupt: pass
    finally:
        shared.running = False
        print("[Main] Exiting...")

if __name__ == "__main__":
    main()