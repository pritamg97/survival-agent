import time

from agent.approval import APPROVAL
from agent.config import CONFIG
from agent.logger import LOGGER
from agent.state import SurvivalState


def needs_approval(opportunity: dict, strategy: str) -> bool:
    """A real, sourced opportunity being acted on via service_arbitrage requires
    a fresh email approval before the agent takes any real-world action under
    the operator's identity. If ENABLE_REAL_BIDDING is off, real actions are
    disabled entirely so there's nothing to gate — falls through to the
    existing simulated arbitrage instead."""
    return strategy == "service_arbitrage" and bool(opportunity.get("source_url")) and CONFIG.ENABLE_REAL_BIDDING


def approval_gate(state: SurvivalState) -> SurvivalState:
    """APPROVAL GATE — email the operator before any real-world bid, and wait
    for an explicit reply. Fails closed: no reply, no SMTP/IMAP config, or a
    timeout all resolve to 'not approved'."""
    pending = state.get("pending_approval")

    if pending:
        elapsed_hours = (time.time() - pending["sent_at"]) / 3600
        result = APPROVAL.check_reply(pending["token"])

        if result is True:
            state["current_opportunity_approved"] = True
            state["approval_history"].append({**pending, "resolution": "approved"})
            state["working_memory"].append(f"APPROVED by email: {pending['opportunity'].get('niche')}")
            LOGGER.info(f"Approval granted for token {pending['token']}")
            state["pending_approval"] = None
        elif result is False or elapsed_hours >= CONFIG.APPROVAL_TIMEOUT_HOURS:
            reason = "explicit reject" if result is False else "timed out"
            state["current_opportunity_approved"] = False
            state["approval_history"].append({**pending, "resolution": reason})
            state["working_memory"].append(f"Bid NOT approved ({reason}): {pending['opportunity'].get('niche')}")
            LOGGER.info(f"Approval denied ({reason}) for token {pending['token']}")
            state["pending_approval"] = None
            state["consecutive_failures"] += 1
        else:
            state["current_opportunity_approved"] = False
            state["working_memory"].append(f"Awaiting approval reply (token {pending['token']})...")
        return state

    opp = state["current_opportunities"][0] if state["current_opportunities"] else None
    if opp and needs_approval(opp, state["current_strategy"]):
        record = APPROVAL.send_request(opp)
        state["current_opportunity_approved"] = False
        if record:
            state["pending_approval"] = record
            state["working_memory"].append(f"Requested approval to bid on: {opp.get('niche')} ({record['token']})")
            LOGGER.info(f"Approval requested: {record['token']}")
        else:
            state["consecutive_failures"] += 1
            state["working_memory"].append("Approval email could not be sent (SMTP not configured?)")
            LOGGER.warning("Approval request failed to send; treating as not approved")

    return state
