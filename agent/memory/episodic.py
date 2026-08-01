import json
import os
from typing import Dict, List, Optional

from agent.config import CONFIG
from agent.logger import LOGGER

COMPRESSION_PROMPT = """You are compressing a survival agent's daily log into actionable learnings.

Day {day} Summary: revenue=${revenue:.2f}, costs=${costs:.2f}
Strategies used: {strategies}
Products: {products}

Raw events (last 20):
{events}

Generate a 5-bullet summary: what worked, what failed, patterns, next actions."""


class EpisodicMemory:
    """Daily event logs, compressed every 3 days via LLM reflection."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or CONFIG.EPISODIC_DB_PATH
        self._episodes: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with open(self.db_path, "w") as f:
            json.dump(self._episodes, f, indent=2)

    def record_day(self, day: int, events: List[Dict]) -> None:
        revenue = sum(e.get("amount", 0) for e in events if e.get("type") == "revenue")
        costs = sum(e.get("amount", 0) for e in events if e.get("type") in ("cost", "burn"))
        strategies = sorted({e.get("strategy") for e in events if e.get("strategy")})
        products = sorted({e.get("product") for e in events if e.get("product")})

        episode = {
            "day": day,
            "date": events[-1]["timestamp"] if events else "",
            "events": events,
            "revenue": revenue,
            "cost": costs,
            "products": products,
            "strategies": strategies,
            "summary": None,
        }
        self._episodes.append(episode)
        self._save()
        LOGGER.info(f"Episodic memory: recorded day {day} ({len(events)} events)")

    def compress_day(self, day_index: int = -1, state: Optional[dict] = None) -> Optional[str]:
        if not self._episodes:
            return None
        episode = self._episodes[day_index]
        from agent.router import ROUTER

        prompt = COMPRESSION_PROMPT.format(
            day=episode["day"],
            revenue=episode["revenue"],
            costs=episode["cost"],
            strategies=", ".join(episode["strategies"]) or "none",
            products=", ".join(episode["products"]) or "none",
            events="\n".join(str(e) for e in episode["events"][-20:]),
        )
        try:
            summary = ROUTER.call(
                [{"role": "user", "content": prompt}], task_type="reasoning", max_tokens=400, state=state
            )
        except Exception as e:  # noqa: BLE001
            LOGGER.warning(f"Episodic compression failed: {e}")
            return None

        episode["summary"] = summary
        self._save()
        return summary

    def get_recent_summary(self, days: int = 3) -> str:
        recent = self._episodes[-days:]
        parts = []
        for ep in recent:
            text = ep.get("summary") or f"Day {ep['day']}: revenue=${ep['revenue']:.2f}, cost=${ep['cost']:.2f}"
            parts.append(text)
        return "\n\n".join(parts)

    def get_all_episodes(self) -> List[Dict]:
        return list(self._episodes)
