from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict


@dataclass
class Product:
    name: str
    description: str
    price: float
    status: str = "live"  # live | dead | building
    url: str = ""
    customers: int = 0
    revenue: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Transaction:
    type: str  # cost | revenue | burn
    amount: float
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


class SurvivalState(TypedDict):
    alive: bool
    bank_balance: float
    burn_rate_per_hour: float
    runway_hours: float
    iteration_count: int
    day_count: int
    month_count: int
    month_start_balance: float
    month_start_revenue: float
    monthly_target: float
    cycle_start_time: str
    last_day_logged: int
    current_strategy: Optional[str]
    current_task: Optional[str]
    current_opportunities: List[dict]
    emergency_mode: bool
    panic_mode: bool
    naive_mode: bool
    products: List[dict]
    transactions: List[dict]
    total_revenue: float
    total_costs: float
    total_burn: float
    consecutive_failures: int
    working_memory: List[str]
    episodic_summary: str
    semantic_facts: List[dict]
    skills_available: List[str]
    reason_of_death: Optional[str]
    death_certificate: Optional[dict]
    langsmith_run_id: Optional[str]
    provider_usage: Dict[str, int]
    total_api_calls: int
    total_tokens_used: int
    pending_approval: Optional[dict]
    current_opportunity_approved: bool
    approval_history: List[dict]


def create_initial_state(seed_budget: float, month_1_target: float) -> SurvivalState:
    now = datetime.now(timezone.utc).isoformat()
    return SurvivalState(
        alive=True,
        bank_balance=seed_budget,
        burn_rate_per_hour=0.0,
        runway_hours=float("inf"),
        iteration_count=0,
        day_count=0,
        month_count=1,
        month_start_balance=seed_budget,
        month_start_revenue=0.0,
        monthly_target=month_1_target,
        cycle_start_time=now,
        last_day_logged=-1,
        current_strategy=None,
        current_task=None,
        current_opportunities=[],
        emergency_mode=False,
        panic_mode=False,
        naive_mode=True,
        products=[],
        transactions=[],
        total_revenue=0.0,
        total_costs=0.0,
        total_burn=0.0,
        consecutive_failures=0,
        working_memory=[],
        episodic_summary="",
        semantic_facts=[],
        skills_available=[],
        reason_of_death=None,
        death_certificate=None,
        langsmith_run_id=None,
        provider_usage={},
        total_api_calls=0,
        total_tokens_used=0,
        pending_approval=None,
        current_opportunity_approved=False,
        approval_history=[],
    )
