import time
from typing import Dict, List

import requests

from agent.logger import LOGGER

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def fetch_freelance_threads(query: str = "freelance hire seeking", limit: int = 10, max_age_days: int = 30) -> List[Dict]:
    """Free, keyless Hacker News search (Algolia) for freelance/hiring signals.

    Algolia's default /search endpoint ranks by relevance, not recency — a
    highly-upvoted 'does anybody need a developer' thread from 2010 ranks
    just as high as anything current, and bidding on a dead decade-old post
    is pointless. Restricts to posts from the last max_age_days via
    numericFilters on created_at_i."""
    cutoff = int(time.time()) - max_age_days * 86400
    try:
        resp = requests.get(
            ALGOLIA_URL,
            params={
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
                "numericFilters": f"created_at_i>{cutoff}",
            },
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
