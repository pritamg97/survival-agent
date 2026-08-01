import time
from typing import Dict, List, Optional

import requests

from agent.config import CONFIG
from agent.logger import LOGGER

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_BASE = "https://oauth.reddit.com"
PUBLIC_BASE = "https://www.reddit.com"

_token_cache = {"token": None, "expires_at": 0.0}


def _get_token() -> Optional[str]:
    """OAuth2 client-credentials flow for a free Reddit 'script' app.
    Returns None (not an error) if no client id/secret is configured —
    callers fall back to Reddit's public unauthenticated JSON endpoint."""
    if not (CONFIG.REDDIT_CLIENT_ID and CONFIG.REDDIT_CLIENT_SECRET):
        return None
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 30:
        return _token_cache["token"]

    try:
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(CONFIG.REDDIT_CLIENT_ID, CONFIG.REDDIT_CLIENT_SECRET),
            headers={"User-Agent": CONFIG.REDDIT_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
        return _token_cache["token"]
    except (requests.RequestException, ValueError, KeyError) as e:
        LOGGER.warning(f"Reddit OAuth token fetch failed: {e}")
        return None


def fetch_new(subreddit: str, limit: int = 10) -> List[Dict]:
    """Fetch the newest posts from a subreddit as opportunity signals."""
    token = _get_token()
    headers = {"User-Agent": CONFIG.REDDIT_USER_AGENT}

    if token:
        url = f"{OAUTH_BASE}/r/{subreddit}/new"
        headers["Authorization"] = f"Bearer {token}"
    else:
        url = f"{PUBLIC_BASE}/r/{subreddit}/new.json"

    try:
        resp = requests.get(url, headers=headers, params={"limit": limit}, timeout=10)
        resp.raise_for_status()
        children = resp.json()["data"]["children"]
    except (requests.RequestException, KeyError, ValueError) as e:
        LOGGER.warning(f"Reddit fetch r/{subreddit} failed: {e}")
        return []

    signals = []
    for child in children:
        d = child.get("data", {})
        signals.append(
            {
                "source": f"reddit/r/{subreddit}",
                "title": d.get("title", ""),
                "snippet": (d.get("selftext", "") or "")[:200],
                "url": f"https://reddit.com{d.get('permalink', '')}",
                "score": d.get("score", 0),
                "created_utc": d.get("created_utc", 0),
            }
        )
    return signals
