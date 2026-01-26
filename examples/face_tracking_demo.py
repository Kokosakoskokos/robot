#!/usr/bin/env python3
"""
Face Tracking Demo for Clanker Robot
====================================

This script demonstrates the face tracking and person following capabilities
of the Clanker robot.

Usage:
    python examples/face_tracking_demo.py --simulation
    python examples/face_tracking_demo.py --train <name>
    python examples/face_tracking_demo.py --follow <name>
"""

import sys
import time
import cv2
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.robot import ClankerRobot
from utils.logger import setup_logger

logger = setup_logger(__name__)


def demo_detect_faces(simulation: bool = False):
    """Demo face detection."""
    print("=" * 60)
    print("Face Detection Demo")
    print("=" * 60)
    
    robot = ClankerRobot(simulation_mode=simulation)
    
    print("\nInitializing face tracking...")
    print("Camera: Ready")
    print("Face detection: Ready")
    
    if simulation:
        print("\n⚠️  Running in simulation mode")
        print("   Real face detection requires a camera with OpenCV")
        print("   Simulation will randomly show face detections")
    
    print("\nStarting face detection...")
    print("Press Ctrl+C to stop\n")
    
    try:
        frame_count = 0
        detection_count = 0
        
        while True:
            # Capture frame
            frame = robot.vision.capture_frame()
            
            if frame is None:
                logger.warning("Could not capture frame")
                time.sleep(1)
                continue
            
            # Detect faces
            faces = robot.face_tracker.detect_faces(frame)
            
            # Draw detection info on frame
            display_frame = frame.copy()
            
            if faces:
                detection_count += 1
                for face in faces:
                    x, y, w, h = face['bbox']
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Face", (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # Show distance
                    if face['distance_estimate']:
                        distance = face['distance_estimate']
                        cv2.putText(display_frame, f"{int(distance)}mm", 
                                   (x, y + h + 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            # Show detection info
            cv2.putText(display_frame, f"Frame: {frame_count}", (10, 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display_frame, f"Faces: {len(faces)}", (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display
            cv2.imshow('Face Tracking Demo', display_frame)
            
            # Print info every 10 frames
            if frame_count % 10 == 0:
                status = robot.face_tracker.get_tracking_status()
                print(f"Frame {frame_count}: {len(faces)} faces detected")
            
            frame_count += 1
            
            # Check for key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                break
            elif key == ord('s'):  # s to save screenshot
                filename = f"face_detection_{frame_count}.jpg"
                cv2.imwrite(filename, display_frame)
                print(f"Screenshot saved: {filename}")
        
    except KeyboardInterrupt:
        print("\nStopping face detection...")
    finally:
        cv2.destroyAllWindows()
        robot.shutdown()
    
    print(f"\nDemo complete!")
    print(f"Frames processed: {frame_count}")
    print(f"Detections: {detection_count}")


def demo_follow_person(simulation: bool = False, person_name: str = None):
    """Demo person following."""
    print("=" * 60)
    print("Person Following Demo")
    print("=" * 60)
    
    robot = ClankerRobot(simulation_mode=simulation)
    
    print(f"\nTarget person: {person_name or 'Any person'}")
    print("Initializing face tracking...")
    print("Camera: Ready")
    print("Face tracking: Ready")
    
    if simulation:
        print("\n⚠️  Running in simulation mode")
        print("   Robot will randomly detect and follow simulated faces")
    
    print("\nStarting person following...")
    print("Press Ctrl+C to stop\n")
    
    try:
        frame_count = 0
        follow_count = 0
        
        while True:
            # Capture frame
            frame = robot.vision.capture_frame()
            
            if frame is None:
                logger.warning("Could not capture frame")
                time.sleep(1)
                continue
            
            # Track person
            tracking = robot.face_tracker.track_person(frame, person_name)
            
            # Draw tracking info on frame
            display_frame = frame.copy()
            
            if tracking['person_found']:
                follow_count += 1
                
                # Draw bounding box
                if tracking['bbox']:
                    x, y, w, h = tracking['bbox']
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
                    
                    # Draw person name
                    name = tracking['person_name']
                    cv2.putText(display_frame, name, (x, y - 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    
                    # Draw distance
                    if tracking['distance']:
                        distance = tracking['distance']
                        cv2.putText(display_frame, f"{int(distance)}mm", 
                                   (x, y + h + 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # Draw confidence
                confidence = tracking['confidence']
                cv2.putText(display_frame, f"Conf: {confidence:.1%}", 
                           (10, display_frame.shape[0] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Show tracking status
            status_text = "Tracking: " + ("ACTIVE" if tracking['person_found'] else "SEARCHING")
            color = (0, 255, 0) if tracking['person_found'] else (0, 0, 255)
            cv2.putText(display_frame, status_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # Calculate follow action
            if tracking['person_found']:
                follow_action = robot.face_tracker.follow_person(frame, robot.heading)
                
                if follow_action:
                    action_text = f"Action: {follow_action['action']}"
                    if 'angle' in follow_action:
                        action_text += f" {follow_action['angle']}°"
                    if 'steps' in follow_action:
                        action_text += f" {follow_action['steps']} steps"
                    
                    cv2.putText(display_frame, action_text, (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    cv2.putText(display_frame, f"Reason: {follow_action['reason']}", 
                               (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Show frame info
            cv2.putText(display_frame, f"Frame: {frame_count}", (10, display_frame.shape[0] - 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display
            cv2.imshow('Person Following Demo', display_frame)
            
            # Print info every 10 frames
            if frame_count % 10 == 0:
                if tracking['person_found']:
                    print(f"Frame {frame_count}: Following {tracking['person_name']} at {tracking['distance']}mm")
                else:
                    print(f"Frame {frame_count}: Searching for person...")
            
            frame_count += 1
            
            # Check for key press
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # q or ESC
                break
            elif key == ord('s'):  # s to save screenshot
                filename = f"person_follow_{frame_count}.jpg"
                cv2.imwrite(filename, display_frame)
                print(f"Screenshot saved: {filename}")
        
    except KeyboardInterrupt:
        print("\nStopping person following...")
    finally:
        cv2.destroyAllWindows()
        robot.shutdown()
    
    print(f"\nDemo complete!")
    print(f"Frames processed: {frame_count}")
    print(f"Follow attempts: {follow_count}")


def demo_train_face(simulation: bool = False, name: str = "User"):
    """Demo face training."""
    print("=" * 60)
    print("Face Training Demo")
    print("=" * 60)
    
    robot = ClankerRobot(simulation_mode=simulation)
    
    print(f"\nTraining face for: {name}")
    print("Initializing face tracking...")
    print("Camera: Ready")
    
    if simulation:
        print("\n⚠️  Running in simulation mode")
        print("   Face training requires real camera")
    
    print("\nPosition face in camera view...")
    print("Press Space to capture training sample")
    print("Press 't' to train (collect 5 samples)")
    print("Press 'q' to quit\n")
    
    try:
        frame_count = 0
        training_samples = []
        target_samples = 5
        
        while True:
            # Capture frame
            frame = robot.vision.capture_frame()
            
            if frame is None:
                logger.warning("Could not capture frame")
                time.sleep(1)
                continue
            
            # Detect faces
            faces = robot.face_tracker.detect_faces(frame)
            
            # Draw on frame
            display_frame = frame.copy()
            
            if faces:
                for face in faces:
                    x, y, w, h = face['bbox']
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(display_frame, "Face detected", (x, y - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Show info
            cv2.putText(display_frame, f"Sample: {len(training_samples)}/{target_samples}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.putText(display_frame, f"Target: {name}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            cv2.imshow('Face Training Demo', display_frame)
            
            # Key handling
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' ') and len(faces) > 0:  # Space to capture
                training_samples.append(frame.copy())
                print(f"Captured sample {len(training_samples)}/{target_samples}")
                
                if len(training_samples) >= target_samples:
                    print("\nCollected enough samples! Press 't' to train")
            
            elif key == ord('t') and len(training_samples) >= target_samples:
                print(f"\nTraining face for '{name}' with {len(training_samples)} samples...")
                
                # Train with each sample
                for i, sample in enumerate(training_samples):
                    success = robot.face_tracker.train_face(sample, name)
                    if success:
                        print(f"  Sample {i+1}: ✓ Trained")
                    else:
                        print(f"  Sample {i+1}: ✗ No face detected")
                
                print(f"\n✓ Training complete!")
                print(f"  Known faces: {list(robot.face_tracker.known_faces.keys())}")
                break
            
            elif key == ord('q'):
                print("\nTraining cancelled")
                break
            
            frame_count += 1
        
    except KeyboardInterrupt:
        print("\nTraining interrupted...")
    finally:
        cv2.destroyAllWindows()
        robot.shutdown()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Face Tracking Demo for Clanker Robot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python examples/face_tracking_demo.py --simulation
  python examples/face_tracking_demo.py --train "John"
  python examples/face_tracking_demo.py --follow "John"
        """
    )
    
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in simulation mode (no real camera)"
    )
    
    parser.add_argument(
        "--train",
        type=str,
        metavar="NAME",
        help="Train face for a person (e.g., --train 'John')"
    )
    
    parser.add_argument(
        "--follow",
        type=str,
        metavar="NAME",
        help="Follow a specific person (e.g., --follow 'John')"
    )
    
    parser.add_argument(
        "--detect",
        action="store_true",
        help="Demo face detection only"
    )
    
    args = parser.parse_args()
    
    # Determine which demo to run
    if args.train:
        demo_train_face(args.simulation, args.train)
    elif args.follow:
        demo_follow_person(args.simulation, args.follow)
    elif args.detect or not (args.train or args.follow):
        demo_detect_faces(args.simulation)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
