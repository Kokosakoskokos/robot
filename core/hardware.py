"""Hardware abstraction layer for Clanker robot system.

This module provides a unified interface for hardware components,
with automatic fallback to simulation mode when hardware isn't available.
"""

import sys
from typing import Optional, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)


class HardwareInterface:
    """Abstract base class for hardware interfaces."""
    
    def __init__(self, simulation_mode: bool = False):
        self.simulation_mode = simulation_mode
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize the hardware interface."""
        raise NotImplementedError
        
    def is_available(self) -> bool:
        """Check if hardware is available."""
        return not self.simulation_mode and self.initialized


class ServoController(HardwareInterface):
    """Servo controller interface supporting multiple PCA9685 controllers."""
    
    def __init__(self, simulation_mode: bool = False, addresses: Optional[Dict[str, int]] = None):
        super().__init__(simulation_mode)
        self.addresses = addresses or {"right": 0x40, "left": 0x41}
        self.kits = {}
        
        if not simulation_mode:
            self._try_init_hardware()
    
    def _try_init_hardware(self):
        """Try to initialize hardware servo controllers."""
        try:
            from adafruit_servokit import ServoKit
            for side, addr in self.addresses.items():
                try:
                    self.kits[side] = ServoKit(channels=16, address=addr)
                    logger.info(f"Servo controller ({side}) initialized at address {hex(addr)}")
                except Exception as e:
                    logger.error(f"Failed to initialize {side} servo controller at {hex(addr)}: {e}")
            
            if self.kits:
                self.initialized = True
            else:
                logger.warning("No servo controllers initialized, using simulation mode")
                self.simulation_mode = True
        except ImportError:
            logger.warning("adafruit_servokit not available, using simulation mode")
            self.simulation_mode = True
        except Exception as e:
            logger.warning(f"Failed to initialize servo controllers: {e}, using simulation mode")
            self.simulation_mode = True
    
    def set_angle(self, servo_id: int, angle: float) -> bool:
        """
        Set servo angle. Mapping: 0-15 -> kit['left'], 16-31 -> kit['right'] 
        (or based on leg logic in subsystems)
        """
        angle = max(0, min(180, angle))
        
        if self.simulation_mode:
            logger.debug(f"[SIM] Servo {servo_id} -> {angle:.1f}°")
            return True
        
        # Mapping logic (Example: 0-8 left legs, 9-17 right legs)
        # But we will use the side mapping directly from the hexapod controller
        # For simplicity, let's assume hexapod controller handles which kit to use.
        # We'll add a side parameter or use ID mapping.
        
        # Let's use ID mapping: 0-15 = kit['left'], 16-31 = kit['right']
        side = "left" if servo_id < 16 else "right"
        local_id = servo_id % 16
        
        if side not in self.kits:
            return False
            
        try:
            self.kits[side].servo[local_id].angle = angle
            return True
        except Exception as e:
            logger.error(f"Failed to set servo {servo_id} ({side}:{local_id}) angle: {e}")
            return False
    
    def get_angle(self, servo_id: int) -> Optional[float]:
        """Get current servo angle."""
        if self.simulation_mode:
            return None
        
        side = "left" if servo_id < 16 else "right"
        local_id = servo_id % 16
        
        if side not in self.kits:
            return None
            
        try:
            return self.kits[side].servo[local_id].angle
        except Exception as e:
            logger.error(f"Failed to get servo {servo_id} ({side}:{local_id}) angle: {e}")
            return None


class CameraInterface(HardwareInterface):
    """Camera interface with simulation mode support."""
    
    def __init__(self, simulation_mode: bool = False, device_id: int = 0, width: int = 640, height: int = 480):
        super().__init__(simulation_mode)
        self.device_id = device_id
        self.width = width
        self.height = height
        self.cap = None
        
        if not simulation_mode:
            self._try_init_hardware()
    
    def _try_init_hardware(self):
        """Try to initialize camera."""
        try:
            import cv2
            self.cap = cv2.VideoCapture(self.device_id)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.initialized = True
                logger.info(f"Camera initialized (device {self.device_id}, {self.width}x{self.height})")
            else:
                logger.warning("Camera failed to open, using simulation mode")
                self.simulation_mode = True
        except ImportError:
            logger.warning("OpenCV not available, using simulation mode")
            self.simulation_mode = True
        except Exception as e:
            logger.warning(f"Failed to initialize camera: {e}, using simulation mode")
            self.simulation_mode = True
    
    def read_frame(self):
        """Read a frame from the camera."""
        if self.simulation_mode:
            import numpy as np
            # Return a black frame in simulation
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        if not self.initialized or self.cap is None:
            return None
        
        try:
            ret, frame = self.cap.read()
            if ret:
                return frame
            return None
        except Exception as e:
            logger.error(f"Failed to read camera frame: {e}")
            return None
    
    def release(self):
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            logger.info("Camera released")


class GPSInterface(HardwareInterface):
    """GPS interface with simulation mode support."""
    
    def __init__(self, simulation_mode: bool = False, port: str = "/dev/ttyUSB0", baudrate: int = 9600):
        super().__init__(simulation_mode)
        self.port = port
        self.baudrate = baudrate
        self.gps_serial = None
        
        if not simulation_mode:
            self._try_init_hardware()
    
    def _try_init_hardware(self):
        """Try to initialize GPS module."""
        try:
            import serial
            self.gps_serial = serial.Serial(self.port, self.baudrate, timeout=1.0)
            self.initialized = True
            logger.info(f"GPS initialized on {self.port} at {self.baudrate} baud")
        except ImportError:
            logger.warning("pyserial not available, using simulation mode")
            self.simulation_mode = True
        except Exception as e:
            logger.warning(f"Failed to initialize GPS: {e}, using simulation mode")
            self.simulation_mode = True
    
    def get_position(self) -> Optional[Dict[str, float]]:
        """Get current GPS position."""
        if self.simulation_mode:
            # Return simulated position
            return {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}
        
        if not self.initialized:
            return None
        
        try:
            import pynmea2
            line = self.gps_serial.readline().decode('utf-8')
            if line.startswith('$GPGGA'):
                msg = pynmea2.parse(line)
                if msg.latitude and msg.longitude:
                    return {
                        "latitude": float(msg.latitude),
                        "longitude": float(msg.longitude),
                        "altitude": float(msg.altitude) if msg.altitude else 0.0
                    }
        except Exception as e:
            logger.debug(f"GPS read error: {e}")
        
        return None

