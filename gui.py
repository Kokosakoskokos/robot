import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import os
from core.robot import ClankerRobot
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ClankerGUI:
    def __init__(self, root, robot_instance=None):
        self.root = root
        self.root.title("Clanker Robot Control Panel")
        self.root.geometry("800x600")
        
        # Use provided robot or create new one
        self.robot = robot_instance or ClankerRobot(simulation_mode=True)
        self.robot_thread = None
        self.running = False

        self._setup_ui()
        self._update_status_loop()

    def _setup_ui(self):
        # Main Layout
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Status Header ---
        status_frame = ttk.LabelFrame(main_frame, text="Robot Status", padding="10")
        status_frame.pack(fill=tk.X, pady=5)

        self.lbl_mode = ttk.Label(status_frame, text="Mode: Unknown")
        self.lbl_mode.grid(row=0, column=0, padx=20)

        self.lbl_heading = ttk.Label(status_frame, text="Heading: 0°")
        self.lbl_heading.grid(row=0, column=1, padx=20)

        self.lbl_ai = ttk.Label(status_frame, text="AI: Ready")
        self.lbl_ai.grid(row=0, column=2, padx=20)

        # --- Command Entry (Substitute for Voice) ---
        cmd_frame = ttk.LabelFrame(main_frame, text="Manual Command (Type instead of speaking)", padding="10")
        cmd_frame.pack(fill=tk.X, pady=5)

        self.ent_cmd = ttk.Entry(cmd_frame, font=("Arial", 12))
        self.ent_cmd.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.ent_cmd.bind("<Return>", lambda e: self.send_command())

        btn_send = ttk.Button(cmd_frame, text="Send to Brain", command=self.send_command)
        btn_send.pack(side=tk.RIGHT)

        # --- Quick Action Buttons ---
        btn_frame = ttk.LabelFrame(main_frame, text="Quick Actions", padding="10")
        btn_frame.pack(fill=tk.X, pady=5)

        actions = [
            ("Stand", "stand"), ("Sit", "sit"), 
            ("Dance", "dance"), ("Fist Bump", "fist_bump"),
            ("Follow Me", "follow_person"), ("Stop", "stop")
        ]

        for i, (name, cmd) in enumerate(actions):
            btn = ttk.Button(btn_frame, text=name, command=lambda c=cmd: self.execute_quick_action(c))
            btn.grid(row=0, column=i, padx=5, pady=5)

        # --- Log Output ---
        log_frame = ttk.LabelFrame(main_frame, text="Logs / Console Output", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.txt_log = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 10))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # --- Controls ---
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=10)

        self.btn_toggle = ttk.Button(ctrl_frame, text="START ROBOT ENGINE", command=self.toggle_robot)
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

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
            self.log(f"User (Manual): {cmd}")
            # Inject command into robot state
            self.robot.current_state['voice_command'] = cmd
            self.ent_cmd.delete(0, tk.END)

    def execute_quick_action(self, action_name):
        self.log(f"Executing: {action_name}")
        self.robot.execute_action({'action': action_name})

    def _update_status_loop(self):
        """Update UI labels from robot state."""
        try:
            status = self.robot.get_status()
            mode = status.get('mode', 'simulation')
            heading = self.robot.heading
            
            self.lbl_mode.config(text=f"Mode: {mode.upper()}")
            self.lbl_heading.config(text=f"Heading: {heading:.1f}°")
            
            # Check if robot is thinking
            if self.robot.brain.decision_interval > 0:
                self.lbl_ai.config(text="AI Brain: Active")
        except:
            pass
        
        self.root.after(500, self._update_status_loop)

if __name__ == "__main__":
    root = tk.Tk()
    gui = ClankerGUI(root)
    root.mainloop()
