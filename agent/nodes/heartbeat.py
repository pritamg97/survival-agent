from datetime import datetime, timezone

from agent.config import CONFIG
from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.state import SurvivalState


def heartbeat(state: SurvivalState) -> SurvivalState:
    """HEARTBEAT CHECK — the agent checks its own pulse every cycle."""
    metabolism = Metabolism(state)

    try:
        metabolism.burn_server()
    except AgentDeathException:
        return state

    daily_burn = metabolism.get_daily_burn_rate()
    state["burn_rate_per_hour"] = daily_burn if daily_burn > 0 else CONFIG.SERVER_BURN_PER_HOUR
    state["runway_hours"] = metabolism.get_runway()

    cycle_start = datetime.fromisoformat(state["cycle_start_time"])
    days_elapsed = (datetime.now(timezone.utc) - cycle_start).days

    if days_elapsed >= 30:
        month_revenue = state["total_revenue"] - state["month_start_revenue"]
        if month_revenue < state["monthly_target"]:
            state["alive"] = False
            state["reason_of_death"] = "MONTHLY TARGET FAILED"
            LOGGER.error(
                f"AGENT DIED: month {state['month_count']} target ${state['monthly_target']:.2f} "
                f"not met (earned ${month_revenue:.2f})"
            )
            return state

        state["month_count"] += 1
        state["monthly_target"] = CONFIG.get_monthly_target(state["month_count"])
        state["month_start_balance"] = state["bank_balance"]
        state["month_start_revenue"] = state["total_revenue"]
        state["cycle_start_time"] = datetime.now(timezone.utc).isoformat()
        state["naive_mode"] = state["month_count"] == 1
        LOGGER.info(f"Month boundary passed. Now month {state['month_count']}, target ${state['monthly_target']:.2f}")

    was_panic = state["panic_mode"]
    was_emergency = state["emergency_mode"]
    state["emergency_mode"] = state["runway_hours"] < CONFIG.EMERGENCY_RUNWAY_HOURS
    state["panic_mode"] = state["runway_hours"] < CONFIG.PANIC_RUNWAY_HOURS

    if state["panic_mode"] and not was_panic:
        state["working_memory"].append(f"[PANIC] Runway down to {state['runway_hours']:.1f}h!")
    if state["emergency_mode"] and not was_emergency:
        state["working_memory"].append(f"[EMERGENCY] Runway down to {state['runway_hours']:.1f}h.")

    state["iteration_count"] += 1
    return state
