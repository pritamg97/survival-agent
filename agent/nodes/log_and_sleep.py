import json
import os
import time

from agent.config import CONFIG
from agent.github_state import GITHUB
from agent.logger import LOGGER
from agent.state import SurvivalState


def log_and_sleep(state: SurvivalState, sleep: bool = True) -> SurvivalState:
    """LOG & SLEEP — save state, push to GitHub, sleep until the next cycle."""
    summary = (
        f"Cycle {state['iteration_count']} done: balance=${state['bank_balance']:.2f}, "
        f"strategy={state['current_strategy']}, products={len(state['products'])}"
    )
    state["working_memory"].append(summary)
    state["working_memory"] = state["working_memory"][-CONFIG.WORKING_MEMORY_MAX:]

    pushed = GITHUB.push(dict(state))
    if not pushed:
        os.makedirs(os.path.dirname(CONFIG.STATE_FILE) or ".", exist_ok=True)
        with open(CONFIG.STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
        LOGGER.info(f"State saved locally to {CONFIG.STATE_FILE}")

    LOGGER.info(
        f"VITALS: balance=${state['bank_balance']:.2f} runway={state['runway_hours']:.1f}h "
        f"products={len(state['products'])} revenue=${state['total_revenue']:.2f} "
        f"alive={state['alive']}"
    )

    if state["alive"] and sleep:
        time.sleep(CONFIG.CYCLE_INTERVAL_MINUTES * 60)

    return state
