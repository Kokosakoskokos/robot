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
        # Mapping for two controllers:
        # Left legs (0, 2, 4) -> IDs 0-8 on controller 0x41
        # Right legs (1, 3, 5) -> IDs 16-24 on controller 0x40 (using 16+ as offset)
        if leg_id % 2 == 0:  # Left legs
            base_id = (leg_id // 2) * 3
        else:                # Right legs
            base_id = 16 + (leg_id // 2) * 3
            
        self.coxa_servo = base_id + 0
        self.femur_servo = base_id + 1
        self.tibia_servo = base_id + 2
        
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
        
        # Convert to servo angles
        # Coxa: 90 is center
        coxa_servo_angle = 90 + coxa_angle
        # Femur: 90 is horizontal
        femur_servo_angle = 90 - femur_angle
        # Tibia: 90 is perpendicular (90 deg to femur)
        # If tibia_angle (from 180-beta) is 90, servo is 90. 
        # If tibia_angle is 0 (beta=180, flat), servo is 180.
        tibia_servo_angle = 180 - tibia_angle
        
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
    
    def crab_walk(self, steps: int = 1, direction: str = "left", speed: float = 0.1):
        """Walk sideways."""
        logger.info(f"Crab walking {direction} {steps} steps...")
        y_step = 30 if direction == "left" else -30
        
        tripod1 = [0, 3, 4]
        tripod2 = [1, 2, 5]
        
        for step in range(steps):
            # Phase 1: Lift tripod1, shift tripod2
            for leg_id in tripod1:
                x, y = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x, y, self.lift_height)
            for leg_id in tripod2:
                x, y = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x, y + y_step, self.stance_height)
            time.sleep(speed)
            
            # Phase 2: Lower tripod1, lift tripod2
            for leg_id in tripod1:
                x, y = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x, y + y_step, self.stance_height)
            for leg_id in tripod2:
                x, y = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x, y, self.lift_height)
            time.sleep(speed)
            
            # Phase 3: Lower tripod2
            for leg_id in tripod2:
                x, y = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x, y, self.stance_height)
            time.sleep(speed)

    def fist_bump(self):
        """Perform a fist bump with the front-right leg (leg 1)."""
        logger.info("Fist bump!")
        leg = self.legs[1]
        x, y = self.leg_positions[1]
        
        # Lift and move forward
        leg.move_to(x + 40, y, 20)
        time.sleep(0.5)
        # Bump forward
        leg.move_to(x + 60, y, 20)
        time.sleep(0.3)
        # Retract
        leg.move_to(x + 40, y, 20)
        time.sleep(0.5)
        # Back to ground
        leg.move_to(x, y, self.stance_height)

    def dance(self):
        """A simple happy dance."""
        logger.info("Dancing!")
        for _ in range(3):
            # Tilt left
            for i in [0, 2, 4]: self.legs[i].move_to(*self.leg_positions[i], -30)
            for i in [1, 3, 5]: self.legs[i].move_to(*self.leg_positions[i], -70)
            time.sleep(0.3)
            # Tilt right
            for i in [0, 2, 4]: self.legs[i].move_to(*self.leg_positions[i], -70)
            for i in [1, 3, 5]: self.legs[i].move_to(*self.leg_positions[i], -30)
            time.sleep(0.3)
        self.stand()

    def turn(self, angle: float, steps: int = 1, speed: float = 0.1):
        """Improved turning logic."""
        logger.info(f"Turning {angle} degrees...")
        # Positive = Left, Negative = Right
        tripod1 = [0, 3, 4]
        tripod2 = [1, 2, 5]
        
        rotation = math.radians(angle / steps)
        
        for step in range(steps):
            # Phase 1: Lift tripod1
            for leg_id in tripod1:
                x, y = self.leg_positions[leg_id]
                # Rotate coordinates
                new_x = x * math.cos(rotation) - y * math.sin(rotation)
                new_y = x * math.sin(rotation) + y * math.cos(rotation)
                self.legs[leg_id].move_to(new_x, new_y, self.lift_height)
            time.sleep(speed)
            
            # Phase 2: Lower tripod1, lift tripod2
            for leg_id in tripod1:
                x, y = self.leg_positions[leg_id]
                new_x = x * math.cos(rotation) - y * math.sin(rotation)
                new_y = x * math.sin(rotation) + y * math.cos(rotation)
                self.legs[leg_id].move_to(new_x, new_y, self.stance_height)
            
            for leg_id in tripod2:
                x, y = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x, y, self.lift_height)
            time.sleep(speed)
            
            # Phase 3: Lower tripod2
            for leg_id in tripod2:
                x, y = self.leg_positions[leg_id]
                self.legs[leg_id].move_to(x, y, self.stance_height)
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
