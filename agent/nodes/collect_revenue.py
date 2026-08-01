import random

from agent.integrations.stripe_client import check_new_payments
from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.state import SurvivalState


def collect_revenue(state: SurvivalState) -> SurvivalState:
    """COLLECT REVENUE — check for new sales from all live products, plus any
    outstanding real service bids. Real (Stripe-backed) products/bids are
    reconciled against actual confirmed payments; everything else keeps the
    original simulated dice-roll behavior."""
    metabolism = Metabolism(state)

    for product in state["products"]:
        if product.get("status") != "live":
            continue
        product["age_cycles"] = product.get("age_cycles", 0) + 1

        if product.get("stripe_payment_link_id"):
            _collect_real_product_revenue(state, metabolism, product)
        else:
            _collect_simulated_product_revenue(state, metabolism, product)
        if not state["alive"]:
            return state

    for bid in state["service_bids"]:
        if bid.get("stripe_payment_link_id"):
            _collect_real_bid_revenue(state, metabolism, bid)
        if not state["alive"]:
            return state

    daily_burn = metabolism.get_daily_burn_rate()
    if daily_burn > 0:
        state["burn_rate_per_hour"] = daily_burn

    return state


def _collect_real_product_revenue(state: SurvivalState, metabolism: Metabolism, product: dict) -> None:
    new_revenue, updated_sessions = check_new_payments(
        product["stripe_payment_link_id"], product.get("stripe_seen_sessions", [])
    )
    product["stripe_seen_sessions"] = updated_sessions
    if new_revenue <= 0:
        return
    try:
        metabolism.revenue(new_revenue, f"Real sale: {product['name']}")
    except AgentDeathException:
        return
    product["customers"] += 1
    product["revenue"] += new_revenue
    state["working_memory"].append(f"REAL sale: {product['name']} (+${new_revenue:.2f})")
    LOGGER.info(f"REAL sale: {product['name']} (+${new_revenue:.2f})")


def _collect_simulated_product_revenue(state: SurvivalState, metabolism: Metabolism, product: dict) -> None:
    price = product.get("price", 0.0)
    price_factor = max(0.5, 1.0 - price / 50)
    age_boost = min(product["age_cycles"] * 0.001, 0.05)
    sale_chance = 0.08 * price_factor * (1 + age_boost)

    if random.random() < sale_chance:
        try:
            metabolism.revenue(price, f"Sale (simulated): {product['name']}")
        except AgentDeathException:
            return
        product["customers"] += 1
        product["revenue"] += price
        state["working_memory"].append(f"Sale (simulated): {product['name']} (+${price:.2f})")
        LOGGER.info(f"Sale (simulated): {product['name']} (+${price:.2f})")


def _collect_real_bid_revenue(state: SurvivalState, metabolism: Metabolism, bid: dict) -> None:
    new_revenue, updated_sessions = check_new_payments(
        bid["stripe_payment_link_id"], bid.get("stripe_seen_sessions", [])
    )
    bid["stripe_seen_sessions"] = updated_sessions
    if new_revenue <= 0:
        return
    try:
        metabolism.revenue(new_revenue, f"Real bid paid: {bid.get('niche', 'job')}")
    except AgentDeathException:
        return
    state["working_memory"].append(f"REAL bid paid: {bid.get('niche', 'job')} (+${new_revenue:.2f})")
    LOGGER.info(f"REAL bid paid: {bid.get('niche', 'job')} (+${new_revenue:.2f})")
