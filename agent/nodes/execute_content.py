import random

from agent.config import CONFIG
from agent.integrations.vercel_client import deploy_static_page
from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.router import ROUTER
from agent.state import SurvivalState
from agent.utils import slugify

DEFAULT_TOPIC = "best productivity tools 2026"


def execute_content(state: SurvivalState) -> SurvivalState:
    """EXECUTE CONTENT FARM — write an SEO article.

    When ENABLE_REAL_DEPLOYMENT is on and this opportunity just cleared the
    approval gate, this actually publishes the article to a real live URL
    (Vercel). No ad-network integration exists yet, so real publishes earn $0
    automatically — monetizing them for real needs an ad account wired up
    separately. Otherwise falls back to the original fully-simulated path."""
    if state["current_strategy"] != "content_farm":
        return state

    if CONFIG.ENABLE_REAL_DEPLOYMENT and state.get("current_opportunity_approved"):
        state["current_opportunity_approved"] = False  # consume the one-time approval
        return _execute_real_publish(state)

    return _execute_simulated_publish(state)


def _execute_real_publish(state: SurvivalState) -> SurvivalState:
    metabolism = Metabolism(state)
    opportunity = state["current_opportunities"][0] if state["current_opportunities"] else {}
    topic = opportunity.get("niche") or DEFAULT_TOPIC

    prompt = (
        f"Write a complete, self-contained single-file SEO article as HTML with inline CSS about "
        f"'{topic}': one H1 title, an intro paragraph, 3 H2 sections with bullet points, and a "
        "conclusion. Return ONLY the raw HTML — no markdown fences, no JSON, no commentary."
    )
    try:
        html = ROUTER.call([{"role": "user", "content": prompt}], task_type="marketing", max_tokens=1800)
    except RuntimeError as e:
        state["consecutive_failures"] += 1
        LOGGER.warning(f"execute_content (real) generation failed: {e}")
        return state

    live_url = deploy_static_page(f"article-{slugify(topic)}", html)
    if not live_url:
        state["consecutive_failures"] += 1
        state["working_memory"].append(f"Real publish failed for '{topic}' (Vercel deploy failed)")
        LOGGER.warning(f"Real publish failed for '{topic}'")
        return state

    try:
        metabolism.burn_infra(0.05, f"Real publish: {topic}")
    except AgentDeathException:
        return state

    state["working_memory"].append(
        f"REAL article published: {topic} -> {live_url} (no ad-revenue integration wired up — $0 automatic)"
    )
    LOGGER.info(f"REAL article published: {topic} -> {live_url}")
    return state


def _execute_simulated_publish(state: SurvivalState) -> SurvivalState:
    metabolism = Metabolism(state)

    prompt = (
        f"Write a short SEO article about '{DEFAULT_TOPIC}'. "
        "Structure: one H2 heading, 3 H3 sections, bullet points, and a conclusion."
    )
    articles_written = state["provider_usage"].get("_articles_written", 0)

    try:
        ROUTER.call([{"role": "user", "content": prompt}], task_type="marketing", max_tokens=1200)
    except RuntimeError as e:
        state["consecutive_failures"] += 1
        LOGGER.warning(f"execute_content (simulated) generation failed: {e}")
        return state

    try:
        metabolism.burn_infra(0.05, "Content farm: publishing cost")
    except AgentDeathException:
        return state

    state["provider_usage"]["_articles_written"] = articles_written + 1
    revenue_chance = min(0.05 + 0.001 * articles_written, 0.30)

    if random.random() < revenue_chance:
        ad_revenue = round(random.uniform(0.50, 5.00), 2)
        try:
            metabolism.revenue(ad_revenue, "Content farm: ad revenue (simulated)")
        except AgentDeathException:
            return state
        state["working_memory"].append(f"Content farm (simulated): article earned ${ad_revenue:.2f}")
        LOGGER.info(f"Content farm (simulated): article earned ${ad_revenue:.2f}")
    else:
        state["working_memory"].append("Content farm (simulated): article published, no revenue yet")
        LOGGER.info("Content farm (simulated): article published, no immediate revenue")

    return state
