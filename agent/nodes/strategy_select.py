from agent.logger import LOGGER
from agent.state import SurvivalState


def strategy_select(state: SurvivalState) -> SurvivalState:
    """STRATEGY SELECTOR — pick execution strategy based on survival pressure."""
    if state["panic_mode"]:
        state["current_strategy"] = "service_arbitrage"
        state["current_task"] = "Find any paying job, hire cheaper worker, pocket difference"
    elif state["emergency_mode"]:
        state["current_strategy"] = "service_arbitrage"
        state["current_task"] = "Quick arbitrage job — under 1 hour to first dollar"
    elif state["current_opportunities"]:
        best = state["current_opportunities"][0]
        state["current_strategy"] = best["strategy"]
        state["current_task"] = best["solution"]
    else:
        state["current_strategy"] = "content_farm"
        state["current_task"] = "Write SEO article for ad revenue (no opportunities found)"

    LOGGER.info(f"STRATEGY: {state['current_strategy']} — {state['current_task']}")
    state["working_memory"].append(f"Strategy: {state['current_strategy']} | Task: {state['current_task']}")
    return state
