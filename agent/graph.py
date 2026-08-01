from datetime import datetime, timezone

from langgraph.graph import END, StateGraph

from agent.logger import LOGGER
from agent.nodes.collect_revenue import collect_revenue
from agent.nodes.execute_build import execute_build
from agent.nodes.execute_content import execute_content
from agent.nodes.execute_service import execute_service
from agent.nodes.heartbeat import heartbeat
from agent.nodes.log_and_sleep import log_and_sleep
from agent.nodes.opportunity_scan import opportunity_scan
from agent.nodes.pivot_or_die import pivot_or_die
from agent.nodes.strategy_select import strategy_select
from agent.state import SurvivalState


def kill_switch(state: SurvivalState) -> SurvivalState:
    """Terminal node: agent is permanently dead. Writes the death certificate."""
    state["death_certificate"] = {
        "cause": state.get("reason_of_death", "UNKNOWN"),
        "time_of_death": datetime.now(timezone.utc).isoformat(),
        "iterations_survived": state["iteration_count"],
        "days_survived": state["day_count"],
        "month_reached": state["month_count"],
        "total_revenue": state["total_revenue"],
        "total_costs": state["total_costs"],
        "total_burn": state["total_burn"],
        "final_balance": state["bank_balance"],
        "products_built": len(state["products"]),
    }
    LOGGER.error(f"KILL SWITCH: {state['death_certificate']}")

    from agent.github_state import GITHUB

    GITHUB.push(dict(state))
    return state


def _after_heartbeat(state: SurvivalState) -> str:
    return "kill_switch" if not state["alive"] else "opportunity_scan"


def _route_strategy(state: SurvivalState) -> str:
    strategy = state.get("current_strategy")
    if strategy == "micro_saas":
        return "execute_build"
    if strategy == "service_arbitrage":
        return "execute_service"
    return "execute_content"


def _after_pivot(state: SurvivalState) -> str:
    return "kill_switch" if not state["alive"] else "log_and_sleep"


def build_graph(sleep: bool = True):
    graph = StateGraph(SurvivalState)

    graph.add_node("heartbeat", heartbeat)
    graph.add_node("opportunity_scan", opportunity_scan)
    graph.add_node("strategy_select", strategy_select)
    graph.add_node("execute_build", execute_build)
    graph.add_node("execute_service", execute_service)
    graph.add_node("execute_content", execute_content)
    graph.add_node("collect_revenue", collect_revenue)
    graph.add_node("pivot_or_die", pivot_or_die)
    graph.add_node("log_and_sleep", lambda state: log_and_sleep(state, sleep=sleep))
    graph.add_node("kill_switch", kill_switch)

    graph.set_entry_point("heartbeat")
    graph.add_conditional_edges(
        "heartbeat", _after_heartbeat, {"kill_switch": "kill_switch", "opportunity_scan": "opportunity_scan"}
    )
    graph.add_edge("opportunity_scan", "strategy_select")
    graph.add_conditional_edges(
        "strategy_select",
        _route_strategy,
        {
            "execute_build": "execute_build",
            "execute_service": "execute_service",
            "execute_content": "execute_content",
        },
    )
    graph.add_edge("execute_build", "collect_revenue")
    graph.add_edge("execute_service", "collect_revenue")
    graph.add_edge("execute_content", "collect_revenue")
    graph.add_edge("collect_revenue", "pivot_or_die")
    graph.add_conditional_edges(
        "pivot_or_die", _after_pivot, {"kill_switch": "kill_switch", "log_and_sleep": "log_and_sleep"}
    )
    graph.add_edge("log_and_sleep", "heartbeat")
    graph.add_edge("kill_switch", END)

    return graph.compile()
