import xml.etree.ElementTree as ET
from typing import Dict, List

import requests

from agent.config import CONFIG
from agent.logger import LOGGER


def fetch_saved_search() -> List[Dict]:
    """Reads the user's own Upwork saved-search RSS feed, if configured.
    Upwork's public jobs-search API requires an approved partnership and isn't
    self-serve; the RSS feed from a saved search is the documented, ToS-compliant
    free alternative. Returns [] silently if UPWORK_RSS_URL isn't set."""
    if not CONFIG.UPWORK_RSS_URL:
        return []

    try:
        resp = requests.get(CONFIG.UPWORK_RSS_URL, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError) as e:
        LOGGER.warning(f"Upwork RSS fetch failed: {e}")
        return []

    signals = []
    for item in root.findall(".//item")[:15]:
        signals.append(
            {
                "source": "upwork",
                "title": (item.findtext("title") or "").strip(),
                "snippet": (item.findtext("description") or "").strip()[:200],
                "url": (item.findtext("link") or "").strip(),
                "score": 0,
                "created_utc": 0,
            }
        )
    return signals
