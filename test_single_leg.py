#!/usr/bin/env python3
"""
Interactive single leg test for Clanker hexapod.
Allows moving one leg using IK coordinates.
"""

import sys
import time
import yaml
from core.hardware import ServoController
from subsystems.servos import HexapodController

def main():
    print("=" * 60)
    print("Clanker Hexapod - Single Leg Tester")
    print("=" * 60)
    
    # Load config
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

    # Init hardware
    controller = ServoController(simulation_mode=False, addresses=addresses)
    if not controller.initialized:
        print("❌ Hardware init failed. Check connections.")
        return

    hexapod = HexapodController(controller)
    
    print("\nLeg IDs: 0=FL, 1=FR, 2=ML, 3=MR, 4=RL, 5=RR")
    try:
        leg_id = int(input("Which leg is assembled? (0-5): "))
        if not (0 <= leg_id <= 5): raise ValueError
    except:
        print("Invalid leg ID. Exiting.")
        return

    leg = hexapod.legs[leg_id]
    # Starting position (relative to body center)
    curr_x, curr_y = hexapod.leg_positions[leg_id]
    curr_z = hexapod.stance_height

    print(f"\nTesting Leg {leg_id}")
    print("Controls:")
    print("  W / S : Forward / Backward")
    print("  A / D : Left / Right")
    print("  R / F : Up / Down")
    print("  Space : Center position")
    print("  Q     : Quit")
    
    step = 5 # mm per key press

    while True:
        leg.move_to(curr_x, curr_y, curr_z)
        print(f"\rCurrent POS -> X: {curr_x:.1f}, Y: {curr_y:.1f}, Z: {curr_z:.1f}    ", end="")
        
        cmd = input("\nEnter command: ").lower()
        
        if cmd == 'w': curr_x += step
        elif cmd == 's': curr_x -= step
        elif cmd == 'a': curr_y += step
        elif cmd == 'd': curr_y -= step
        elif cmd == 'r': curr_z += step
        elif cmd == 'f': curr_z -= step
        elif cmd == ' ': 
            curr_x, curr_y = hexapod.leg_positions[leg_id]
            curr_z = hexapod.stance_height
        elif cmd == 'q':
            print("\nExiting...")
            break
        else:
            print("\nUnknown command.")

if __name__ == "__main__":
    main()
