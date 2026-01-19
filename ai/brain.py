"""AI brain - main decision-making system for Clanker robot."""

import json
import time
from typing import Dict, Optional, List, Any

from dotenv import load_dotenv

from ai.behaviors import BehaviorManager
from ai.self_modify import SelfModifier
from ai.openrouter_client import OpenRouterClient, OpenRouterConfig
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RobotBrain:
    """Main AI brain for autonomous decision-making."""
    
    def __init__(
        self,
        project_root: str = ".",
        self_modify_enabled: bool = True,
        llm_config: Optional[Dict[str, Any]] = None,
        robot_name: str = "Clanker",
        primary_language: str = "cs",
    ):
        """
        Initialize robot brain.
        
        Args:
            project_root: Root directory for self-modification
            self_modify_enabled: Whether to enable self-modification
            llm_config: Optional LLM configuration dict (OpenRouter)
            robot_name: Identity name the robot should use in prompts/state
            primary_language: Language preference for reasoning/speech
        """
        load_dotenv()  # load OPENROUTER_API_KEY, etc.

        self.behavior_manager = BehaviorManager()
        self.self_modifier = SelfModifier(project_root)
        self.robot_name = robot_name
        self.primary_language = primary_language
        
        if not self_modify_enabled:
            self.self_modifier.disable()
        
        self.llm_enabled = False
        self.openrouter: Optional[OpenRouterClient] = None
        self.llm_required = False
        if llm_config:
            try:
                enabled = bool(llm_config.get("enabled", False))
                self.llm_required = bool(llm_config.get("required", False))
                if enabled:
                    cfg = OpenRouterConfig(
                        base_url=str(llm_config.get("base_url", "https://openrouter.ai/api/v1")),
                        model=str(llm_config.get("model", "mistralai/devstral-small:free")),
                        timeout_s=int(llm_config.get("timeout_s", 20)),
                        max_retries=int(llm_config.get("max_retries", 2)),
                        temperature=float(llm_config.get("temperature", 0.2)),
                        site_url=llm_config.get("site_url"),
                        app_name=llm_config.get("app_name"),
                    )
                    self.openrouter = OpenRouterClient(cfg)
                    self.llm_enabled = self.openrouter.is_configured()
                    if enabled and not self.llm_enabled:
                        if self.llm_required:
                            logger.warning("LLM is REQUIRED but OPENROUTER_API_KEY is not set; robot will fail-safe (stop).")
                        else:
                            logger.warning("LLM enabled in config, but OPENROUTER_API_KEY is not set; using fallback behaviors.")
            except Exception as e:
                if self.llm_required:
                    logger.warning(f"Failed to initialize OpenRouter client; robot will fail-safe (stop): {e}")
                else:
                    logger.warning(f"Failed to initialize OpenRouter client; using fallback behaviors: {e}")

        self.decision_interval = 0.5  # seconds
        self.last_decision_time = 0
        self.state_history: List[Dict] = []
        self.performance_metrics: Dict = {
            'decisions_made': 0,
            'behaviors_executed': {},
            'errors': 0
        }
        
        logger.info("Robot brain initialized")
    
    def _llm_system_prompt(self) -> str:
        return (
            f"You are {self.robot_name}, an autonomous hexapod robot controller. "
            f"Primary language: {self.primary_language}. "
            "You can self-modify code when enabled, create new behaviors, and recover from missing capabilities.\n"
            "You must output ONLY a single JSON object describing the next action.\n"
            "Allowed actions and fields:\n"
            "- {\"action\":\"walk_forward\",\"steps\":int,\"speed\":float}\n"
            "- {\"action\":\"turn\",\"angle\":float,\"steps\":int}\n"
            "- {\"action\":\"stand\"}\n"
            "- {\"action\":\"sit\"}\n"
            "- {\"action\":\"wave\",\"leg_id\":int}\n"
            "- {\"action\":\"stop\"}\n"
            "- {\"action\":\"idle\"}\n"
            "Rules:\n"
            "- Always choose a safe action. If uncertain, choose {\"action\":\"stop\"}.\n"
            "- If a capability seems missing (e.g., wave not implemented), propose creating or fixing it via self-modification.\n"
            "- Do not include any extra keys except: action, steps, speed, angle, leg_id, reason.\n"
            "- Never request tools, never output code, never output markdown.\n"
        )

    def _sanitize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Clamp and validate action fields to safe ranges."""
        if not isinstance(action, dict):
            return {"action": "stop", "reason": "invalid_action_type"}

        allowed_actions = {"walk_forward", "turn", "stand", "sit", "wave", "stop", "idle", "continue"}
        a = str(action.get("action", "stop"))
        if a not in allowed_actions:
            return {"action": "stop", "reason": "unknown_action"}

        out: Dict[str, Any] = {"action": a}
        if "reason" in action and isinstance(action["reason"], str):
            out["reason"] = action["reason"][:200]

        if a == "walk_forward":
            steps = int(action.get("steps", 1))
            speed = float(action.get("speed", 0.1))
            out["steps"] = max(1, min(10, steps))
            out["speed"] = max(0.05, min(1.0, speed))
        elif a == "turn":
            angle = float(action.get("angle", 0.0))
            steps = int(action.get("steps", 1))
            out["angle"] = max(-180.0, min(180.0, angle))
            out["steps"] = max(1, min(10, steps))
        elif a == "wave":
            leg_id = int(action.get("leg_id", 0))
            out["leg_id"] = max(0, min(5, leg_id))

        return out

    def _think_with_llm(self, current_state: Dict) -> Optional[Dict[str, Any]]:
        if not self.openrouter:
            return None
        if not self.llm_enabled:
            # Not configured (missing key), but caller decides whether to fallback
            return None

        # Keep prompt small + stable: only the fields the planner needs.
        state_brief = {
            "name": self.robot_name,
            "language": self.primary_language,
            "mode": current_state.get("mode"),
            "obstacles": current_state.get("obstacles", [])[:3],
            "navigation_info": current_state.get("navigation_info"),
            "navigation_target": current_state.get("navigation_target"),
            "heading": current_state.get("heading"),
            "environment": current_state.get("environment"),
        }

        messages = [
            {"role": "system", "content": self._llm_system_prompt()},
            {"role": "user", "content": json.dumps(state_brief)},
        ]

        try:
            content = self.openrouter.chat(messages)
            parsed = json.loads(content.strip())
            action = self._sanitize_action(parsed)
            action["behavior"] = "llm"
            return action
        except Exception as e:
            logger.warning(f"LLM decision failed; falling back to behaviors: {e}")
            return None

    def think(self, current_state: Dict) -> Dict:
        """
        Main thinking/decision-making process.
        
        Args:
            current_state: Current state of the robot
            
        Returns:
            Action commands
        """
        current_time = time.time()
        
        # Rate limit decisions
        if current_time - self.last_decision_time < self.decision_interval:
            return {'action': 'continue'}
        
        self.last_decision_time = current_time
        self.performance_metrics['decisions_made'] += 1
        
        # Store state history
        state_copy = current_state.copy()
        state_copy['timestamp'] = current_time
        self.state_history.append(state_copy)
        
        # Keep only recent history
        if len(self.state_history) > 1000:
            self.state_history = self.state_history[-1000:]
        
        try:
            # Prefer LLM planner when configured.
            llm_action = self._think_with_llm(current_state)
            if llm_action is not None:
                self.performance_metrics['behaviors_executed'].setdefault("llm", 0)
                self.performance_metrics['behaviors_executed']["llm"] += 1
                return llm_action

            # API-required mode: do NOT fallback to local behaviors.
            if self.llm_required:
                return {"action": "stop", "behavior": "llm", "reason": "llm_unavailable_or_failed"}

            # Select and execute behavior
            action = self.behavior_manager.execute_behavior(current_state)
            
            # Track behavior usage
            current_behavior = self.behavior_manager.current_behavior
            behavior_name = current_behavior.name if current_behavior else 'unknown'
            action['behavior'] = behavior_name
            if behavior_name not in self.performance_metrics['behaviors_executed']:
                self.performance_metrics['behaviors_executed'][behavior_name] = 0
            self.performance_metrics['behaviors_executed'][behavior_name] += 1
            
            return self._sanitize_action(action)
            
        except Exception as e:
            logger.error(f"Error in brain.think(): {e}")
            self.performance_metrics['errors'] += 1
            return {'action': 'stop', 'error': str(e)}
    
    def learn(self):
        """Learning process - analyze performance and optimize."""
        logger.info("Learning from experience...")
        
        # Analyze behavior performance
        behavior_stats = self.behavior_manager.get_behavior_stats()
        
        # Find underperforming behaviors
        for behavior_name, stats in behavior_stats.items():
            success_rate = stats['success_rate']
            if success_rate < 0.3 and stats['success_count'] + stats['failure_count'] > 10:
                logger.warning(f"Behavior {behavior_name} has low success rate: {success_rate:.2%}")
        
        # Self-modification: analyze code and find optimizations
        if self.self_modifier.enabled:
            try:
                opportunities = self.self_modifier.find_optimization_opportunities()
                if opportunities:
                    logger.info(f"Found {len(opportunities)} optimization opportunities")
                    # Could automatically apply optimizations here
            except Exception as e:
                logger.error(f"Error in learning/self-modification: {e}")
    
    def self_analyze(self) -> Dict:
        """Perform self-analysis of codebase."""
        if not self.self_modifier.enabled:
            return {'error': 'Self-modification disabled'}
        
        try:
            analysis = self.self_modifier.analyze_self()
            return analysis
        except Exception as e:
            logger.error(f"Error in self-analysis: {e}")
            return {'error': str(e)}
    
    def create_new_behavior(self, behavior_name: str, behavior_code: str) -> bool:
        """
        Create a new behavior dynamically.
        
        Args:
            behavior_name: Name of the behavior
            behavior_code: Python code for the behavior class
            
        Returns:
            True if successful
        """
        if not self.self_modifier.enabled:
            logger.warning("Cannot create behavior: self-modification disabled")
            return False
        
        # Template for behavior class
        template = f'''"""Auto-generated behavior: {behavior_name}"""

from ai.behaviors import Behavior

class {behavior_name}Behavior(Behavior):
    """{behavior_name} behavior."""
    
    def __init__(self):
        super().__init__("{behavior_name.lower()}", priority=5)
    
    def should_activate(self, state):
        """Check if this behavior should be activated."""
        {behavior_code}
    
    def execute(self, state):
        """Execute the behavior."""
        return {{'action': 'idle'}}
'''
        
        return self.self_modifier.create_behavior_file(behavior_name, template)
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics."""
        return {
            **self.performance_metrics,
            'behavior_stats': self.behavior_manager.get_behavior_stats(),
            'state_history_length': len(self.state_history)
        }
    
    def get_recent_states(self, count: int = 10) -> List[Dict]:
        """Get recent state history."""
        return self.state_history[-count:] if self.state_history else []
