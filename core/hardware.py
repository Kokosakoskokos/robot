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
    """Servo controller interface with simulation mode support."""
    
    def __init__(self, simulation_mode: bool = False, pca9685_address: int = 0x40):
        super().__init__(simulation_mode)
        self.pca9685_address = pca9685_address
        self.servo_kit = None
        
        if not simulation_mode:
            self._try_init_hardware()
    
    def _try_init_hardware(self):
        """Try to initialize hardware servo controller."""
        try:
            from adafruit_servokit import ServoKit
            self.servo_kit = ServoKit(channels=16, address=self.pca9685_address)
            self.initialized = True
            logger.info(f"Servo controller initialized at address {hex(self.pca9685_address)}")
        except ImportError:
            logger.warning("adafruit_servokit not available, using simulation mode")
            self.simulation_mode = True
        except Exception as e:
            logger.warning(f"Failed to initialize servo controller: {e}, using simulation mode")
            self.simulation_mode = True
    
    def set_angle(self, servo_id: int, angle: float) -> bool:
        """
        Set servo angle.
        
        Args:
            servo_id: Servo ID (0-17 for 18 servos)
            angle: Angle in degrees (0-180)
            
        Returns:
            True if successful
        """
        angle = max(0, min(180, angle))  # Clamp to valid range
        
        if self.simulation_mode:
            logger.debug(f"[SIM] Servo {servo_id} -> {angle:.1f}°")
            return True
        
        if not self.initialized:
            logger.warning(f"Servo controller not initialized, simulating servo {servo_id} -> {angle:.1f}°")
            return False
        
        try:
            self.servo_kit.servo[servo_id].angle = angle
            return True
        except Exception as e:
            logger.error(f"Failed to set servo {servo_id} angle: {e}")
            return False
    
    def get_angle(self, servo_id: int) -> Optional[float]:
        """Get current servo angle."""
        if self.simulation_mode:
            return None
        
        if not self.initialized:
            return None
        
        try:
            return self.servo_kit.servo[servo_id].angle
        except Exception as e:
            logger.error(f"Failed to get servo {servo_id} angle: {e}")
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


class DisplayInterface(HardwareInterface):
    """OLED display interface with simulation mode support."""
    
    def __init__(self, simulation_mode: bool = False, width: int = 128, height: int = 64, i2c_address: int = 0x3C):
        super().__init__(simulation_mode)
        self.width = width
        self.height = height
        self.i2c_address = i2c_address
        self.display = None
        
        if not simulation_mode:
            self._try_init_hardware()
    
    def _try_init_hardware(self):
        """Try to initialize OLED display."""
        try:
            import board
            import busio
            from adafruit_ssd1306 import SSD1306_I2C
            from PIL import Image, ImageDraw, ImageFont
            
            i2c = busio.I2C(board.SCL, board.SDA)
            self.display = SSD1306_I2C(self.width, self.height, i2c, addr=self.i2c_address)
            self.initialized = True
            logger.info(f"OLED display initialized ({self.width}x{self.height})")
        except ImportError:
            logger.warning("OLED display libraries not available, using simulation mode")
            self.simulation_mode = True
        except Exception as e:
            logger.warning(f"Failed to initialize OLED display: {e}, using simulation mode")
            self.simulation_mode = True
    
    def show_text(self, text: str, x: int = 0, y: int = 0):
        """Display text on OLED."""
        if self.simulation_mode:
            logger.debug(f"[SIM] Display: {text[:50]}")
            return
        
        if not self.initialized:
            return
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            image = Image.new('1', (self.width, self.height))
            draw = ImageDraw.Draw(image)
            
            # Try to use default font
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            draw.text((x, y), text, font=font, fill=255)
            self.display.image(image)
            self.display.show()
        except Exception as e:
            logger.error(f"Failed to update display: {e}")
    
    def clear(self):
        """Clear the display."""
        if self.simulation_mode:
            return
        
        if not self.initialized:
            return
        
        try:
            self.display.fill(0)
            self.display.show()
        except Exception as e:
            logger.error(f"Failed to clear display: {e}")
