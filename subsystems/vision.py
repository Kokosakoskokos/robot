"""Computer vision module for Clanker robot."""

import numpy as np
from typing import Optional, List, Dict, Tuple
from core.hardware import CameraInterface
from utils.logger import setup_logger

logger = setup_logger(__name__)


class VisionSystem:
    """Computer vision system for object detection and environment awareness."""
    
    def __init__(self, camera: CameraInterface):
        """
        Initialize vision system.
        
        Args:
            camera: Camera interface instance
        """
        self.camera = camera
        self.frame_count = 0
        self.detection_history: List[Dict] = []
        
        logger.info("Vision system initialized")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from the camera."""
        frame = self.camera.read_frame()
        if frame is not None:
            self.frame_count += 1
        return frame
    
    def detect_objects(self, frame: Optional[np.ndarray] = None) -> List[Dict]:
        """
        Detect objects in the frame.
        
        Args:
            frame: Input frame (if None, captures new frame)
            
        Returns:
            List of detected objects with bounding boxes and confidence
        """
        if frame is None:
            frame = self.capture_frame()
        
        if frame is None:
            return []
        
        # Simplified object detection
        # In a full implementation, this would use YOLO, TensorFlow, or similar
        detections = []
        
        # Basic color-based detection (placeholder)
        # Convert to HSV for better color detection
        try:
            import cv2
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Example: detect red objects
            lower_red = np.array([0, 50, 50])
            upper_red = np.array([10, 255, 255])
            mask = cv2.inRange(hsv, lower_red, upper_red)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 500:  # Minimum area threshold
                    x, y, w, h = cv2.boundingRect(contour)
                    detections.append({
                        'class': 'object',
                        'confidence': min(1.0, area / 10000),
                        'bbox': (x, y, w, h),
                        'center': (x + w // 2, y + h // 2)
                    })
        except ImportError:
            # Simulation mode - return empty detections
            pass
        except Exception as e:
            logger.error(f"Error in object detection: {e}")
        
        # Store detection history
        if detections:
            self.detection_history.extend(detections)
            # Keep only recent history
            if len(self.detection_history) > 100:
                self.detection_history = self.detection_history[-100:]
        
        return detections
    
    def detect_obstacles(self, frame: Optional[np.ndarray] = None) -> List[Dict]:
        """
        Detect obstacles in the robot's path.
        
        Returns:
            List of obstacles with position and size information
        """
        detections = self.detect_objects(frame)
        obstacles = []
        
        for det in detections:
            # Filter for obstacles (objects in lower portion of frame)
            center_y = det['center'][1]
            frame_height = self.camera.height if hasattr(self.camera, 'height') else 480
            
            if center_y > frame_height * 0.6:  # Lower 40% of frame
                obstacles.append({
                    'position': det['center'],
                    'size': det['bbox'][2] * det['bbox'][3],
                    'distance_estimate': self._estimate_distance(det['bbox'][3])
                })
        
        return obstacles
    
    def _estimate_distance(self, height_pixels: int) -> float:
        """
        Estimate distance to object based on height in pixels.
        This is a simplified estimation.
        
        Args:
            height_pixels: Height of object in pixels
            
        Returns:
            Estimated distance in mm
        """
        # Simplified distance estimation
        # In reality, this would use camera calibration and known object sizes
        if height_pixels == 0:
            return float('inf')
        
        # Rough estimate: larger objects are closer
        # This is a placeholder calculation
        focal_length_estimate = 500  # pixels
        object_height_mm = 100  # assumed object height
        distance_mm = (focal_length_estimate * object_height_mm) / height_pixels
        return distance_mm
    
    def get_environment_info(self) -> Dict:
        """
        Get general information about the environment.
        
        Returns:
            Dictionary with environment information
        """
        frame = self.capture_frame()
        if frame is None:
            return {'error': 'No frame available'}
        
        try:
            import cv2
            
            # Calculate brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray)
            
            # Detect edges (for structure detection)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            return {
                'brightness': float(brightness),
                'edge_density': float(edge_density),
                'frame_count': self.frame_count,
                'detections': len(self.detect_objects(frame))
            }
        except ImportError:
            return {'simulation': True, 'frame_count': self.frame_count}
        except Exception as e:
            logger.error(f"Error getting environment info: {e}")
            return {'error': str(e)}
