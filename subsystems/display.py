"""OLED display interface for Clanker robot."""

from typing import Optional
from core.hardware import DisplayInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DisplayManager:
    """Manages OLED display output."""
    
    def __init__(self, display: DisplayInterface):
        """
        Initialize display manager.
        
        Args:
            display: Display interface instance
        """
        self.display = display
        self.current_screen = "status"
        
        logger.info("Display manager initialized")
    
    def show_status(self, status: Dict):
        """
        Display robot status information.
        
        Args:
            status: Dictionary with status information
        """
        lines = []
        
        # Mode
        mode = status.get('mode', 'unknown')
        lines.append(f"Mode: {mode}")
        
        # Position
        if 'position' in status:
            pos = status['position']
            lat = pos.get('latitude', 0)
            lon = pos.get('longitude', 0)
            lines.append(f"Pos: {lat:.4f}")
            lines.append(f"     {lon:.4f}")
        
        # Battery/Status
        if 'battery' in status:
            lines.append(f"Batt: {status['battery']}%")
        
        # Activity
        if 'activity' in status:
            lines.append(f"Act: {status['activity']}")
        
        # Combine lines
        text = "\n".join(lines[:4])  # Display can show ~4 lines
        self.display.show_text(text)
    
    def show_message(self, message: str, duration: float = 2.0):
        """
        Show a temporary message.
        
        Args:
            message: Message to display
            duration: Duration in seconds (not implemented in simulation)
        """
        self.display.show_text(message)
    
    def clear(self):
        """Clear the display."""
        self.display.clear()
    
    def show_vision_info(self, detections: int, obstacles: int):
        """Show vision system information."""
        text = f"Vision:\nDet: {detections}\nObs: {obstacles}"
        self.display.show_text(text)
    
    def show_navigation_info(self, bearing: Optional[float], distance: Optional[float]):
        """Show navigation information."""
        if bearing is None or distance is None:
            text = "Nav: No target"
        else:
            text = f"Nav:\nDir: {bearing:.0f}°\nDist: {distance:.1f}m"
        self.display.show_text(text)
