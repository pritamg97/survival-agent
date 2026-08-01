import random

from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.state import SurvivalState


def collect_revenue(state: SurvivalState) -> SurvivalState:
    """COLLECT REVENUE — check for new sales from all live products."""
    metabolism = Metabolism(state)

    for product in state["products"]:
        if product.get("status") != "live":
            continue

        product["age_cycles"] = product.get("age_cycles", 0) + 1
        price = product.get("price", 0.0)
        price_factor = max(0.5, 1.0 - price / 50)
        age_boost = min(product["age_cycles"] * 0.001, 0.05)
        sale_chance = 0.08 * price_factor * (1 + age_boost)

        if random.random() < sale_chance:
            try:
                metabolism.revenue(price, f"Sale: {product['name']}")
            except AgentDeathException:
                return state
            product["customers"] += 1
            product["revenue"] += price
            state["working_memory"].append(f"Sale: {product['name']} (+${price:.2f})")
            LOGGER.info(f"Sale: {product['name']} (+${price:.2f})")

    daily_burn = metabolism.get_daily_burn_rate()
    if daily_burn > 0:
        state["burn_rate_per_hour"] = daily_burn

    return state
