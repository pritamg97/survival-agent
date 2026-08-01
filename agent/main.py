import json
import os
import sys

from agent.config import CONFIG
from agent.github_state import GITHUB
from agent.graph import build_graph
from agent.logger import LOGGER
from agent.state import create_initial_state


def load_or_create_state():
    if os.path.exists(CONFIG.STATE_FILE):
        LOGGER.info(f"Resuming from local state file {CONFIG.STATE_FILE}")
        with open(CONFIG.STATE_FILE, "r") as f:
            return json.load(f)

    remote = GITHUB.pull()
    if remote:
        LOGGER.info("Resuming from GitHub state")
        return remote

    LOGGER.info("No prior state found — spawning a new agent")
    return create_initial_state(CONFIG.SEED_BUDGET, CONFIG.get_monthly_target(1))


def main() -> None:
    state = load_or_create_state()

    if not state.get("alive", True):
        LOGGER.error("Loaded state is already dead. Refusing to resurrect. Delete state to spawn a new agent.")
        sys.exit(1)

    LOGGER.info(
        f"SURVIVAL AGENT starting: balance=${state['bank_balance']:.2f}, "
        f"month={state['month_count']}, target=${state['monthly_target']:.2f}"
    )

    graph = build_graph(sleep=True)

    try:
        graph.invoke(state, config={"recursion_limit": 10_000_000})
    except KeyboardInterrupt:
        LOGGER.info("Received shutdown signal, state already persisted at last cycle boundary.")
        sys.exit(0)


if __name__ == "__main__":
    main()
