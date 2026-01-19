"""Autonomous operation demo for Clanker robot."""

from core.robot import ClankerRobot
import signal
import sys

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print('\nShutdown signal received...')
    sys.exit(0)

def main():
    """Run autonomous demo."""
    print("=" * 60)
    print("Clanker Robot - Autonomous Operation Demo")
    print("=" * 60)
    print("\nThis demo shows the robot operating autonomously.")
    print("The AI brain will make decisions based on sensor data.")
    print("\nPress Ctrl+C to stop.\n")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create robot in simulation mode
    robot = ClankerRobot(simulation_mode=True)
    
    # Optionally set a navigation target
    # robot.set_navigation_target(latitude=37.7749, longitude=-122.4194)
    
    # Start autonomous operation
    print("Starting autonomous operation...\n")
    robot.start()

if __name__ == '__main__':
    main()
