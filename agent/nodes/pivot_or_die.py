from datetime import datetime, timezone

from agent.config import CONFIG
from agent.logger import LOGGER
from agent.memory.episodic import EpisodicMemory
from agent.state import SurvivalState


def _evaluate_product_trials(state: SurvivalState) -> None:
    """Kills real products that have had their full PRODUCT_TRIAL_DAYS window
    live with zero real revenue — frees the niche (via execute_build's dedupe
    guard) so the agent tries something else. Only applies to real
    (Stripe-backed) products; simulated ones already cycle via the
    consecutive-failures pivot above, and a slow-starting real product still
    gets its complete trial window before being judged."""
    now = datetime.now(timezone.utc).timestamp()
    for product in state["products"]:
        if product.get("status") != "live" or not product.get("real") or not product.get("stripe_payment_link_id"):
            continue
        try:
            created = datetime.fromisoformat(product["created_at"]).timestamp()
        except (KeyError, ValueError):
            continue
        age_days = (now - created) / 86400
        if age_days >= CONFIG.PRODUCT_TRIAL_DAYS and product.get("revenue", 0) <= 0:
            product["status"] = "dead"
            state["working_memory"].append(
                f"Trial ended: '{product['name']}' killed after {age_days:.0f}d with $0 revenue"
            )
            LOGGER.info(f"Trial ended: '{product['name']}' killed after {age_days:.0f}d with $0 revenue")


def pivot_or_die(state: SurvivalState) -> SurvivalState:
    """PIVOT OR DIE — check bankruptcy, handle failures, evaluate product
    trials, log daily events."""
    if state["bank_balance"] <= 0:
        state["alive"] = False
        state["reason_of_death"] = "BANKRUPTCY"
        LOGGER.error("AGENT DIED: bankruptcy")
        return state

    _evaluate_product_trials(state)

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
            episodic.compress_day(state=state)
            state["episodic_summary"] = episodic.get_recent_summary()

    return state
