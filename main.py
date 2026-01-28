#!/usr/bin/env python3
"""Main entry point for Clanker robot system."""

import argparse
import sys
import os
import ctypes
import threading
from pathlib import Path

# Suppress ALSA errors as early as possible
if os.name != 'nt':
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so.2')
        asound.snd_lib_error_set_handler(None)
    except:
        pass

from core.robot import ClankerRobot
from utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Clanker - Autonomous Hexapod Robot System')
    parser.add_argument('--simulation', '-s', action='store_true',
                        help='Run in simulation mode (no hardware required)')
    parser.add_argument('--config', '-c', type=str, default='config/config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--test', '-t', action='store_true',
                        help='Run test sequence instead of autonomous mode')
    parser.add_argument('--say', type=str, default=None,
                        help='Speak a message (uses TTS language in config), then exit')
    parser.add_argument('--cmd', type=str, default=None,
                        help='Execute a specific action command (e.g., dance, fist_bump)')
    parser.add_argument('--gui', '-g', action='store_true',
                        help='Start the robot with Graphical User Interface')
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config).exists() and not args.simulation:
        logger.warning(f"Config file not found: {args.config}")
        logger.info("Running in simulation mode")
        args.simulation = True
    
    try:
        if args.gui:
            import tkinter as tk
            from gui import ClankerGUI
            logger.info("Launching Graphical User Interface...")
            root = tk.Tk()
            
            # Create GUI with robot_instance=None first
            # The GUI will handle starting the robot in a thread
            app = ClankerGUI(root, robot_instance=None)
            
            # Helper to init robot in background so GUI is not blocked
            def init_robot_task():
                try:
                    logger.info("Initializing Robot Hardware in background...")
                    robot = ClankerRobot(config_path=args.config, simulation_mode=args.simulation)
                    app.robot = robot
                    logger.info("Robot Hardware Ready.")
                except Exception as e:
                    logger.error(f"Failed to init robot hardware: {e}")
                    if hasattr(app, 'log'):
                        app.log(f"CHYBA STARTU: {e}")

            threading.Thread(target=init_robot_task, daemon=True).start()
            root.mainloop()
            return

        # Normal terminal mode
        robot = ClankerRobot(config_path=args.config, simulation_mode=args.simulation)
        
        if args.test:
            # Run test sequence
            logger.info("Running test sequence...")
            robot.hexapod.stand()
            import time
            time.sleep(2)
            robot.hexapod.walk_forward(steps=3)
            time.sleep(2)
            robot.hexapod.wave_leg(0)
            time.sleep(2)
            robot.hexapod.sit()
            logger.info("Test sequence complete")
        else:
            # Run autonomous mode
            logger.info("Starting autonomous operation...")
            robot.start()
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
