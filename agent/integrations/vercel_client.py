from typing import Optional

import requests

from agent.config import CONFIG
from agent.logger import LOGGER

API_BASE = "https://api.vercel.com"


def deploy_static_page(project_name: str, html: str) -> Optional[str]:
    """Deploys a single static HTML file as a real, live Vercel deployment and
    returns its https URL. Returns None if VERCEL_TOKEN is unconfigured or the
    deploy fails — callers should treat that as 'no real deployment happened',
    not raise.

    Uses Vercel's inline-file deployment (v13/deployments) suitable for small
    single-file sites; large multi-file projects would need the chunked
    file-upload flow instead, which isn't implemented here."""
    if not CONFIG.VERCEL_TOKEN:
        return None

    headers = {"Authorization": f"Bearer {CONFIG.VERCEL_TOKEN}"}
    params = {"teamId": CONFIG.VERCEL_TEAM_ID} if CONFIG.VERCEL_TEAM_ID else {}
    payload = {
        "name": project_name,
        "files": [{"file": "index.html", "data": html}],
        "target": "production",
    }

    try:
        resp = requests.post(
            f"{API_BASE}/v13/deployments", headers=headers, params=params, json=payload, timeout=30
        )
        resp.raise_for_status()
        url = resp.json().get("url")
        if not url:
            LOGGER.error(f"Vercel deployment for '{project_name}' returned no url")
            return None
        live_url = f"https://{url}"
        LOGGER.info(f"Vercel deployment live: {live_url}")
        return live_url
    except (requests.RequestException, ValueError) as e:
        LOGGER.error(f"Vercel deployment failed for '{project_name}': {e}")
        return None
