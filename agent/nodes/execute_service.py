import random

from agent.logger import LOGGER
from agent.metabolism import AgentDeathException, Metabolism
from agent.state import SurvivalState


def execute_service(state: SurvivalState) -> SurvivalState:
    """EXECUTE SERVICE ARBITRAGE — act as middleman between client and cheaper worker."""
    if state["current_strategy"] != "service_arbitrage":
        return state

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
