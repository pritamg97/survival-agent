import json
import random

from agent.config import CONFIG
from agent.integrations.stripe_client import create_payment_link
from agent.integrations.vercel_client import deploy_static_page
from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.router import ROUTER
from agent.state import SurvivalState
from agent.utils import slugify


def execute_build(state: SurvivalState) -> SurvivalState:
    """EXECUTE BUILD — build a micro-SaaS product.

    When ENABLE_REAL_DEPLOYMENT is on and this opportunity just cleared the
    approval gate, this deploys a REAL live page (Vercel) with a REAL payable
    Stripe product behind it. Otherwise it falls back to the original
    simulated build (fabricated URL, no real Stripe product)."""
    if state["current_strategy"] != "micro_saas":
        return state

    opportunity = state["current_opportunities"][0] if state["current_opportunities"] else {}
    niche = opportunity.get("niche")

    if niche and any(p.get("niche") == niche and p.get("status") == "live" for p in state["products"]):
        state["working_memory"].append(f"Skip build: '{niche}' already deployed and live")
        return state

    if CONFIG.ENABLE_REAL_DEPLOYMENT and state.get("current_opportunity_approved"):
        state["current_opportunity_approved"] = False  # consume the one-time approval
        return _execute_real_build(state, niche)

    return _execute_simulated_build(state, niche)


def _execute_real_build(state: SurvivalState, niche) -> SurvivalState:
    metabolism = Metabolism(state)

    prompt = (
        f"Create a micro-SaaS landing page spec. Task: {state['current_task']}. "
        "Return ONLY JSON with keys: name, description, price, "
        "landing_page_html (a COMPLETE, self-contained single-file HTML page with inline CSS, "
        "no external assets/scripts, including a headline, a short pitch, and a buy button whose "
        "href is exactly the literal placeholder text {{PAYMENT_LINK}})."
    )
    try:
        raw = ROUTER.call([{"role": "user", "content": prompt}], task_type="coding", max_tokens=1800)
        spec = json.loads(raw)
    except (json.JSONDecodeError, KeyError, RuntimeError) as e:
        state["consecutive_failures"] += 1
        LOGGER.warning(f"execute_build (real) spec generation failed: {e}")
        return state

    name = spec.get("name") or "Untitled Product"
    price = float(spec.get("price", 9.0))

    link = create_payment_link(name, price)
    if not link:
        state["consecutive_failures"] += 1
        state["working_memory"].append(f"Real build failed: could not create Stripe payment link for '{name}'")
        LOGGER.warning(f"Real build failed: Stripe payment link creation failed for '{name}'")
        return state

    html = spec.get("landing_page_html") or f"<html><body><h1>{name}</h1><a href='{{{{PAYMENT_LINK}}}}'>Buy</a></body></html>"
    html = html.replace("{{PAYMENT_LINK}}", link["url"])

    live_url = deploy_static_page(slugify(name), html)
    if not live_url:
        state["consecutive_failures"] += 1
        state["working_memory"].append(
            f"Real build failed: Vercel deploy failed for '{name}' "
            f"(Stripe product {link['product_id']} was already created — check your Stripe dashboard)"
        )
        LOGGER.warning(f"Real build failed: Vercel deployment failed for '{name}'")
        return state

    try:
        metabolism.burn_infra(round(random.uniform(0.30, 1.50), 2), f"Real build: {name}")
    except AgentDeathException:
        return state

    product = {
        "name": name,
        "description": spec.get("description", ""),
        "price": price,
        "status": "live",
        "url": live_url,
        "customers": 0,
        "revenue": 0.0,
        "created_at": state["cycle_start_time"],
        "age_cycles": 0,
        "niche": niche,
        "real": True,
        "stripe_product_id": link["product_id"],
        "stripe_price_id": link["price_id"],
        "stripe_payment_link_id": link["payment_link_id"],
        "stripe_payment_link_url": link["url"],
        "stripe_seen_sessions": [],
    }
    state["products"].append(product)
    state["working_memory"].append(f"REAL product deployed: {name} @ ${price:.2f} -> {live_url}")
    LOGGER.info(f"REAL product deployed: {name} @ ${price:.2f} -> {live_url} (stripe: {link['payment_link_id']})")
    return state


def _execute_simulated_build(state: SurvivalState, niche) -> SurvivalState:
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
            "niche": niche,
            "real": False,
        }
        state["products"].append(product)
        state["working_memory"].append(f"Product built (simulated): {product['name']} @ ${product['price']:.2f}")
        LOGGER.info(f"Product built (simulated): {product['name']} @ ${product['price']:.2f}")
    except (json.JSONDecodeError, KeyError, RuntimeError) as e:
        state["consecutive_failures"] += 1
        LOGGER.warning(f"execute_build (simulated) failed: {e}")

    return state
