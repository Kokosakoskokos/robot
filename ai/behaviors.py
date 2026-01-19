"""Behavior system for autonomous robot actions."""

import time
from typing import Dict, List, Callable, Optional
from abc import ABC, abstractmethod
from utils.logger import setup_logger

logger = setup_logger(__name__)


class Behavior(ABC):
    """Base class for robot behaviors."""
    
    def __init__(self, name: str, priority: int = 5):
        """
        Initialize behavior.
        
        Args:
            name: Behavior name
            priority: Priority level (1-10, higher = more important)
        """
        self.name = name
        self.priority = priority
        self.active = False
        self.success_count = 0
        self.failure_count = 0
    
    @abstractmethod
    def should_activate(self, state: Dict) -> bool:
        """Check if this behavior should be activated."""
        pass
    
    @abstractmethod
    def execute(self, state: Dict) -> Dict:
        """
        Execute the behavior.
        
        Args:
            state: Current robot state
            
        Returns:
            Updated state or action commands
        """
        pass
    
    def get_success_rate(self) -> float:
        """Get success rate of this behavior."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Default
        return self.success_count / total


class ExploreBehavior(Behavior):
    """Behavior for exploring the environment."""
    
    def __init__(self):
        super().__init__("explore", priority=3)
        self.exploration_target = None
    
    def should_activate(self, state: Dict) -> bool:
        """Activate if no specific task is active."""
        return state.get('current_task') is None
    
    def execute(self, state: Dict) -> Dict:
        """Execute exploration behavior."""
        logger.info("Exploring environment...")
        
        # Simple exploration: walk forward, check for obstacles
        obstacles = state.get('obstacles', [])
        
        if obstacles:
            # Turn to avoid obstacle
            return {'action': 'turn', 'angle': 45, 'steps': 2}
        else:
            # Walk forward
            return {'action': 'walk_forward', 'steps': 1}


class AvoidObstacleBehavior(Behavior):
    """Behavior for avoiding obstacles."""
    
    def __init__(self):
        super().__init__("avoid_obstacle", priority=9)
    
    def should_activate(self, state: Dict) -> bool:
        """Activate if obstacles are detected nearby."""
        obstacles = state.get('obstacles', [])
        if not obstacles:
            return False
        
        # Check if any obstacle is close
        for obstacle in obstacles:
            distance = obstacle.get('distance_estimate', float('inf'))
            if distance < 500:  # 50cm threshold
                return True
        
        return False
    
    def execute(self, state: Dict) -> Dict:
        """Execute obstacle avoidance."""
        logger.info("Avoiding obstacle...")
        obstacles = state.get('obstacles', [])
        
        if obstacles:
            # Find obstacle position
            obstacle = obstacles[0]
            center_x = obstacle['position'][0]
            frame_width = state.get('frame_width', 640)
            
            # Turn away from obstacle
            if center_x < frame_width / 2:
                # Obstacle on left, turn right
                return {'action': 'turn', 'angle': -45, 'steps': 2}
            else:
                # Obstacle on right, turn left
                return {'action': 'turn', 'angle': 45, 'steps': 2}
        
        return {'action': 'stop'}


class NavigateToTargetBehavior(Behavior):
    """Behavior for navigating to a GPS target."""
    
    def __init__(self):
        super().__init__("navigate_to_target", priority=7)
    
    def should_activate(self, state: Dict) -> bool:
        """Activate if there's a navigation target."""
        return state.get('navigation_target') is not None
    
    def execute(self, state: Dict) -> Dict:
        """Execute navigation behavior."""
        nav_info = state.get('navigation_info')
        if not nav_info:
            return {'action': 'stop'}
        
        bearing = nav_info.get('bearing')
        distance = nav_info.get('distance')
        
        if distance is None or distance < 5.0:
            logger.info("Reached target!")
            return {'action': 'stop', 'reached_target': True}
        
        # Turn towards target
        current_heading = state.get('heading', 0)
        turn_angle = bearing - current_heading
        
        # Normalize angle
        while turn_angle > 180:
            turn_angle -= 360
        while turn_angle < -180:
            turn_angle += 360
        
        if abs(turn_angle) > 10:
            return {'action': 'turn', 'angle': turn_angle, 'steps': 1}
        else:
            return {'action': 'walk_forward', 'steps': 1}


class BehaviorManager:
    """Manages and executes robot behaviors."""
    
    def __init__(self):
        self.behaviors: List[Behavior] = []
        self.current_behavior: Optional[Behavior] = None
        
        # Register default behaviors
        self.register_behavior(AvoidObstacleBehavior())
        self.register_behavior(NavigateToTargetBehavior())
        self.register_behavior(ExploreBehavior())
        
        logger.info(f"Behavior manager initialized with {len(self.behaviors)} behaviors")
    
    def register_behavior(self, behavior: Behavior):
        """Register a new behavior."""
        self.behaviors.append(behavior)
        logger.info(f"Registered behavior: {behavior.name}")
    
    def select_behavior(self, state: Dict) -> Optional[Behavior]:
        """
        Select the most appropriate behavior based on current state.
        
        Args:
            state: Current robot state
            
        Returns:
            Selected behavior or None
        """
        # Sort behaviors by priority (highest first)
        candidates = [b for b in self.behaviors if b.should_activate(state)]
        candidates.sort(key=lambda x: x.priority, reverse=True)
        
        if candidates:
            return candidates[0]
        return None
    
    def execute_behavior(self, state: Dict) -> Dict:
        """
        Execute the current or selected behavior.
        
        Args:
            state: Current robot state
            
        Returns:
            Action commands
        """
        # Select behavior if none active
        if self.current_behavior is None or not self.current_behavior.should_activate(state):
            self.current_behavior = self.select_behavior(state)
        
        if self.current_behavior is None:
            return {'action': 'idle'}
        
        try:
            result = self.current_behavior.execute(state)
            self.current_behavior.success_count += 1
            return result
        except Exception as e:
            logger.error(f"Error executing behavior {self.current_behavior.name}: {e}")
            self.current_behavior.failure_count += 1
            self.current_behavior = None
            return {'action': 'stop'}
    
    def get_behavior_stats(self) -> Dict:
        """Get statistics about all behaviors."""
        stats = {}
        for behavior in self.behaviors:
            stats[behavior.name] = {
                'priority': behavior.priority,
                'success_rate': behavior.get_success_rate(),
                'success_count': behavior.success_count,
                'failure_count': behavior.failure_count,
                'active': behavior == self.current_behavior
            }
        return stats
