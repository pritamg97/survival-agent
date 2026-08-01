import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

from agent.config import CONFIG
from agent.logger import LOGGER

_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


class SemanticMemory:
    """Vector-based fact store, queried by semantic similarity."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or CONFIG.SEMANTIC_DB_PATH
        self._facts: List[Dict] = self._load()

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
            json.dump(self._facts, f, indent=2)

    def add(self, fact: str, category: str = "general", confidence: float = 0.5, source: str = "") -> int:
        fact_id = (max((f["id"] for f in self._facts), default=0)) + 1
        embedding = _get_model().encode(fact).tolist()
        self._facts.append(
            {
                "id": fact_id,
                "fact": fact,
                "category": category,
                "confidence": confidence,
                "source": source,
                "created": datetime.now(timezone.utc).isoformat(),
                "times_validated": 0,
                "times_contradicted": 0,
                "embedding": embedding,
            }
        )
        self._save()
        return fact_id

    def query(self, query: str, top_k: int = 5, min_confidence: float = 0.3) -> List[str]:
        candidates = [f for f in self._facts if f["confidence"] >= min_confidence]
        if not candidates:
            return []
        query_vec = np.array(_get_model().encode(query))
        scored = []
        for f in candidates:
            vec = np.array(f["embedding"])
            denom = (np.linalg.norm(query_vec) * np.linalg.norm(vec)) or 1e-9
            sim = float(np.dot(query_vec, vec) / denom)
            scored.append((sim, f))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f["fact"] for _, f in scored[:top_k]]

    def validate(self, fact_id: int, outcome: bool) -> None:
        for f in self._facts:
            if f["id"] == fact_id:
                if outcome:
                    f["times_validated"] += 1
                    f["confidence"] = min(1.0, f["confidence"] + 0.1)
                else:
                    f["times_contradicted"] += 1
                    f["confidence"] = max(0.0, f["confidence"] - 0.15)
                self._save()
                return
        LOGGER.warning(f"validate(): fact_id {fact_id} not found")

    def get_by_category(self, category: str) -> List[Dict]:
        return [f for f in self._facts if f["category"] == category]

    def get_all(self) -> List[Dict]:
        return list(self._facts)
