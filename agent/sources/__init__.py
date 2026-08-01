from typing import Dict, List

from agent.config import CONFIG
from agent.logger import LOGGER
from agent.sources.hn_source import fetch_freelance_threads
from agent.sources.reddit_source import fetch_new as fetch_reddit
from agent.sources.upwork_source import fetch_saved_search


def gather_signals(limit_per_source: int = 8) -> List[Dict]:
    """Read-only sweep of free opportunity signals. Never fails the caller —
    any source that errors or isn't configured just contributes nothing."""
    signals: List[Dict] = []

    for sub in CONFIG.OPPORTUNITY_SUBREDDITS:
        signals.extend(fetch_reddit(sub, limit=limit_per_source))

    signals.extend(fetch_freelance_threads(limit=limit_per_source))
    signals.extend(fetch_saved_search())

    LOGGER.info(f"Opportunity signals gathered: {len(signals)} across {1 + len(CONFIG.OPPORTUNITY_SUBREDDITS)} sources")
    return signals
