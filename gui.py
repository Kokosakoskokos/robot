import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os
import cv2
import numpy as np
from PIL import Image, ImageTk
from core.robot import ClankerRobot
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ClankerGUI:
    def __init__(self, root, robot_instance=None):
        self.root = root
        self.root.title("Clanker Robot Control Panel")
        self.root.geometry("1000x650")
        
        # Use provided robot or create new one
        self.robot = robot_instance or ClankerRobot(simulation_mode=True)
        self.robot_thread = None
        self.running = False
        self.current_frame = None

        self._setup_ui()
        self._update_status_loop()
        self._update_video_loop()

    def _setup_ui(self):
        # Main Layout: Left (Video) | Right (Controls)
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Left Side: Video ---
        video_side = ttk.Frame(self.paned)
        self.paned.add(video_side, weight=2)

        video_frame = ttk.LabelFrame(video_side, text="Robot Vision (Live Camera Feed)", padding="5")
        video_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(video_frame, bg="#1a1a1a", width=640, height=480)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # --- Right Side: Controls ---
        control_side = ttk.Frame(self.paned)
        self.paned.add(control_side, weight=1)

        main_frame = ttk.Frame(control_side, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Power Control (MOVED TO TOP)
        pwr_frame = ttk.LabelFrame(main_frame, text="Power Control", padding="5")
        pwr_frame.pack(fill=tk.X, pady=2)
        
        self.btn_toggle = tk.Button(pwr_frame, text="START ROBOT ENGINE", 
                                   command=self.toggle_robot, bg="#4CAF50", fg="white", 
                                   font=("Arial", 10, "bold"), height=2)
        self.btn_toggle.pack(fill=tk.X, pady=2)

        # 2. Status Header
        status_frame = ttk.LabelFrame(main_frame, text="Robot Status", padding="5")
        status_frame.pack(fill=tk.X, pady=2)

        self.lbl_mode = ttk.Label(status_frame, text="Mode: Unknown", font=("Arial", 10))
        self.lbl_mode.pack(anchor=tk.W)

        self.lbl_heading = ttk.Label(status_frame, text="Heading: 0°", font=("Arial", 10))
        self.lbl_heading.pack(anchor=tk.W)

        self.lbl_ai = ttk.Label(status_frame, text="AI Brain: Idle", font=("Arial", 10))
        self.lbl_ai.pack(anchor=tk.W)

        # 3. Command Entry
        cmd_frame = ttk.LabelFrame(main_frame, text="Manual Command (Type instead of speaking)", padding="5")
        cmd_frame.pack(fill=tk.X, pady=2)

        self.ent_cmd = ttk.Entry(cmd_frame, font=("Arial", 11))
        self.ent_cmd.pack(side=tk.TOP, fill=tk.X, pady=2)
        self.ent_cmd.bind("<Return>", lambda e: self.send_command())

        btn_send = ttk.Button(cmd_frame, text="Send to Brain", command=self.send_command)
        btn_send.pack(side=tk.TOP, fill=tk.X)

        # 4. Quick Action Buttons (Compact Grid)
        btn_frame = ttk.LabelFrame(main_frame, text="Quick Actions", padding="5")
        btn_frame.pack(fill=tk.X, pady=2)

        actions = [
            ("Stand", "stand"), ("Sit", "sit"), 
            ("Dance", "dance"), ("Fist Bump", "fist_bump"),
            ("Follow Me", "follow_person"), ("Stop", "stop")
        ]

        for i, (name, cmd) in enumerate(actions):
            btn = ttk.Button(btn_frame, text=name, command=lambda c=cmd: self.execute_quick_action(c))
            btn.grid(row=i//2, column=i%2, sticky="ew", padx=2, pady=2)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        # 5. Audio Test
        audio_frame = ttk.Frame(main_frame)
        audio_frame.pack(fill=tk.X, pady=2)
        ttk.Button(audio_frame, text="Test Speaker (Czech)", 
                   command=lambda: self.robot.tts.speak("Zkouška reproduktoru. Slyšíš mě?")).pack(fill=tk.X)

        # 6. Log Output
        log_frame = ttk.LabelFrame(main_frame, text="Robot Logs", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        self.txt_log = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.txt_log.see(tk.END)

    def toggle_robot(self):
        if not self.running:
            self.running = True
            self.btn_toggle.config(text="STOP ROBOT ENGINE", bg="#f44336")
            self.robot_thread = threading.Thread(target=self.robot.start, daemon=True)
            self.robot_thread.start()
            self.log("Robot engine started.")
        else:
            self.running = False
            self.robot.running = False
            self.btn_toggle.config(text="START ROBOT ENGINE", bg="#4CAF50")
            self.log("Robot engine stopping...")

    def send_command(self):
        cmd = self.ent_cmd.get()
        if cmd:
            self.log(f"User: {cmd}")
            self.robot.current_state['voice_command'] = cmd
            self.ent_cmd.delete(0, tk.END)

    def execute_quick_action(self, action_name):
        self.log(f"Executing: {action_name}")
        self.robot.execute_action({'action': action_name})

    def _update_status_loop(self):
        try:
            mode_str = self.robot.config.get('mode', 'sim').upper()
            self.lbl_mode.config(text=f"Mode: {mode_str}")
            self.lbl_heading.config(text=f"Heading: {self.robot.heading:.1f}°")
            
            # Show if thinking
            if self.robot.current_state.get('_ai_error') == "RATE_LIMIT":
                self.lbl_ai.config(text="AI Brain: RATE LIMIT (Wait)", foreground="red")
            elif self.robot.current_state.get('voice_command'):
                self.lbl_ai.config(text="AI Brain: THINKING...", foreground="orange")
                # Clear error if we are thinking again
                if '_ai_error' in self.robot.current_state:
                    self.robot.current_state.pop('_ai_error')
            else:
                self.lbl_ai.config(text=f"AI Brain: {'ACTIVE' if self.robot.running else 'IDLE'}", foreground="black")
        except: pass
        self.root.after(500, self._update_status_loop)

    def _update_video_loop(self):
        try:
            frame = self.robot.vision.capture_frame()
            
            if frame is None:
                # Create a placeholder if no frame
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Visual feedback for simulation
            if self.robot.config.get('mode') == 'simulation':
                cv2.putText(frame, "SIMULACE AKTIVNI", (160, 220), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                cv2.putText(frame, "Pro realnou kameru vypnete --simulation", (140, 260), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            else:
                # Real camera: Detect faces
                faces = self.robot.face_tracker.detect_faces(frame)
                for face in faces:
                    x, y, w, h = face['bbox']
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"Osoba {int(face['distance_estimate'])}mm", 
                                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Detect and draw bodies
                bodies = self.robot.vision.detect_bodies(frame)
                for body in bodies:
                    x, y, w, h = body['bbox']
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    cv2.putText(frame, "Postava", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # Convert to PIL/Tkinter format
            cv2_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2_img)
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width > 10 and canvas_height > 10:
                img = img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(image=img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        except Exception as e:
            logger.debug(f"Video loop error: {e}")
        
        self.root.after(100, self._update_video_loop)

if __name__ == "__main__":
    root = tk.Tk()
    gui = ClankerGUI(root)
    root.mainloop()
