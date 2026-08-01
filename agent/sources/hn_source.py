from typing import Dict, List

import requests

from agent.logger import LOGGER

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def fetch_freelance_threads(query: str = "freelance hire seeking", limit: int = 10) -> List[Dict]:
    """Free, keyless Hacker News search (Algolia) for freelance/hiring signals."""
    try:
        resp = requests.get(
            ALGOLIA_URL,
            params={"query": query, "tags": "story", "hitsPerPage": limit},
            timeout=10,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except (requests.RequestException, ValueError) as e:
        LOGGER.warning(f"Hacker News fetch failed: {e}")
        return []

    return [
        {
            "source": "hackernews",
            "title": hit.get("title") or hit.get("story_title") or "",
            "snippet": (hit.get("story_text") or hit.get("comment_text") or "")[:200],
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "score": hit.get("points", 0),
            "created_utc": hit.get("created_at_i", 0),
        }
        for hit in hits
    ]
