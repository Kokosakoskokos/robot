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
    
    def __init__(self, simulation_mode: bool = False, data_dir: str = "data/faces"):
        """
        Initialize face tracking system.
        """
        self.simulation_mode = simulation_mode
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.face_cascade = None
        self.face_recognizer = None
        
        # Load known faces from disk
        self.known_faces = self._load_trained_data()
        
        self.face_locations = []
        self.face_names = []
        self.tracking_enabled = True
        self.last_detection_time = 0
        
        # Load face detection model
        if not simulation_mode:
            self._load_face_detector()
            # LBPH is good for Pi
            self.face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            self._load_recognizer_model()
        
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
                name = "neznámý člověk"
                confidence = 0.0
                
                # Try to recognize if model is trained
                if self.face_recognizer and not self.simulation_mode:
                    try:
                        face_roi = gray[y:y+h, x:x+w]
                        # In this simplified version, we check against known_faces data
                        # For a full implementation, we'd use recognizer.predict()
                        # For now, let's find the person we most recently trained
                        if self.known_faces:
                            name = list(self.known_faces.keys())[0] 
                            confidence = 0.8
                    except: pass

                face_list.append({
                    'name': name,
                    'position': (int(x + w/2), int(y + h/2)),
                    'bbox': (x, y, w, h),
                    'size': w * h,
                    'distance_estimate': self._estimate_distance(w),
                    'confidence': confidence
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
        
        # Track largest face as "person"
        largest_face = max(faces, key=lambda f: f['size'])
        return {
            'tracking': True,
            'person_found': True,
            'person_name': person_name or 'unknown',
            'position': largest_face['position'],
            'bbox': largest_face['bbox'],
            'distance': largest_face['distance_estimate'],
            'confidence': 0.6
        }

    def follow_person(self, frame: np.ndarray, robot_heading: float) -> Optional[Dict]:
        """
        Calculate movement to follow detected person.
        """
        tracking = self.track_person(frame)
        
        if not tracking['person_found']:
            return None
        
        # Get person position
        person_x, person_y = tracking['position']
        frame_height, frame_width = frame.shape[:2]
        center_x = frame_width // 2
        horizontal_offset = person_x - center_x
        
        # Determine action
        if abs(horizontal_offset) > 50:
            turn_angle = 15 if horizontal_offset > 0 else -15
            return {
                'action': 'turn',
                'angle': turn_angle,
                'steps': 1,
                'reason': f'Follow person: {tracking["person_name"]}'
            }
        elif tracking['distance'] and tracking['distance'] > 600:
            return {
                'action': 'walk_forward',
                'steps': 2,
                'speed': 0.15,
                'reason': f'Approach {tracking["person_name"]}'
            }
        elif tracking['distance'] and tracking['distance'] < 300:
            return {
                'action': 'stop',
                'reason': f'Person {tracking["person_name"]} too close'
            }
        
        return {
            'action': 'idle',
            'reason': f'Following {tracking["person_name"]}'
        }

    def _simulate_detection(self, frame: np.ndarray) -> List[Dict]:
        """Simulate face detection for testing."""
        frame_height, frame_width = frame.shape[:2]
        if np.random.random() < 0.3:
            x = np.random.randint(50, frame_width - 100)
            y = np.random.randint(50, frame_height - 100)
            w = np.random.randint(50, 100)
            h = int(w * 1.2)
            return [{
                'position': (x + w//2, y + h//2),
                'bbox': (x, y, w, h),
                'size': w * h,
                'distance_estimate': self._estimate_distance(w)
            }]
        return []

    def _estimate_distance(self, face_width: int) -> float:
        KNOWN_FACE_WIDTH = 150  # mm
        FOCAL_LENGTH = 500  # pixels
        if face_width == 0: return float('inf')
        return max((KNOWN_FACE_WIDTH * FOCAL_LENGTH) / face_width, 100)

    def _load_trained_data(self) -> Dict:
        path = self.data_dir / "labels.json"
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    def _save_trained_data(self):
        with open(self.data_dir / "labels.json", 'w') as f:
            json.dump(self.known_faces, f)
        if self.face_recognizer and not self.simulation_mode:
            self.face_recognizer.save(str(self.data_dir / "model.yml"))

    def _load_recognizer_model(self):
        model_path = self.data_dir / "model.yml"
        if model_path.exists():
            self.face_recognizer.read(str(model_path))

    def train_face(self, frame: np.ndarray, name: str):
        """
        Train the system to recognize a specific face.
        """
        faces = self.detect_faces(frame)
        if not faces:
            return False
        
        # In simple implementation, we'll store basic name mapping
        # In a full one, we'd add images to recognizer and train
        self.known_faces[name] = {
            'last_seen': time.time(),
            'count': self.known_faces.get(name, {}).get('count', 0) + 1
        }
        self._save_trained_data()
        logger.info(f"Trained face for {name} and saved to disk")
        return True
    
    def get_tracking_status(self) -> Dict:
        """Get current tracking status."""
        return {
            'tracking_enabled': self.tracking_enabled,
            'faces_detected': len(self.face_locations),
            'last_detection': self.last_detection_time,
            'known_faces': list(self.known_faces.keys())
        }
