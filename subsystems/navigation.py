"""Navigation and GPS module for Clanker robot."""

import math
from typing import Optional, Dict, Tuple, List
from core.hardware import GPSInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)


class NavigationSystem:
    """Navigation system using GPS and path planning."""
    
    def __init__(self, gps: GPSInterface):
        """
        Initialize navigation system.
        
        Args:
            gps: GPS interface instance
        """
        self.gps = gps
        self.current_position: Optional[Dict[str, float]] = None
        self.target_position: Optional[Dict[str, float]] = None
        self.path_history: List[Dict[str, float]] = []
        
        logger.info("Navigation system initialized")
    
    def update_position(self) -> bool:
        """Update current position from GPS."""
        position = self.gps.get_position()
        if position and position.get('latitude') != 0.0:  # Valid position
            self.current_position = position
            self.path_history.append(position.copy())
            # Keep only recent history
            if len(self.path_history) > 1000:
                self.path_history = self.path_history[-1000:]
            return True
        return False
    
    def get_current_position(self) -> Optional[Dict[str, float]]:
        """Get current position."""
        self.update_position()
        return self.current_position
    
    def set_target(self, latitude: float, longitude: float, altitude: Optional[float] = None):
        """
        Set target destination.
        
        Args:
            latitude: Target latitude
            longitude: Target longitude
            altitude: Target altitude (optional)
        """
        self.target_position = {
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude if altitude is not None else 0.0
        }
        logger.info(f"Target set: ({latitude}, {longitude})")
    
    def calculate_bearing(self, pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
        """
        Calculate bearing from pos1 to pos2.
        
        Args:
            pos1: Starting position (lat, lon)
            pos2: Target position (lat, lon)
            
        Returns:
            Bearing in degrees (0-360, 0 = North)
        """
        lat1 = math.radians(pos1['latitude'])
        lat2 = math.radians(pos2['latitude'])
        dlon = math.radians(pos2['longitude'] - pos1['longitude'])
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360
    
    def calculate_distance(self, pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
        """
        Calculate distance between two positions using Haversine formula.
        
        Args:
            pos1: First position (lat, lon)
            pos2: Second position (lat, lon)
            
        Returns:
            Distance in meters
        """
        R = 6371000  # Earth radius in meters
        
        lat1 = math.radians(pos1['latitude'])
        lat2 = math.radians(pos2['latitude'])
        dlat = lat2 - lat1
        dlon = math.radians(pos2['longitude'] - pos1['longitude'])
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def get_direction_to_target(self) -> Optional[Dict[str, float]]:
        """
        Get direction and distance to target.
        
        Returns:
            Dictionary with 'bearing' (degrees), 'distance' (meters), or None if no target/position
        """
        if self.current_position is None:
            self.update_position()
        
        if self.current_position is None or self.target_position is None:
            return None
        
        bearing = self.calculate_bearing(self.current_position, self.target_position)
        distance = self.calculate_distance(self.current_position, self.target_position)
        
        return {
            'bearing': bearing,
            'distance': distance
        }
    
    def is_at_target(self, tolerance_meters: float = 5.0) -> bool:
        """
        Check if robot is at target position.
        
        Args:
            tolerance_meters: Distance tolerance in meters
            
        Returns:
            True if within tolerance of target
        """
        direction = self.get_direction_to_target()
        if direction is None:
            return False
        
        return direction['distance'] <= tolerance_meters
    
    def get_path_statistics(self) -> Dict:
        """Get statistics about the path traveled."""
        if len(self.path_history) < 2:
            return {'total_distance': 0.0, 'points': 0}
        
        total_distance = 0.0
        for i in range(1, len(self.path_history)):
            distance = self.calculate_distance(
                self.path_history[i-1],
                self.path_history[i]
            )
            total_distance += distance
        
        return {
            'total_distance': total_distance,
            'points': len(self.path_history),
            'average_speed': total_distance / len(self.path_history) if self.path_history else 0.0
        }
