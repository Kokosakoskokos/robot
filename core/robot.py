"""Main robot controller - orchestrates all subsystems."""

import time
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from core.hardware import ServoController, CameraInterface, GPSInterface, DisplayInterface
from subsystems.servos import HexapodController
from subsystems.vision import VisionSystem
from subsystems.navigation import NavigationSystem
from subsystems.display import DisplayManager
from subsystems.face_tracking import FaceTracker
from ai.brain import RobotBrain
from utils.logger import setup_logger
from utils.tts import TextToSpeech

logger = setup_logger(__name__)


class ClankerRobot:
    """Main robot controller for Clanker hexapod system."""
    
    def __init__(self, config_path: str = "config/config.yaml", simulation_mode: bool = False):
        """
        Initialize Clanker robot.
        
        Args:
            config_path: Path to configuration file
            simulation_mode: Force simulation mode
        """
        # Load configuration
        self.config = self._load_config(config_path)
        self.name = self.config.get("identity", {}).get("name", "Clanker")
        self.primary_language = self.config.get("identity", {}).get("language", "cs")
        
        # Override mode if specified
        if simulation_mode:
            self.config['mode'] = 'simulation'
        
        is_simulation = self.config['mode'] == 'simulation'
        
        logger.info(f"Initializing Clanker robot (mode: {self.config['mode']})")
        
        # Initialize hardware interfaces with error handling
        try:
            self.servo_controller = ServoController(
                simulation_mode=is_simulation,
                pca9685_address=self.config['servos']['pca9685_address']
            )
        except Exception as e:
            logger.error(f"Failed to initialize servo controller: {e}")
            logger.warning("Reverting to simulation mode for servos")
            self.servo_controller = ServoController(simulation_mode=True)
        
        try:
            self.camera = CameraInterface(
                simulation_mode=is_simulation,
                device_id=self.config['camera']['device_id'],
                width=self.config['camera']['width'],
                height=self.config['camera']['height']
            )
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            logger.warning("Reverting to simulation mode for camera")
            self.camera = CameraInterface(simulation_mode=True)
        
        try:
            self.gps = GPSInterface(
                simulation_mode=is_simulation,
                port=self.config['gps']['port'],
                baudrate=self.config['gps']['baudrate']
            )
        except Exception as e:
            logger.error(f"Failed to initialize GPS: {e}")
            logger.warning("Reverting to simulation mode for GPS")
            self.gps = GPSInterface(simulation_mode=True)
        
        try:
            self.display = DisplayInterface(
                simulation_mode=is_simulation,
                width=self.config['display']['width'],
                height=self.config['display']['height'],
                i2c_address=self.config['display']['i2c_address']
            )
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
            logger.warning("Reverting to simulation mode for display")
            self.display = DisplayInterface(simulation_mode=True)

        # TTS (Czech by default, can run headless; optional if engines missing)
        tts_cfg = self.config.get("tts", {}) if isinstance(self.config, dict) else {}
        self.tts = TextToSpeech(
            language=tts_cfg.get("language", "cs"),
            engine_priority=tts_cfg.get("engine_priority", ["pyttsx3", "gtts"]),
            voice_substring=tts_cfg.get("voice_substring", "cs"),
            playback_timeout_s=int(tts_cfg.get("playback_timeout_s", 15)),
        )
        
        # Initialize subsystems
        self.hexapod = HexapodController(
            self.servo_controller,
            coxa_length=self.config['servos']['coxa_length'],
            femur_length=self.config['servos']['femur_length'],
            tibia_length=self.config['servos']['tibia_length']
        )
        
        self.vision = VisionSystem(self.camera)
        self.navigation = NavigationSystem(self.gps)
        self.display_manager = DisplayManager(self.display)
        self.face_tracker = FaceTracker(simulation_mode=is_simulation)
        
        # Initialize AI brain
        self.brain = RobotBrain(
            project_root=".",
            self_modify_enabled=self.config['ai']['self_modify_enabled'],
            llm_config=self.config.get("ai", {}).get("llm", {}),
            robot_name=self.name,
            primary_language=self.primary_language,
        )
        
        # Robot state
        self.running = False
        self.current_state: Dict = {}
        self.heading = 0.0  # Current heading in degrees
        
        logger.info("Clanker robot initialized successfully")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return self._default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """Return default configuration."""
        return {
            'mode': 'simulation',
            'servos': {
                'pca9685_address': 0x40,
                'coxa_length': 30,
                'femur_length': 60,
                'tibia_length': 80
            },
            'camera': {
                'device_id': 0,
                'width': 640,
                'height': 480
            },
            'gps': {
                'port': '/dev/ttyUSB0',
                'baudrate': 9600
            },
            'display': {
                'width': 128,
                'height': 64,
                'i2c_address': 0x3C
            },
            'ai': {
                'self_modify_enabled': True,
                'decision_interval': 0.5
            }
        }
    
    def update_state(self):
        """Update robot state from all subsystems with error handling."""
        try:
            # Vision
            frame = self.vision.capture_frame()
            obstacles = self.vision.detect_obstacles(frame) if frame is not None else []
            detections = self.vision.detect_objects(frame) if frame is not None else []
            env_info = self.vision.get_environment_info()
            
            # Face tracking
            face_info = {}
            if frame is not None:
                faces = self.face_tracker.detect_faces(frame)
                if faces:
                    face_info = {
                        'faces_detected': len(faces),
                        'largest_face': max(faces, key=lambda f: f['size']),
                        'face_positions': [f['position'] for f in faces]
                    }
            
            # Navigation
            position = self.navigation.get_current_position()
            nav_info = self.navigation.get_direction_to_target()
            
            # Update state
            self.current_state = {
                'mode': self.config['mode'],
                'obstacles': obstacles,
                'detections': detections,
                'environment': env_info,
                'face_tracking': face_info,
                'position': position,
                'navigation_info': nav_info,
                'navigation_target': self.navigation.target_position,
                'heading': self.heading,
                'frame_width': self.config['camera']['width'],
                'frame_height': self.config['camera']['height'],
                'current_task': None  # Could be set by behaviors
            }
        except Exception as e:
            logger.error(f"Error updating robot state: {e}")
            # Maintain minimal state for recovery
            self.current_state = {
                'mode': self.config['mode'],
                'obstacles': [],
                'detections': [],
                'environment': {'error': str(e)},
                'position': None,
                'navigation_info': None,
                'navigation_target': None,
                'heading': self.heading,
                'frame_width': self.config['camera']['width'],
                'frame_height': self.config['camera']['height'],
                'current_task': None
            }
    
    def execute_action(self, action: Dict):
        """Execute an action command from the AI brain with safety checks."""
        action_type = action.get('action', 'idle')
        
        try:
            # Validate action before execution
            if not isinstance(action, dict):
                logger.error(f"Invalid action type: {type(action)}")
                return
            
            # Safety check: prevent dangerous actions in critical situations
            if self.current_state.get('obstacles', []):
                # If obstacles detected, limit risky actions
                if action_type in ['walk_forward', 'turn']:
                    logger.warning("Obstacles detected, limiting movement action")
                    if action_type == 'walk_forward':
                        action['steps'] = min(action.get('steps', 1), 1)
                    elif action_type == 'turn':
                        action['angle'] = min(abs(action.get('angle', 0)), 30)
            
            if action_type == 'walk_forward':
                steps = action.get('steps', 1)
                speed = action.get('speed', 0.1)
                
                # Sanity checks
                if not isinstance(steps, (int, float)) or steps < 1:
                    logger.warning(f"Invalid steps value: {steps}, using default 1")
                    steps = 1
                if not isinstance(speed, (int, float)) or speed < 0.05:
                    logger.warning(f"Invalid speed value: {speed}, using default 0.1")
                    speed = 0.1
                
                # Clamp values
                steps = max(1, min(10, int(steps)))
                speed = max(0.05, min(1.0, float(speed)))
                
                self.hexapod.walk_forward(steps=steps, speed=speed)
                
            elif action_type == 'turn':
                angle = action.get('angle', 0)
                steps = action.get('steps', 1)
                
                # Sanity checks
                if not isinstance(angle, (int, float)):
                    logger.warning(f"Invalid angle value: {angle}, using default 0")
                    angle = 0
                if not isinstance(steps, (int, float)) or steps < 1:
                    logger.warning(f"Invalid steps value: {steps}, using default 1")
                    steps = 1
                
                # Clamp values
                angle = max(-180, min(180, float(angle)))
                steps = max(1, min(10, int(steps)))
                
                self.heading = (self.heading + angle) % 360
                self.hexapod.turn(angle=angle, steps=steps)
                
            elif action_type == 'stand':
                self.hexapod.stand()
                
            elif action_type == 'sit':
                self.hexapod.sit()
                
            elif action_type == 'wave':
                leg_id = action.get('leg_id', 0)
                
                # Sanity checks
                if not isinstance(leg_id, (int, float)):
                    logger.warning(f"Invalid leg_id value: {leg_id}, using default 0")
                    leg_id = 0
                
                # Clamp value
                leg_id = max(0, min(5, int(leg_id)))
                
                self.hexapod.wave_leg(leg_id)
                
            elif action_type == 'stop':
                # Stop movement (legs stay in current position)
                logger.info("Stopping movement")
                
            elif action_type == 'idle':
                # Do nothing
                pass
                
            elif action_type == 'continue':
                # Continue current action
                pass
                
            else:
                logger.warning(f"Unknown action: {action_type}")
                
        except Exception as e:
            logger.error(f"Error executing action {action_type}: {e}", exc_info=True)
            # Attempt to recover by stopping
            try:
                logger.info("Attempting recovery - stopping movement")
                self.hexapod.sit()
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
    
    def update_display(self):
        """Update OLED display with current status."""
        status = {
            'mode': self.config['mode'],
            'position': self.current_state.get('position'),
            'activity': self.brain.behavior_manager.current_behavior.name if self.brain.behavior_manager.current_behavior else 'idle'
        }
        self.display_manager.show_status(status)
    
    def run_cycle(self):
        """Run one cycle of the robot's main loop."""
        # Update state
        self.update_state()
        
        # AI decision-making
        action = self.brain.think(self.current_state)
        
        # Execute action
        self.execute_action(action)
        
        # Update display
        self.update_display()
        
        # Periodic learning
        if self.brain.performance_metrics['decisions_made'] % 100 == 0:
            self.brain.learn()
    
    def start(self):
        """Start the robot's main loop with comprehensive error handling."""
        logger.info("Starting Clanker robot...")
        self.running = True
        
        # Stand up with error handling
        try:
            self.hexapod.stand()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Failed to stand up: {e}")
            logger.warning("Attempting to continue anyway...")
        
        # Main loop with watchdog
        last_cycle_time = time.time()
        watchdog_timeout = 5.0  # seconds
        
        try:
            while self.running:
                cycle_start = time.time()
                
                # Watchdog check
                if cycle_start - last_cycle_time > watchdog_timeout:
                    logger.warning(f"Watchdog timeout - cycle took too long ({cycle_start - last_cycle_time:.2f}s)")
                    last_cycle_time = cycle_start
                
                try:
                    self.run_cycle()
                    last_cycle_time = time.time()
                except KeyboardInterrupt:
                    raise  # Re-raise to be caught by outer handler
                except Exception as cycle_error:
                    logger.error(f"Error in cycle: {cycle_error}", exc_info=True)
                    # Brief pause before attempting recovery
                    time.sleep(0.5)
                    # Try to reset to safe state
                    try:
                        self.hexapod.sit()
                    except Exception as recovery_error:
                        logger.error(f"Cycle recovery failed: {recovery_error}")
                
                # Rate limiting
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.config['ai']['decision_interval'] - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.critical(f"Fatal error in main loop: {e}", exc_info=True)
            # Attempt emergency shutdown
            try:
                self.hexapod.sit()
                self.camera.release()
            except Exception as emergency_error:
                logger.error(f"Emergency shutdown failed: {emergency_error}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown the robot safely."""
        logger.info("Shutting down Clanker robot...")
        self.running = False
        
        # Sit down
        self.hexapod.sit()
        time.sleep(0.5)
        
        # Release resources
        self.camera.release()
        self.display_manager.clear()
        
        logger.info("Shutdown complete")
    
    def set_navigation_target(self, latitude: float, longitude: float):
        """Set a navigation target."""
        self.navigation.set_target(latitude, longitude)
        logger.info(f"Navigation target set: ({latitude}, {longitude})")
    
    def get_status(self) -> Dict:
        """Get current robot status."""
        return {
            'running': self.running,
            'mode': self.config['mode'],
            'state': self.current_state,
            'performance': self.brain.get_performance_metrics()
        }
