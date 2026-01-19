"""Main robot controller - orchestrates all subsystems."""

import time
import yaml
from pathlib import Path
from typing import Dict, Optional
from core.hardware import ServoController, CameraInterface, GPSInterface, DisplayInterface
from subsystems.servos import HexapodController
from subsystems.vision import VisionSystem
from subsystems.navigation import NavigationSystem
from subsystems.display import DisplayManager
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
        
        # Initialize hardware interfaces
        self.servo_controller = ServoController(
            simulation_mode=is_simulation,
            pca9685_address=self.config['servos']['pca9685_address']
        )
        
        self.camera = CameraInterface(
            simulation_mode=is_simulation,
            device_id=self.config['camera']['device_id'],
            width=self.config['camera']['width'],
            height=self.config['camera']['height']
        )
        
        self.gps = GPSInterface(
            simulation_mode=is_simulation,
            port=self.config['gps']['port'],
            baudrate=self.config['gps']['baudrate']
        )
        
        self.display = DisplayInterface(
            simulation_mode=is_simulation,
            width=self.config['display']['width'],
            height=self.config['display']['height'],
            i2c_address=self.config['display']['i2c_address']
        )

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
        """Update robot state from all subsystems."""
        # Vision
        frame = self.vision.capture_frame()
        obstacles = self.vision.detect_obstacles(frame)
        detections = self.vision.detect_objects(frame)
        env_info = self.vision.get_environment_info()
        
        # Navigation
        position = self.navigation.get_current_position()
        nav_info = self.navigation.get_direction_to_target()
        
        # Update state
        self.current_state = {
            'mode': self.config['mode'],
            'obstacles': obstacles,
            'detections': detections,
            'environment': env_info,
            'position': position,
            'navigation_info': nav_info,
            'navigation_target': self.navigation.target_position,
            'heading': self.heading,
            'frame_width': self.config['camera']['width'],
            'frame_height': self.config['camera']['height'],
            'current_task': None  # Could be set by behaviors
        }
    
    def execute_action(self, action: Dict):
        """Execute an action command from the AI brain."""
        action_type = action.get('action', 'idle')
        
        try:
            if action_type == 'walk_forward':
                steps = action.get('steps', 1)
                speed = action.get('speed', 0.1)
                self.hexapod.walk_forward(steps=steps, speed=speed)
                
            elif action_type == 'turn':
                angle = action.get('angle', 0)
                steps = action.get('steps', 1)
                self.heading = (self.heading + angle) % 360
                self.hexapod.turn(angle=angle, steps=steps)
                
            elif action_type == 'stand':
                self.hexapod.stand()
                
            elif action_type == 'sit':
                self.hexapod.sit()
                
            elif action_type == 'wave':
                leg_id = action.get('leg_id', 0)
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
            logger.error(f"Error executing action {action_type}: {e}")
    
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
        """Start the robot's main loop."""
        logger.info("Starting Clanker robot...")
        self.running = True
        
        # Stand up
        self.hexapod.stand()
        time.sleep(1)
        
        # Main loop
        try:
            while self.running:
                self.run_cycle()
                time.sleep(self.config['ai']['decision_interval'])
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
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
