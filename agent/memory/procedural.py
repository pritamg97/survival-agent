import json
import os
from typing import Dict, List, Optional

from agent.config import CONFIG
from agent.logger import LOGGER


class ProceduralMemory:
    """Reusable skills/templates, retrieved by keyword match + success weighting."""

    def __init__(self, skills_dir: Optional[str] = None):
        self.skills_dir = skills_dir or CONFIG.SKILLS_DIR
        os.makedirs(self.skills_dir, exist_ok=True)

    def _path(self, name: str) -> str:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return os.path.join(self.skills_dir, f"{safe}.json")

    def add_skill(
        self, name: str, trigger: str, code: str, description: str = "", success_rate: float = 0.0
    ) -> None:
        skill = {
            "name": name,
            "trigger": trigger,
            "code": code,
            "description": description,
            "success_rate": success_rate,
            "usage_count": 0,
        }
        with open(self._path(name), "w") as f:
            json.dump(skill, f, indent=2)
        LOGGER.info(f"Procedural memory: added skill '{name}'")

    def find_skill(self, context: str) -> Optional[Dict]:
        context_lower = context.lower()
        best, best_score = None, 0.0
        for skill in self._all_skills():
            trigger_words = skill["trigger"].lower().split()
            hits = sum(1 for w in trigger_words if w in context_lower)
            if hits == 0:
                continue
            score = hits * (1 + skill["success_rate"])
            if score > best_score:
                best, best_score = skill, score
        return best

    def use_skill(self, name: str, **kwargs) -> Optional[str]:
        skill = self.get_skill(name)
        if not skill:
            return None
        skill["usage_count"] += 1
        with open(self._path(name), "w") as f:
            json.dump(skill, f, indent=2)
        try:
            return skill["code"].format(**kwargs)
        except (KeyError, IndexError):
            return skill["code"]

    def record_success(self, name: str, success: bool) -> None:
        skill = self.get_skill(name)
        if not skill:
            return
        n = max(skill["usage_count"], 1)
        prev_successes = skill["success_rate"] * n
        skill["success_rate"] = (prev_successes + (1 if success else 0)) / n
        with open(self._path(name), "w") as f:
            json.dump(skill, f, indent=2)

    def list_skills(self) -> List[str]:
        return [s["name"] for s in self._all_skills()]

    def get_skill(self, name: str) -> Optional[Dict]:
        path = self._path(name)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    def _all_skills(self) -> List[Dict]:
        skills = []
        for fname in os.listdir(self.skills_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self.skills_dir, fname), "r") as f:
                        skills.append(json.load(f))
                except (json.JSONDecodeError, OSError):
                    continue
        return skills
