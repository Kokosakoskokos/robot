import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

class LongTermMemory:
    """Handles persistent storage for conversations and people."""
    
    def __init__(self, data_dir: str = "data/memory"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.conv_file = self.data_dir / "conversations.json"
        self.people_file = self.data_dir / "people.json"
        
        self.history: List[Dict] = self._load_json(self.conv_file, [])
        self.people: Dict[str, Dict] = self._load_json(self.people_file, {})
        
        logger.info(f"Memory system initialized. Loaded {len(self.history)} interactions.")

    def _load_json(self, path: Path, default):
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading memory file {path}: {e}")
        return default

    def _save_json(self, data, path: Path):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving memory file {path}: {e}")

    def add_interaction(self, user_input: str, robot_response: str):
        """Save a new conversation snippet."""
        entry = {
            "timestamp": time.time(),
            "user": user_input,
            "robot": robot_response
        }
        self.history.append(entry)
        # Keep only last 500 interactions to save disk/token space
        if len(self.history) > 500:
            self.history.pop(0)
        self._save_json(self.history, self.conv_file)

    def get_recent_context(self, limit: int = 10) -> str:
        """Get last N interactions as a string for the AI prompt."""
        if not self.history:
            return "Žádná předchozí konverzace."
        
        context = []
        for h in self.history[-limit:]:
            context.append(f"Uživatel: {h['user']}\nClanker: {h['robot']}")
        return "\n---\n".join(context)

    def update_person(self, name: str, data: Dict):
        """Store info about a specific person."""
        if name not in self.people:
            self.people[name] = {"first_seen": time.time(), "interactions": 0}
        
        self.people[name].update(data)
        self.people[name]["last_seen"] = time.time()
        self.people[name]["interactions"] += 1
        self._save_json(self.people, self.people_file)

    def get_person_info(self, name: str) -> Optional[Dict]:
        return self.people.get(name)
