import time

from agent.approval import APPROVAL
from agent.config import CONFIG
from agent.logger import LOGGER
from agent.state import SurvivalState


def needs_approval(opportunity: dict, strategy: str) -> bool:
    """Any real-world action taken under the operator's identity requires a
    fresh email approval first. Two independent safety switches gate whether
    there's anything to approve at all:

    - service_arbitrage: only gated when the opportunity is a real, sourced
      listing (has source_url) AND ENABLE_REAL_BIDDING is on. Otherwise it's
      the synthetic/simulated arbitrage path, which has no real-world action.
    - micro_saas / content_farm: gated whenever ENABLE_REAL_DEPLOYMENT is on —
      these are agent-originated (no source_url needed) but still create a
      real Stripe product or publish real content once approved.

    If the relevant switch is off, needs_approval is False and execution falls
    through to the existing simulated behavior unchanged."""
    if strategy == "service_arbitrage":
        return bool(opportunity.get("source_url")) and CONFIG.ENABLE_REAL_BIDDING
    if strategy in ("micro_saas", "content_farm"):
        return CONFIG.ENABLE_REAL_DEPLOYMENT
    return False


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
    strategy = state["current_strategy"]
    if opp and needs_approval(opp, strategy):
        record = APPROVAL.send_request(opp, strategy=strategy)
        state["current_opportunity_approved"] = False
        if record:
            state["pending_approval"] = record
            state["working_memory"].append(
                f"Requested approval ({strategy}): {opp.get('niche')} ({record['token']})"
            )
            LOGGER.info(f"Approval requested: {record['token']} ({strategy})")
        else:
            state["consecutive_failures"] += 1
            state["working_memory"].append("Approval email could not be sent (SMTP not configured?)")
            LOGGER.warning("Approval request failed to send; treating as not approved")

    return state
