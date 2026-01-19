"""Hexapod servo control system.

Manages 18 servos (3 per leg) for a 6-legged robot.
Each leg has: coxa (hip), femur (thigh), tibia (shin)
"""

import math
import time
from typing import List, Tuple, Optional, Dict
from core.hardware import ServoController
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Leg:
    """Represents a single leg of the hexapod."""
    
    def __init__(self, leg_id: int, servo_controller: ServoController, 
                 coxa_length: float, femur_length: float, tibia_length: float):
        """
        Initialize a leg.
        
        Args:
            leg_id: Leg ID (0-5)
            servo_controller: Servo controller instance
            coxa_length: Length of coxa segment in mm
            femur_length: Length of femur segment in mm
            tibia_length: Length of tibia segment in mm
        """
        self.leg_id = leg_id
        self.servo_controller = servo_controller
        self.coxa_length = coxa_length
        self.femur_length = femur_length
        self.tibia_length = tibia_length
        
        # Servo IDs: leg_id * 3 + joint (0=coxa, 1=femur, 2=tibia)
        self.coxa_servo = leg_id * 3 + 0
        self.femur_servo = leg_id * 3 + 1
        self.tibia_servo = leg_id * 3 + 2
        
        # Current angles
        self.coxa_angle = 90.0
        self.femur_angle = 90.0
        self.tibia_angle = 90.0
    
    def set_angles(self, coxa: float, femur: float, tibia: float):
        """Set all three joint angles."""
        self.coxa_angle = coxa
        self.femur_angle = femur
        self.tibia_angle = tibia
        
        self.servo_controller.set_angle(self.coxa_servo, coxa)
        self.servo_controller.set_angle(self.femur_servo, femur)
        self.servo_controller.set_angle(self.tibia_servo, tibia)
    
    def inverse_kinematics(self, x: float, y: float, z: float) -> Tuple[float, float, float]:
        """
        Calculate inverse kinematics for leg position.
        
        Args:
            x: X position relative to coxa (forward/backward)
            y: Y position relative to coxa (left/right)
            z: Z position relative to coxa (up/down)
            
        Returns:
            Tuple of (coxa_angle, femur_angle, tibia_angle) in degrees
        """
        # Calculate coxa angle (rotation around vertical axis)
        coxa_angle = math.degrees(math.atan2(y, x))
        
        # Calculate distance in XY plane
        r = math.sqrt(x**2 + y**2) - self.coxa_length
        
        # Calculate distance to target point
        d = math.sqrt(r**2 + z**2)
        
        # Check if target is reachable
        max_reach = self.femur_length + self.tibia_length
        if d > max_reach:
            logger.warning(f"Leg {self.leg_id} target out of reach: {d:.1f}mm > {max_reach:.1f}mm")
            d = max_reach
        
        # Calculate femur and tibia angles using law of cosines
        # Angle between femur and line to target
        cos_femur = (self.femur_length**2 + d**2 - self.tibia_length**2) / (2 * self.femur_length * d)
        cos_femur = max(-1, min(1, cos_femur))  # Clamp to valid range
        femur_angle = math.degrees(math.acos(cos_femur)) + math.degrees(math.atan2(z, r))
        
        # Angle between femur and tibia
        cos_tibia = (self.femur_length**2 + self.tibia_length**2 - d**2) / (2 * self.femur_length * self.tibia_length)
        cos_tibia = max(-1, min(1, cos_tibia))  # Clamp to valid range
        tibia_angle = 180 - math.degrees(math.acos(cos_tibia))
        
        # Convert to servo angles (assuming servos are centered at 90 degrees)
        coxa_servo_angle = 90 + coxa_angle
        femur_servo_angle = 90 - femur_angle
        tibia_servo_angle = 90 - tibia_angle
        
        return (coxa_servo_angle, femur_servo_angle, tibia_servo_angle)
    
    def move_to(self, x: float, y: float, z: float):
        """Move leg tip to specified position using inverse kinematics."""
        coxa, femur, tibia = self.inverse_kinematics(x, y, z)
        self.set_angles(coxa, femur, tibia)


