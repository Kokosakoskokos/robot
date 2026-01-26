import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os
import cv2
from PIL import Image, ImageTk
from core.robot import ClankerRobot
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ClankerGUI:
    def __init__(self, root, robot_instance=None):
        self.root = root
        self.root.title("Clanker Robot Control Panel")
        self.root.geometry("1100x700")
        
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
        self.paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Left Side: Video ---
        video_side = ttk.Frame(self.paned)
        self.paned.add(video_side, weight=2)

        video_frame = ttk.LabelFrame(video_side, text="Robot Vision", padding="5")
        video_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(video_frame, bg="black", width=640, height=480)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # --- Right Side: Controls ---
        control_side = ttk.Frame(self.paned)
        self.paned.add(control_side, weight=1)

        main_frame = ttk.Frame(control_side, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status Header
        status_frame = ttk.LabelFrame(main_frame, text="Robot Status", padding="10")
        status_frame.pack(fill=tk.X, pady=5)

        self.lbl_mode = ttk.Label(status_frame, text="Mode: Unknown")
        self.lbl_mode.pack(anchor=tk.W)

        self.lbl_heading = ttk.Label(status_frame, text="Heading: 0°")
        self.lbl_heading.pack(anchor=tk.W)

        self.lbl_ai = ttk.Label(status_frame, text="AI: Ready")
        self.lbl_ai.pack(anchor=tk.W)

        # Command Entry
        cmd_frame = ttk.LabelFrame(main_frame, text="Manual Command", padding="10")
        cmd_frame.pack(fill=tk.X, pady=5)

        self.ent_cmd = ttk.Entry(cmd_frame, font=("Arial", 11))
        self.ent_cmd.pack(side=tk.TOP, fill=tk.X, pady=5)
        self.ent_cmd.bind("<Return>", lambda e: self.send_command())

        btn_send = ttk.Button(cmd_frame, text="Send Command", command=self.send_command)
        btn_send.pack(side=tk.TOP, fill=tk.X)

        # Quick Action Buttons
        btn_frame = ttk.LabelFrame(main_frame, text="Quick Actions", padding="10")
        btn_frame.pack(fill=tk.X, pady=5)

        actions = [
            ("Stand", "stand"), ("Sit", "sit"), 
            ("Dance", "dance"), ("Fist Bump", "fist_bump"),
            ("Follow Me", "follow_person"), ("Stop", "stop")
        ]

        for name, cmd in actions:
            btn = ttk.Button(btn_frame, text=name, command=lambda c=cmd: self.execute_quick_action(c))
            btn.pack(side=tk.TOP, fill=tk.X, pady=2)

        # Log Output
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.txt_log = scrolledtext.ScrolledText(log_frame, height=10, font=("Consolas", 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Engine Control
        self.btn_toggle = ttk.Button(main_frame, text="START ROBOT ENGINE", command=self.toggle_robot)
        self.btn_toggle.pack(fill=tk.X, pady=10)

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.txt_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.txt_log.see(tk.END)

    def toggle_robot(self):
        if not self.running:
            self.running = True
            self.btn_toggle.config(text="STOP ROBOT ENGINE")
            self.robot_thread = threading.Thread(target=self.robot.start, daemon=True)
            self.robot_thread.start()
            self.log("Robot engine started.")
        else:
            self.running = False
            self.robot.running = False
            self.btn_toggle.config(text="START ROBOT ENGINE")
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
            self.lbl_mode.config(text=f"Mode: {self.robot.config['mode'].upper()}")
            self.lbl_heading.config(text=f"Heading: {self.robot.heading:.1f}°")
            self.lbl_ai.config(text=f"AI Brain: {'Active' if self.robot.running else 'Idle'}")
        except: pass
        self.root.after(500, self._update_status_loop)

    def _update_video_loop(self):
        try:
            # Capture frame from robot vision
            frame = self.robot.vision.capture_frame()
            if frame is not None:
                # Detect faces for visual overlay
                faces = self.robot.face_tracker.detect_faces(frame)
                for face in faces:
                    x, y, w, h = face['bbox']
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, f"Person {int(face['distance_estimate'])}mm", 
                                (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Convert to PIL/Tkinter format
                cv2_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2_img)
                
                # Resize to fit canvas
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                if canvas_width > 1 and canvas_height > 1:
                    img = img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                
                self.photo = ImageTk.PhotoImage(image=img)
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        except Exception as e:
            logger.debug(f"Video loop error: {e}")
        
        self.root.after(100, self._update_video_loop)

if __name__ == "__main__":
    root = tk.Tk()
    gui = ClankerGUI(root)
    root.mainloop()
