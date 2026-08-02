import json
from typing import Optional

from agent.logger import LOGGER
from agent.router import ROUTER
from agent.utils import extract_json


def generate_listing_copy(product: dict, state: Optional[dict] = None) -> Optional[dict]:
    """Generates ready-to-paste copy for a micro-SaaS launch directory
    listing (TinyLaunch, Uneed, OpenHunts, etc.) — title, one-line tagline,
    and a short description. Deliberately does NOT submit anywhere: those
    sites require creating an account and logging in, which would mean the
    agent holding directory-site credentials under the operator's identity.
    This just prepares the copy so the operator can paste it in themselves,
    on their own account, whenever they choose to."""
    prompt = (
        f"Write launch-directory listing copy for this product:\n"
        f"Name: {product.get('name')}\n"
        f"Description: {product.get('description')}\n"
        f"URL: {product.get('url')}\n"
        f"Price: ${product.get('price')}\n\n"
        "Return ONLY JSON with keys: title (product name, max 40 chars), "
        "tagline (one punchy line, max 60 chars), description (2-3 sentences, "
        "max 300 chars, written for a maker/indie-hacker audience)."
    )
    try:
        raw = ROUTER.call([{"role": "user", "content": prompt}], task_type="marketing", max_tokens=400, state=state)
        copy = json.loads(extract_json(raw))
    except (json.JSONDecodeError, KeyError, ValueError, TypeError, RuntimeError) as e:
        LOGGER.warning(f"Directory listing copy generation failed for '{product.get('name')}': {e}")
        return None

    LOGGER.info(f"Directory listing copy generated for '{product.get('name')}'")
    return copy
