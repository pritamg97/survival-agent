from datetime import datetime, timezone
from typing import Optional

from agent.config import CONFIG
from agent.logger import LOGGER
from agent.state import SurvivalState


class AgentDeathException(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class Metabolism:
    """Economic engine. Every action costs money. Bankruptcy = death."""

    def __init__(self, state: SurvivalState):
        self.state = state

    def burn_server(self, hours: Optional[float] = None) -> None:
        hours = CONFIG.CYCLE_INTERVAL_MINUTES / 60 if hours is None else hours
        amount = CONFIG.SERVER_BURN_PER_HOUR * hours
        self._apply(-amount)
        self.state["total_burn"] += amount
        self._log_transaction("burn", amount, "Server burn")
        self._check_death(f"Server burn: ${amount:.4f}")

    def burn_llm(self, provider: str, input_tokens: int, output_tokens: int, purpose: str) -> None:
        # LLM calls are free via the zero-cost router; still track usage.
        self.state["provider_usage"][provider] = self.state["provider_usage"].get(provider, 0) + 1
        self.state["total_api_calls"] += 1
        self.state["total_tokens_used"] += input_tokens + output_tokens
        LOGGER.debug(
            "LLM call",
            extra={
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "purpose": purpose,
                "cost": 0,
            },
        )

    def burn_infra(self, amount: float, description: str) -> None:
        if amount <= 0:
            return
        self._apply(-amount)
        self.state["total_costs"] += amount
        self._log_transaction("cost", amount, description)
        self._check_death(description)

    def revenue(self, amount: float, source: str) -> None:
        if amount <= 0:
            return
        self._apply(amount)
        self.state["total_revenue"] += amount
        self.state["consecutive_failures"] = 0
        self._log_transaction("revenue", amount, source)
        self._check_death(source)

    def get_runway(self) -> float:
        rate = self.state["burn_rate_per_hour"]
        if rate <= 0:
            return float("inf")
        return self.state["bank_balance"] / rate

    def get_daily_burn_rate(self) -> float:
        cutoff = datetime.now(timezone.utc).timestamp() - 24 * 3600
        total = 0.0
        for tx in self.state["transactions"]:
            if tx["type"] in ("cost", "burn"):
                try:
                    ts = datetime.fromisoformat(tx["timestamp"]).timestamp()
                except ValueError:
                    continue
                if ts >= cutoff:
                    total += tx["amount"]
        return total / 24

    def _apply(self, delta: float) -> None:
        self.state["bank_balance"] = round(self.state["bank_balance"] + delta, 6)

    def _log_transaction(self, type_: str, amount: float, description: str) -> None:
        tx = {
            "type": type_,
            "amount": amount,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.state["transactions"].append(tx)
        self.state["transactions"] = self.state["transactions"][-100:]
        LOGGER.info(f"{type_.upper()}: ${amount:.4f} — {description}", extra=tx)

    def _check_death(self, description: str) -> None:
        if self.state["bank_balance"] <= 0 and self.state["alive"]:
            self.state["alive"] = False
            self.state["reason_of_death"] = "BANKRUPTCY"
            LOGGER.error(f"AGENT DIED: bankruptcy triggered by '{description}'")
            raise AgentDeathException("BANKRUPTCY")