class HexapodController:
    """Main controller for hexapod robot with 6 legs."""
    
    def __init__(self, servo_controller: ServoController, 
                 coxa_length: float = 30, femur_length: float = 60, tibia_length: float = 80):
        """
        Initialize hexapod controller.
        
        Args:
            servo_controller: Servo controller instance
            coxa_length: Length of coxa segment in mm
            femur_length: Length of femur segment in mm
            tibia_length: Length of tibia segment in mm
        """
        self.servo_controller = servo_controller
        self.legs: List[Leg] = []
        
        # Create 6 legs
        for leg_id in range(6):
            leg = Leg(leg_id, servo_controller, coxa_length, femur_length, tibia_length)
            self.legs.append(leg)
        
        # Gait parameters
        self.stance_height = -50  # Height when leg is on ground (negative = down)
        self.lift_height = -30    # Height when leg is lifted
        self.step_length = 30     # Step length in mm
        self.step_height = 20     # Step height in mm
        
        # Leg positions (relative to body center)
        # Format: (x_offset, y_offset) for each leg
        self.leg_positions = [
            (40, 30),   # Front-left
            (40, -30),  # Front-right
            (0, 30),    # Mid-left
            (0, -30),   # Mid-right
            (-40, 30),  # Rear-left
            (-40, -30), # Rear-right
        ]
        
        logger.info("Hexapod controller initialized with 6 legs")
    
    def stand(self):
        """Move all legs to standing position."""
        logger.info("Standing up...")
        for i, leg in enumerate(self.legs):
            x_offset, y_offset = self.leg_positions[i]
            leg.move_to(x_offset, y_offset, self.stance_height)
        time.sleep(0.5)  # Allow servos to move
    
    def sit(self):
        """Move all legs to sitting position."""
        logger.info("Sitting down...")
        for i, leg in enumerate(self.legs):
            x_offset, y_offset = self.leg_positions[i]
            leg.move_to(x_offset, y_offset, -80)  # Lower body
        time.sleep(0.5)
    
    def walk_forward(self, steps: int = 1, speed: float = 0.1):
        """
        Walk forward using tripod gait.
        
        Args:
            steps: Number of steps to take
            speed: Speed of movement (seconds per step phase)
        """
        logger.info(f"Walking forward {steps} steps...")
        
        # Tripod gait: legs 0, 3, 4 move together, then 1, 2, 5
        tripod1 = [0, 3, 4]  # Front-left, mid-right, rear-left
        tripod2 = [1, 2, 5]  # Front-right, mid-left, rear-right
        
        for step in range(steps):
            # Phase 1: Lift tripod1, move tripod2 forward
            for leg_id in tripod1:
                x_offset, y_offset = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x_offset, y_offset, self.lift_height)
            
            for leg_id in tripod2:
                x_offset, y_offset = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x_offset + self.step_length, y_offset, self.stance_height)
            
            time.sleep(speed)
            
            # Phase 2: Lower tripod1, lift tripod2
            for leg_id in tripod1:
                x_offset, y_offset = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x_offset + self.step_length, y_offset, self.stance_height)
            
            for leg_id in tripod2:
                x_offset, y_offset = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x_offset, y_offset, self.lift_height)
            
            time.sleep(speed)
            
            # Phase 3: Lower tripod2
            for leg_id in tripod2:
                x_offset, y_offset = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x_offset, y_offset, self.stance_height)
            
            time.sleep(speed)
    
    def turn(self, angle: float, steps: int = 1, speed: float = 0.1):
        """
        Turn the robot.
        
        Args:
            angle: Turn angle in degrees (positive = left, negative = right)
            steps: Number of steps
            speed: Speed of movement
        """
        logger.info(f"Turning {angle} degrees...")
        # Simplified turning - rotate legs around body center
        # This is a simplified implementation
        for step in range(steps):
            # Similar to walk_forward but with rotation
            # Implementation would calculate rotated positions
            time.sleep(speed)
    
    def wave_leg(self, leg_id: int):
        """Wave a specific leg (for demonstration/attention)."""
        if leg_id < 0 or leg_id >= 6:
            logger.warning(f"Invalid leg_id: {leg_id}")
            return
        
        logger.info(f"Waving leg {leg_id}...")
        leg = self.legs[leg_id]
        x_offset, y_offset = self.leg_positions[leg_id]
        
        # Wave motion
        for _ in range(2):
            leg.move_to(x_offset + 20, y_offset, self.lift_height)
            time.sleep(0.3)
            leg.move_to(x_offset, y_offset, self.stance_height)
            time.sleep(0.3)
