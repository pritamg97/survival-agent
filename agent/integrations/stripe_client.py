from typing import List, Optional, Tuple

import requests

from agent.config import CONFIG
from agent.logger import LOGGER

API_BASE = "https://api.stripe.com/v1"


def _auth() -> Tuple[str, str]:
    return (CONFIG.STRIPE_SECRET_KEY, "")


def create_payment_link(name: str, price_usd: float) -> Optional[dict]:
    """Creates a REAL Stripe Product + Price + Payment Link (test or live mode,
    depending on which STRIPE_SECRET_KEY is configured). Returns
    {product_id, price_id, payment_link_id, url}, or None if unconfigured/failed."""
    if not CONFIG.STRIPE_SECRET_KEY:
        return None

    try:
        product_resp = requests.post(
            f"{API_BASE}/products", auth=_auth(), data={"name": name}, timeout=15
        )
        product_resp.raise_for_status()
        product_id = product_resp.json()["id"]

        price_resp = requests.post(
            f"{API_BASE}/prices",
            auth=_auth(),
            data={
                "product": product_id,
                "unit_amount": max(int(round(price_usd * 100)), 50),  # Stripe minimum ~$0.50
                "currency": "usd",
            },
            timeout=15,
        )
        price_resp.raise_for_status()
        price_id = price_resp.json()["id"]

        link_resp = requests.post(
            f"{API_BASE}/payment_links",
            auth=_auth(),
            data={"line_items[0][price]": price_id, "line_items[0][quantity]": 1},
            timeout=15,
        )
        link_resp.raise_for_status()
        link_data = link_resp.json()

        LOGGER.info(f"Stripe payment link created for '{name}': {link_data['url']}")
        return {
            "product_id": product_id,
            "price_id": price_id,
            "payment_link_id": link_data["id"],
            "url": link_data["url"],
        }
    except (requests.RequestException, KeyError, ValueError) as e:
        LOGGER.error(f"Stripe payment link creation failed for '{name}': {e}")
        return None


def check_new_payments(payment_link_id: str, seen_session_ids: List[str]) -> Tuple[float, List[str]]:
    """Polls completed Checkout Sessions for a payment link. Returns
    (new_revenue_this_check, updated_seen_session_ids) — only counts sessions
    with payment_status == 'paid' that aren't already in seen_session_ids, so
    repeated polling never double-credits a payment."""
    if not (CONFIG.STRIPE_SECRET_KEY and payment_link_id):
        return 0.0, seen_session_ids

    try:
        resp = requests.get(
            f"{API_BASE}/checkout/sessions",
            auth=_auth(),
            params={"payment_link": payment_link_id, "limit": 25},
            timeout=15,
        )
        resp.raise_for_status()
        sessions = resp.json().get("data", [])
    except (requests.RequestException, ValueError) as e:
        LOGGER.warning(f"Stripe session poll failed for {payment_link_id}: {e}")
        return 0.0, seen_session_ids

    new_total = 0.0
    updated = list(seen_session_ids)
    for session in sessions:
        if session.get("payment_status") == "paid" and session["id"] not in updated:
            new_total += (session.get("amount_total") or 0) / 100
            updated.append(session["id"])

    if new_total > 0:
        LOGGER.info(f"Stripe: ${new_total:.2f} in new confirmed payment(s) on {payment_link_id}")

    return new_total, updated
