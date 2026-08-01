import random

from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.router import ROUTER
from agent.state import SurvivalState

DEFAULT_TOPIC = "best productivity tools 2026"


def execute_content(state: SurvivalState) -> SurvivalState:
    """EXECUTE CONTENT FARM — write SEO articles for long-term ad revenue."""
    if state["current_strategy"] != "content_farm":
        return state

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
        LOGGER.warning(f"execute_content generation failed: {e}")
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
            metabolism.revenue(ad_revenue, "Content farm: ad revenue")
        except AgentDeathException:
            return state
        state["working_memory"].append(f"Content farm: article earned ${ad_revenue:.2f}")
        LOGGER.info(f"Content farm: article earned ${ad_revenue:.2f}")
    else:
        state["working_memory"].append("Content farm: article published, no revenue yet")
        LOGGER.info("Content farm: article published, no immediate revenue")

    return state
