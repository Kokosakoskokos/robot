"""Face Recognition and Person Tracking System for Clanker Robot."""

import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
import time
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)


class FaceTracker:
    """Face recognition and person tracking system."""
    
    def __init__(self, simulation_mode: bool = False):
        """
        Initialize face tracking system.
        
        Args:
            simulation_mode: If True, simulate face detection
        """
        self.simulation_mode = simulation_mode
        self.face_cascade = None
        self.known_faces = {}
        self.face_locations = []
        self.face_names = []
        self.tracking_enabled = True
        self.last_detection_time = 0
        
        # Load face detection model
        if not simulation_mode:
            self._load_face_detector()
        
        logger.info("Face tracking system initialized")
    
    def _load_face_detector(self):
        """Load face detection cascade classifier."""
        try:
            # Use OpenCV's Haar cascade for face detection
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if Path(cascade_path).exists():
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                logger.info("Face cascade loaded successfully")
            else:
                logger.warning("Face cascade not found, using simulation mode")
                self.simulation_mode = True
        except Exception as e:
            logger.warning(f"Failed to load face detector: {e}")
            self.simulation_mode = True
    
    def detect_faces(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect faces in frame.
        
        Args:
            frame: Image frame from camera
            
        Returns:
            List of face dictionaries with position and size
        """
        if self.simulation_mode:
            return self._simulate_detection(frame)
        
        if self.face_cascade is None:
            return []
        
        try:
            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            # Convert to list of dictionaries
            face_list = []
            for (x, y, w, h) in faces:
                face_list.append({
                    'position': (int(x + w/2), int(y + h/2)),  # Center point
                    'bbox': (x, y, w, h),
                    'size': w * h,
                    'distance_estimate': self._estimate_distance(w)
                })
            
            self.face_locations = face_list
            self.last_detection_time = time.time()
            
            return face_list
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def track_person(self, frame: np.ndarray, person_name: Optional[str] = None) -> Dict:
        """
        Track specific person by name or detect any person.
        
        Args:
            frame: Image frame from camera
            person_name: Name of person to track (None = track any person)
            
        Returns:
            Tracking information
        """
        faces = self.detect_faces(frame)
        
        if not faces:
            return {
                'tracking': False,
                'person_found': False,
                'position': None,
                'bbox': None,
                'confidence': 0.0
            }
        
        # If tracking specific person
        if person_name:
            # In full implementation, would use face recognition
            # For now, track largest face as "person"
            largest_face = max(faces, key=lambda f: f['size'])
            return {
                'tracking': True,
                'person_found': True,
                'person_name': person_name,
                'position': largest_face['position'],
                'bbox': largest_face['bbox'],
                'distance': largest_face['distance_estimate'],
                'confidence': 0.7  # Would be actual recognition confidence
            }
        else:
            # Track any person (largest face)
            largest_face = max(faces, key=lambda f: f['size'])
            return {
                'tracking': True,
                'person_found': True,
                'person_name': 'unknown',
                'position': largest_face['position'],
                'bbox': largest_face['bbox'],
                'distance': largest_face['distance_estimate'],
                'confidence': 0.6
            }
    
    def follow_person(self, frame: np.ndarray, robot_heading: float) -> Optional[Dict]:
        """
        Calculate movement to follow detected person.
        
        Args:
            frame: Image frame from camera
            robot_heading: Current robot heading in degrees
            
        Returns:
            Action command to follow person, or None
        """
        tracking = self.track_person(frame)
        
        if not tracking['person_found']:
            return None
        
        # Get person position
        person_x, person_y = tracking['position']
        
        # Get frame dimensions
        frame_height, frame_width = frame.shape[:2]
        
        # Calculate if person is centered
        center_x = frame_width // 2
        center_y = frame_height // 2
        
        # Horizontal offset (left/right)
        horizontal_offset = person_x - center_x
        
        # Vertical offset (up/down)
        vertical_offset = person_y - center_y
        
        # Determine action
        if abs(horizontal_offset) > 50:
            # Person is off-center horizontally
            turn_angle = 15 if horizontal_offset > 0 else -15
            return {
                'action': 'turn',
                'angle': turn_angle,
                'steps': 1,
                'reason': f'Follow person: {tracking["person_name"]}'
            }
        elif tracking['distance'] and tracking['distance'] > 600:
            # Person is far away
            return {
                'action': 'walk_forward',
                'steps': 2,
                'speed': 0.15,
                'reason': f'Approach {tracking["person_name"]}'
            }
        elif tracking['distance'] and tracking['distance'] < 300:
            # Person is too close
            return {
                'action': 'stop',
                'reason': f'Person {tracking["person_name"]} too close'
            }
        
        # Person is centered, maintain position
        return {
            'action': 'idle',
            'reason': f'Following {tracking["person_name"]}'
        }
    
    def _simulate_detection(self, frame: np.ndarray) -> List[Dict]:
        """Simulate face detection for testing."""
        frame_height, frame_width = frame.shape[:2]
        
        # Simulate occasional face detection
        if np.random.random() < 0.3:  # 30% chance of detection
            # Random position in frame
            x = np.random.randint(50, frame_width - 100)
            y = np.random.randint(50, frame_height - 100)
            w = np.random.randint(50, 100)
            h = int(w * 1.2)  # Face aspect ratio
            
            return [{
                'position': (x + w//2, y + h//2),
                'bbox': (x, y, w, h),
                'size': w * h,
                'distance_estimate': self._estimate_distance(w)
            }]
        
        return []
    
    def _estimate_distance(self, face_width: int) -> float:
        """
        Estimate distance to face based on width.
        
        Args:
            face_width: Width of face in pixels
            
        Returns:
            Estimated distance in mm
        """
        # Simplified estimation: assume 150mm face width
        # Using inverse relationship: distance = (known_width * focal_length) / width
        # Using calibrated values for typical camera
        KNOWN_FACE_WIDTH = 150  # mm (average adult face)
        FOCAL_LENGTH = 500  # pixels (estimated for typical camera)
        
        if face_width == 0:
            return float('inf')
        
        distance = (KNOWN_FACE_WIDTH * FOCAL_LENGTH) / face_width
        return max(distance, 100)  # Minimum distance 100mm
    
    def train_face(self, frame: np.ndarray, name: str):
        """
        Train the system to recognize a specific face.
        
        Args:
            frame: Image containing the face
            name: Name of the person
        """
        faces = self.detect_faces(frame)
        
        if not faces:
            logger.warning(f"No face detected in frame for {name}")
            return False
        
        # Store face data (in full implementation, would extract embeddings)
        self.known_faces[name] = {
            'last_seen': time.time(),
            'count': self.known_faces.get(name, {}).get('count', 0) + 1
        }
        
        logger.info(f"Trained face for {name}")
        return True
    
    def get_tracking_status(self) -> Dict:
        """Get current tracking status."""
        return {
            'tracking_enabled': self.tracking_enabled,
            'faces_detected': len(self.face_locations),
            'last_detection': self.last_detection_time,
            'known_faces': list(self.known_faces.keys())
        }
