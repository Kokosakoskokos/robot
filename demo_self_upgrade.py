#!/usr/bin/env python3
"""
Demonstration of AI self-upgrading code.
Robot receives a command for a behavior it wants to improve or doesn't have,
calculates the physics/stability, creates the code, and then executes it.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.robot import ClankerRobot
from utils.logger import setup_logger

logger = setup_logger(__name__)

def demo():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found. Please set it to run the AI demo.")
        return

    print("=" * 60)
    print("DEMO: AI SELF-UPGRADE (Auto-coding 'WaveAtUser')")
    print("=" * 60)

    # Initialize robot in simulation mode
    robot = ClankerRobot(simulation_mode=True)
    
    # 1. Simulate the environment and voice command
    print("\n[User]: 'Zamávej na mě, ale tak, abys u toho nespadl a využil celou délku nohy.'")
    
    simulated_state = {
        'mode': 'simulation',
        'obstacles': [],
        'detections': [{'label': 'person', 'confidence': 0.9, 'bbox': [200, 100, 100, 200]}],
        'position': {'latitude': 50.0, 'longitude': 14.0},
        'heading': 0.0,
        'voice_command': 'Zamávej na mě, ale tak, abys u toho nespadl a využil celou délku nohy.',
        'frame_width': 640,
        'frame_height': 480,
        'battery_level': 0.8
    }

    print("\n[Robot Brain]: Analyzing request and physical constraints...")
    print(f"Constraints: Coxa=30mm, Femur=60mm, Tibia=80mm, Total Reach=170mm")
    print("Stability Check: Tripod base + 2 support legs active.")

    # 2. Get AI decision
    action = robot.brain.think(simulated_state)
    
    print("\n" + "-" * 40)
    print("AI DECISION:")
    print(json.dumps(action, indent=2, ensure_ascii=False))
    print("-" * 40)

    # 3. Execute the action (This will trigger code creation if the AI chose 'create_behavior')
    if action['action'] == 'create_behavior':
        print(f"\n[System]: AI decided to CREATE a new behavior: {action['behavior_name']}")
        robot.execute_action(action)
        
        # Verify the file was created
        behavior_file = Path(f"ai/behaviors/{action['behavior_name'].lower()}.py")
        if behavior_file.exists():
            print(f"✅ SUCCESS: New behavior file created at {behavior_file}")
            print("\n--- GENERATED CODE PREVIEW ---")
            with open(behavior_file, 'r', encoding='utf-8') as f:
                print(f.read())
            print("------------------------------")
        else:
            print("❌ Error: Behavior file was not created.")
    else:
        print(f"\n[System]: AI chose existing action: {action['action']}")
        if 'speech' in action:
            print(f"Robot says: {action['speech']}")

if __name__ == "__main__":
    demo()
