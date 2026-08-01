import json
import random

from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.router import ROUTER
from agent.state import SurvivalState
from agent.utils import slugify


def execute_build(state: SurvivalState) -> SurvivalState:
    """EXECUTE BUILD — build a simple micro-SaaS product."""
    if state["current_strategy"] != "micro_saas":
        return state

    metabolism = Metabolism(state)
    cost = round(random.uniform(0.30, 1.50), 2)
    try:
        metabolism.burn_infra(cost, f"Build: {state['current_task']}")
    except AgentDeathException:
        return state

    prompt = (
        f"Create a micro-SaaS spec. Task: {state['current_task']}. "
        "Return ONLY JSON with keys: name, description, price, landing_page_copy, stripe_product_name."
    )

    try:
        raw = ROUTER.call([{"role": "user", "content": prompt}], task_type="coding", max_tokens=800)
        spec = json.loads(raw)
        product = {
            "name": spec["name"],
            "description": spec.get("description", ""),
            "price": float(spec.get("price", 9.0)),
            "status": "live",
            "url": f"https://{slugify(spec['name'])}.vercel.app",
            "customers": 0,
            "revenue": 0.0,
            "created_at": state["cycle_start_time"],
            "age_cycles": 0,
        }
        state["products"].append(product)
        state["working_memory"].append(f"Product built: {product['name']} @ ${product['price']:.2f}")
        LOGGER.info(f"Product built: {product['name']} @ ${product['price']:.2f}")
    except (json.JSONDecodeError, KeyError, RuntimeError) as e:
        state["consecutive_failures"] += 1
        LOGGER.warning(f"execute_build failed: {e}")

    return state
