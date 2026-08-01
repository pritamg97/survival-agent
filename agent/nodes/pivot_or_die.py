from datetime import datetime, timezone

from agent.config import CONFIG
from agent.logger import LOGGER
from agent.memory.episodic import EpisodicMemory
from agent.state import SurvivalState


def pivot_or_die(state: SurvivalState) -> SurvivalState:
    """PIVOT OR DIE — check bankruptcy, handle failures, log daily events."""
    if state["bank_balance"] <= 0:
        state["alive"] = False
        state["reason_of_death"] = "BANKRUPTCY"
        LOGGER.error("AGENT DIED: bankruptcy")
        return state

    if state["consecutive_failures"] >= CONFIG.MAX_CONSECUTIVE_FAILURES:
        killed = 0
        for product in state["products"]:
            if product.get("status") == "live" and product.get("customers", 0) == 0:
                product["status"] = "dead"
                killed += 1
        state["current_strategy"] = None
        state["current_task"] = None
        state["current_opportunities"] = []
        state["consecutive_failures"] = 0
        state["working_memory"].append(f"PIVOT: killed {killed} dead product(s), resetting strategy")
        LOGGER.warning(f"PIVOT triggered: killed {killed} dead product(s)")

    today = datetime.now(timezone.utc).timetuple().tm_yday
    if today != state["last_day_logged"]:
        state["day_count"] += 1
        state["last_day_logged"] = today

        cutoff = datetime.now(timezone.utc).timestamp() - 24 * 3600
        todays_txs = []
        for tx in state["transactions"]:
            try:
                ts = datetime.fromisoformat(tx["timestamp"]).timestamp()
            except ValueError:
                continue
            if ts >= cutoff:
                enriched = dict(tx)
                enriched["strategy"] = state.get("current_strategy")
                todays_txs.append(enriched)

        episodic = EpisodicMemory()
        episodic.record_day(state["day_count"], todays_txs)

        if len(episodic.get_all_episodes()) % 3 == 0:
            episodic.compress_day()
            state["episodic_summary"] = episodic.get_recent_summary()

    return state
