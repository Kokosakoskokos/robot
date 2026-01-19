"""Example usage of Clanker robot system."""

from core.robot import ClankerRobot
import time

def main():
    """Basic usage example."""
    print("Initializing Clanker robot in simulation mode...")
    
    # Create robot instance
    robot = ClankerRobot(simulation_mode=True)
    
    print("\n=== Test 1: Stand Up ===")
    robot.hexapod.stand()
    time.sleep(2)
    
    print("\n=== Test 2: Walk Forward ===")
    robot.hexapod.walk_forward(steps=3, speed=0.2)
    time.sleep(1)
    
    print("\n=== Test 3: Wave Leg ===")
    robot.hexapod.wave_leg(0)
    time.sleep(1)
    
    print("\n=== Test 4: Vision System ===")
    frame = robot.vision.capture_frame()
    detections = robot.vision.detect_objects(frame)
    print(f"Detected {len(detections)} objects")
    
    env_info = robot.vision.get_environment_info()
    print(f"Environment info: {env_info}")
    
    print("\n=== Test 5: Navigation ===")
    # Set a target (example coordinates)
    robot.set_navigation_target(latitude=37.7749, longitude=-122.4194)
    
    nav_info = robot.navigation.get_direction_to_target()
    if nav_info:
        print(f"Direction to target: {nav_info['bearing']:.1f}°, {nav_info['distance']:.1f}m")
    
    print("\n=== Test 6: AI Brain ===")
    robot.update_state()
    action = robot.brain.think(robot.current_state)
    print(f"AI decision: {action}")
    
    print("\n=== Test 7: Self-Analysis ===")
    analysis = robot.brain.self_analyze()
    print(f"Code analysis: {analysis['total_functions']} functions, {analysis['total_classes']} classes")
    
    print("\n=== Test 8: Sit Down ===")
    robot.hexapod.sit()
    time.sleep(1)
    
    print("\nAll tests complete!")

if __name__ == '__main__':
    main()
