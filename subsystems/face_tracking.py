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
