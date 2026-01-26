#!/usr/bin/env python3
"""
Calibration script for Clanker hexapod.
Sets all servos to 90 degrees for mechanical alignment.
"""

import time
import yaml
from core.hardware import ServoController
from utils.logger import setup_logger

logger = setup_logger(__name__)

def calibrate():
    print("=" * 60)
    print("Clanker Hexapod - Servo Calibration")
    print("=" * 60)
    print("This script will set ALL 18 servos to 90 degrees.")
    print("Use this to mount the legs in the 'FLAT' (horizontal) position.")
    
    # Load config to get addresses
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        addresses = {
            "left": config['servos']['pca9685_left_address'],
            "right": config['servos']['pca9685_right_address']
        }
    except Exception as e:
        print(f"Error loading config: {e}")
        addresses = {"left": 0x41, "right": 0x40}

    print(f"Using addresses: Left={hex(addresses['left'])}, Right={hex(addresses['right'])}")
    
    # Initialize controller in hardware mode
    controller = ServoController(simulation_mode=False, addresses=addresses)
    
    if not controller.initialized:
        print("❌ Could not initialize hardware. Make sure PCA9685 is connected and I2C is enabled.")
        return

    print("\nSetting all servos to 90 degrees...")
    
    # Left legs (0-8 on 0x41)
    for i in range(9):
        controller.set_angle(i, 90)
    
    # Right legs (16-24 on 0x40)
    for i in range(16, 25):
        controller.set_angle(i, 90)
        
    print("✅ Done. All servos are now centered at 90°.")
    print("You can now mount the leg segments in the horizontal position.")
    print("Keep the power ON while mounting to ensure servos stay centered.")

if __name__ == "__main__":
    calibrate()
