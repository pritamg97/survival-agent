import random

from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.state import SurvivalState
from agent.utils import safe_float


def execute_service(state: SurvivalState) -> SurvivalState:
    """EXECUTE SERVICE ARBITRAGE — act as middleman between client and cheaper worker.

    If the current opportunity is a real, sourced listing that just cleared the
    email approval gate, this posts a real reply on that thread instead of
    simulating an outcome. Otherwise (synthetic panic/emergency tasks, or real
    bidding not approved/enabled) it falls back to the original simulated
    close-rate roll."""
    if state["current_strategy"] != "service_arbitrage":
        return state

    opportunity = state["current_opportunities"][0] if state["current_opportunities"] else None
    if opportunity and opportunity.get("source_url") and state.get("current_opportunity_approved"):
        return _execute_real_bid(state, opportunity)

    return _execute_simulated(state)


def _execute_real_bid(state: SurvivalState, opportunity: dict) -> SurvivalState:
    from agent.actions.reddit_bid import post_bid_comment
    from agent.integrations.stripe_client import create_payment_link

    price = safe_float(opportunity.get("price_point"), 25.0)
    link = create_payment_link(f"Service: {opportunity.get('niche', 'job')}", price)

    payment_line = f" Pay here when you're happy with the work: {link['url']}" if link else ""
    message = (
        f"Hi — I can help with this: {opportunity.get('solution')}. "
        f"Rate: ${price:.2f}.{payment_line} Reply here if interested."
    )
    posted = post_bid_comment(opportunity["source_url"], message)
    state["current_opportunity_approved"] = False  # consume the one-time approval

    if posted:
        state["working_memory"].append(f"Posted real bid on {opportunity['source_url']}")
        LOGGER.info(f"Posted real bid on {opportunity['source_url']}")
        if link:
            state["service_bids"].append(
                {
                    "niche": opportunity.get("niche"),
                    "source_url": opportunity["source_url"],
                    "price": price,
                    "stripe_payment_link_id": link["payment_link_id"],
                    "stripe_payment_link_url": link["url"],
                    "stripe_seen_sessions": [],
                    "posted_at": state["cycle_start_time"],
                }
            )
        else:
            state["working_memory"].append("Note: bid posted without a payment link (Stripe not configured)")
    else:
        state["consecutive_failures"] += 1
        state["working_memory"].append(f"Real bid post failed on {opportunity['source_url']}")
        LOGGER.warning(f"Real bid post failed on {opportunity['source_url']}")

    return state


def _execute_simulated(state: SurvivalState) -> SurvivalState:
    metabolism = Metabolism(state)
    close_rate = 0.15 if state["panic_mode"] else 0.30

    if random.random() < close_rate:
        revenue = round(random.uniform(15, 50), 2)
        worker_cost = round(revenue * random.uniform(0.50, 0.70), 2)
        try:
            metabolism.burn_infra(worker_cost, "Service arbitrage: paid worker")
            metabolism.revenue(revenue, "Service arbitrage: client payment")
        except AgentDeathException:
            return state
        profit = revenue - worker_cost
        state["working_memory"].append(f"Service arbitrage WIN: revenue=${revenue:.2f}, profit=${profit:.2f}")
        LOGGER.info(f"Service arbitrage WIN: revenue=${revenue:.2f}, profit=${profit:.2f}")
    else:
        state["consecutive_failures"] += 1
        state["working_memory"].append("Service arbitrage: no client this cycle")
        LOGGER.info("Service arbitrage: miss")

    return state
