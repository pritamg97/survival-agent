from typing import Optional

import requests

from agent.config import CONFIG
from agent.logger import LOGGER

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OAUTH_BASE = "https://oauth.reddit.com"


def _get_write_token() -> Optional[str]:
    """Password-grant OAuth for the operator's own Reddit account. Only used
    for real posting — the read-only opportunity scan uses app-only client
    credentials instead. Requires REDDIT_USERNAME/REDDIT_PASSWORD in addition
    to REDDIT_CLIENT_ID/SECRET.

    Note: Reddit has been tightening password-grant availability for newer
    apps; if this starts failing with invalid_grant, the account/app may need
    the OAuth authorization-code flow instead — that requires a one-time
    interactive login and isn't implemented here."""
    if not (CONFIG.REDDIT_CLIENT_ID and CONFIG.REDDIT_CLIENT_SECRET and CONFIG.REDDIT_USERNAME and CONFIG.REDDIT_PASSWORD):
        return None
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "password",
                "username": CONFIG.REDDIT_USERNAME,
                "password": CONFIG.REDDIT_PASSWORD,
            },
            auth=(CONFIG.REDDIT_CLIENT_ID, CONFIG.REDDIT_CLIENT_SECRET),
            headers={"User-Agent": CONFIG.REDDIT_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("access_token")
    except (requests.RequestException, ValueError) as e:
        LOGGER.error(f"Reddit write-auth failed: {e}")
        return None


def post_bid_comment(post_url: str, message: str) -> bool:
    """Posts a REAL, publicly visible comment on a Reddit thread under the
    operator's account, offering to do the job. This is a genuine external
    action with real consequences (spam/rule violations, reputational risk) —
    it only runs if ENABLE_REAL_BIDDING=true AND the caller has already
    confirmed a fresh per-opportunity email approval."""
    if not CONFIG.ENABLE_REAL_BIDDING:
        LOGGER.warning("ENABLE_REAL_BIDDING is false; refusing to post a real bid")
        return False

    token = _get_write_token()
    if not token:
        LOGGER.warning("No Reddit write credentials configured; cannot post bid")
        return False

    try:
        info_resp = requests.get(
            f"{post_url.rstrip('/')}.json",
            headers={"User-Agent": CONFIG.REDDIT_USER_AGENT},
            timeout=10,
        )
        info_resp.raise_for_status()
        fullname = info_resp.json()[0]["data"]["children"][0]["data"]["name"]
    except (requests.RequestException, ValueError, KeyError, IndexError) as e:
        LOGGER.error(f"Could not resolve Reddit post id for {post_url}: {e}")
        return False

    try:
        resp = requests.post(
            f"{OAUTH_BASE}/api/comment",
            data={"api_type": "json", "thing_id": fullname, "text": message},
            headers={"Authorization": f"Bearer {token}", "User-Agent": CONFIG.REDDIT_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        errors = resp.json().get("json", {}).get("errors", [])
        if errors:
            LOGGER.error(f"Reddit comment API returned errors: {errors}")
            return False
        LOGGER.info(f"Posted real bid comment on {post_url}")
        return True
    except (requests.RequestException, ValueError) as e:
        LOGGER.error(f"Reddit comment post failed: {e}")
        return False
