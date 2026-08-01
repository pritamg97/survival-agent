from datetime import datetime, timezone
from typing import List


class WorkingMemory:
    """FIFO context buffer that fits in every LLM prompt."""

    def __init__(self, max_items: int = 20):
        self.max_items = max_items
        self._items: List[str] = []

    def add(self, item: str, source: str = "") -> None:
        ts = datetime.now(timezone.utc).strftime("%m-%d %H:%M")
        prefix = f"[{ts}]" + (f" [{source}]" if source else "")
        self._items.append(f"{prefix} {item}")
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items:]

    def get_context(self) -> str:
        return "\n".join(self._items)

    def clear(self) -> None:
        self._items = []

    def to_list(self) -> List[str]:
        return list(self._items)

    @classmethod
    def from_list(cls, items: List[str], max_items: int = 20) -> "WorkingMemory":
        wm = cls(max_items=max_items)
        wm._items = list(items[-max_items:])
        return wm
