"""AI brain - main decision-making system for Clanker robot."""

import json
import time
import os
from pathlib import Path
from typing import Dict, Optional, List, Any

from dotenv import load_dotenv

from ai.behaviors import BehaviorManager
from ai.self_modify import SelfModifier
from ai.openrouter_client import OpenRouterClient, OpenRouterConfig
from utils.memory import LongTermMemory
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
        """
        # Load .env file explicitly from project root
        dotenv_path = Path(project_root) / ".env"
        load_dotenv(dotenv_path=dotenv_path)
        
        # DEBUG: Check if key is loaded (only show first few chars)
        test_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("EDENAI_API_KEY")
        if test_key:
            logger.info(f"API Key successfully detected (starts with {test_key[:8]}...)")
        else:
            logger.warning("NO API KEY DETECTED in environment or .env file!")

        self.behavior_manager = BehaviorManager()
        self.self_modifier = SelfModifier(project_root)
        self.memory = LongTermMemory()
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
                provider = str(llm_config.get("provider", "openrouter"))
                
                if enabled:
                    # Select specific config and API KEY based on provider
                    provider_cfg = llm_config.get(provider, {})
                    
                    # Force correct API key based on provider choice
                    api_key = None
                    if provider == "edenai":
                        api_key = os.getenv("EDENAI_API_KEY")
                    elif provider == "openrouter":
                        api_key = os.getenv("OPENROUTER_API_KEY")
                    
                    # Fallback to any available key if specific one is missing
                    if not api_key:
                        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("EDENAI_API_KEY")

                    cfg = OpenRouterConfig(
                        base_url=str(provider_cfg.get("base_url", "https://openrouter.ai/api/v1")),
                        model=str(provider_cfg.get("model", "google/gemini-2.0-flash-exp:free")),
                        fallback_models=provider_cfg.get("fallback_models", []),
                        timeout_s=int(llm_config.get("timeout_s", 30)),
                        max_retries=int(llm_config.get("max_retries", 3)),
                        temperature=float(llm_config.get("temperature", 0.2)),
                        site_url=llm_config.get("site_url"),
                        app_name=llm_config.get("app_name"),
                    )
                    self.openrouter = OpenRouterClient(cfg, api_key=api_key)
                    self.llm_enabled = self.openrouter.is_configured()
                    if enabled and not self.llm_enabled:
                        if self.llm_required:
                            logger.warning(f"LLM ({provider}) is REQUIRED but API KEY is not set; robot will fail-safe (stop).")
                        else:
                            logger.warning(f"LLM ({provider}) enabled in config, but API KEY is not set; using fallback behaviors.")
            except Exception as e:
                if self.llm_required:
                    logger.warning(f"Failed to initialize LLM client; robot will fail-safe (stop): {e}")
                else:
                    logger.warning(f"Failed to initialize LLM client; using fallback behaviors: {e}")

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
            "You are a friendly, helpful, and intelligent companion.\n"
            "You have LONG-TERM MEMORY and can remember previous conversations and people you've met.\n"
            "If you see a person (face_tracking or bodies) and they haven't been greeted recently, greet them by name if known.\n"
            "If the state includes 'voice_command', prioritize answering that specific question or command. Do NOT give a generic greeting if the user asked something else.\n"
            "Be conversational, vary your responses, and show your personality as Clanker.\n"
            "Include a 'speech' field with a short, natural response in the primary language describing what you are doing or replying to the user.\n"
            "You must output ONLY a single JSON object describing the next action.\n"
            "Allowed actions and fields:\n"
            "- {\"action\":\"walk_forward\",\"steps\":int,\"speed\":float}\n"
            "- {\"action\":\"turn\",\"angle\":float,\"steps\":int}\n"
            "- {\"action\":\"crab_walk\",\"direction\":\"left\"|\"right\",\"steps\":int}\n"
            "- {\"action\":\"fist_bump\"}\n"
            "- {\"action\":\"dance\"}\n"
            "- {\"action\":\"follow_person\"}\n"
            "- {\"action\":\"stand\"}\n"
            "- {\"action\":\"sit\"}\n"
            "- {\"action\":\"wave\",\"leg_id\":int}\n"
            "- {\"action\":\"create_behavior\",\"behavior_name\":string,\"code\":string}\n"
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

        allowed_actions = {"walk_forward", "turn", "stand", "sit", "wave", "stop", "idle", "continue", "crab_walk", "fist_bump", "dance", "follow_person", "create_behavior"}
        a = str(action.get("action", "stop"))
        if a not in allowed_actions:
            return {"action": "stop", "reason": "unknown_action"}

        out: Dict[str, Any] = {"action": a}
        if "reason" in action and isinstance(action["reason"], str):
            out["reason"] = action["reason"][:200]
        if "speech" in action and isinstance(action["speech"], str):
            out["speech"] = action["speech"][:200]

        if a == "create_behavior":
            out["behavior_name"] = str(action.get("behavior_name", "NewBehavior"))
            out["code"] = str(action.get("code", ""))
        elif a == "walk_forward":
            steps = int(action.get("steps", 1))
            speed = float(action.get("speed", 0.1))
            out["steps"] = max(1, min(10, steps))
            out["speed"] = max(0.05, min(1.0, speed))
        elif a == "turn":
            angle = float(action.get("angle", 0.0))
            steps = int(action.get("steps", 1))
            out["angle"] = max(-180.0, min(180.0, angle))
            out["steps"] = max(1, min(10, steps))
        elif a == "crab_walk":
            direction = str(action.get("direction", "left"))
            steps = int(action.get("steps", 1))
            out["direction"] = "left" if direction == "left" else "right"
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
            "voice_command": current_state.get("voice_command"),
            "face_tracking": current_state.get("face_tracking"),
            "bodies": current_state.get("bodies", []),
            "memory_context": self.memory.get_recent_context(),
            "environment": current_state.get("environment"),
        }

        # SANITIZE: Convert any NumPy types to standard Python types for JSON
        def sanitize(obj):
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [sanitize(i) for i in obj]
            elif hasattr(obj, "item") and callable(getattr(obj, "item")): # Handle NumPy types
                return obj.item()
            elif hasattr(obj, "dtype"): # Fallback for other NumPy-like objects
                try:
                    return obj.tolist() if hasattr(obj, "tolist") else float(obj)
                except:
                    return str(obj)
            return obj

        messages = [
            {"role": "system", "content": self._llm_system_prompt()},
            {"role": "user", "content": json.dumps(sanitize(state_brief))},
        ]

        try:
            content = self.openrouter.chat(messages)
            parsed = json.loads(content.strip())
            action = self._sanitize_action(parsed)
            action["behavior"] = "llm"
            if 'speech' in action:
                logger.info(f"AI Brain responded with speech: {action['speech']}")
            return action
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Rate limit" in error_msg:
                current_state['_ai_error'] = "RATE_LIMIT"
                logger.error("OpenRouter Rate Limit reached. Please wait or add credits.")
            else:
                current_state['_ai_error'] = error_msg
            logger.warning(f"LLM decision failed; falling back to behaviors: {e}")
            return None

    def think(self, current_state: Dict) -> Dict:
        """Main thinking process divided into logical steps."""
        if not self._is_state_valid(current_state):
            return {'action': 'stop', 'error': 'invalid_state'}
        
        if not self._should_make_decision():
            return {'action': 'continue'}
        
        self._record_state(current_state)
        
        # Check if we have an API key at all
        if not self.llm_enabled:
            logger.error("LLM is not enabled (missing API key?)")
            if current_state.get('voice_command'):
                return self._finalize_decision({
                    'action': 'idle',
                    'speech': 'Omlouvám se, ale nemám nastavený přístupový klíč ke svému digitálnímu mozku. Prosím, zkontroluj nastavení API.'
                }, "error")

        # 1. Try LLM (Cloud AI) first
        action = self._think_with_llm(current_state)
        if action:
            return self._finalize_decision(action, "llm")

        # Fallback speech if LLM failed but user said something
        if current_state.get('voice_command'):
            return self._finalize_decision({
                'action': 'idle',
                'speech': 'Zrovna se mi nedaří spojit se svým mozkem v cloudu, ale slyšel jsem tě!'
            }, "fallback")

        # 2. Safety Fallback if LLM required
        if self.llm_required:
            return {"action": "stop", "behavior": "llm", "reason": "llm_unavailable"}

        # 3. Use local behavior manager
        return self._think_locally(current_state)

    def _is_state_valid(self, state: Any) -> bool:
        return isinstance(state, dict)

    def _should_make_decision(self) -> bool:
        current_time = time.time()
        if current_time - self.last_decision_time < self.decision_interval:
            return False
        self.last_decision_time = current_time
        return True

    def _record_state(self, state: Dict):
        self.performance_metrics['decisions_made'] += 1
        state_copy = state.copy()
        state_copy['timestamp'] = time.time()
        self.state_history.append(state_copy)
        if len(self.state_history) > 1000:
            self.state_history.pop(0)

    def _think_locally(self, state: Dict) -> Dict:
        try:
            action = self.behavior_manager.execute_behavior(state)
            behavior_name = self.behavior_manager.current_behavior.name if self.behavior_manager.current_behavior else 'unknown'
            return self._finalize_decision(action, behavior_name)
        except Exception as e:
            logger.error(f"Local behavior failed: {e}")
            return {'action': 'stop', 'error': str(e)}

    def _finalize_decision(self, action: Dict, source: str) -> Dict:
        self.performance_metrics['behaviors_executed'].setdefault(source, 0)
        self.performance_metrics['behaviors_executed'][source] += 1
        
        validated = self._sanitize_action(action)
        validated['behavior'] = source

        # Save to memory if there's speech
        if 'speech' in validated and validated['speech']:
            # We try to find the user's voice command from history
            user_input = "Neznámý povel"
            if self.state_history:
                user_input = self.state_history[-1].get('voice_command', 'Akce robota')
            self.memory.add_interaction(user_input, validated['speech'])

        return validated
    
    def learn(self):
        """Learning process - analyze performance and optimize."""
        logger.info("Learning from experience...")
        
        try:
            # Analyze behavior performance
            behavior_stats = self.behavior_manager.get_behavior_stats()
            
            # Find underperforming behaviors
            for behavior_name, stats in behavior_stats.items():
                success_rate = stats['success_rate']
                total_attempts = stats['success_count'] + stats['failure_count']
                
                if success_rate < 0.3 and total_attempts > 10:
                    logger.warning(f"Behavior '{behavior_name}' has low success rate: {success_rate:.2%} ({total_attempts} attempts)")
                    
                    # Suggest improvement
                    if success_rate < 0.1:
                        logger.warning(f"Behavior '{behavior_name}' may need urgent review or disabling")
                
                # Track performance trends
                if total_attempts > 50 and success_rate > 0.8:
                    logger.info(f"Behavior '{behavior_name}' performing well: {success_rate:.2%}")
            
            # Self-modification: analyze code and find optimizations
            if self.self_modifier.enabled:
                try:
                    opportunities = self.self_modifier.find_optimization_opportunities()
                    if opportunities:
                        logger.info(f"Found {len(opportunities)} optimization opportunities")
                        # Could automatically apply optimizations here
                        # For safety, we just log them for now
                        for opp in opportunities[:3]:  # Show first 3
                            logger.info(f"  - {opp['type']}: {opp['description']}")
                except Exception as e:
                    logger.error(f"Error in learning/self-modification: {e}")
            else:
                logger.debug("Self-modification disabled, skipping optimization analysis")
                
        except Exception as e:
            logger.error(f"Error in learning process: {e}", exc_info=True)
    
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
