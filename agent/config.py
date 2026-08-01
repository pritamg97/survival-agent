import os
from dataclasses import dataclass, field
from typing import Dict, Optional

from dotenv import load_dotenv

load_dotenv()


def _float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    SEED_BUDGET: float = _float("SEED_BUDGET", 100.00)
    MONTHLY_TARGETS: Dict[int, float] = field(default_factory=lambda: {
        1: _float("MONTH_1_TARGET", 10.00),
        2: _float("MONTH_2_TARGET", 50.00),
        3: _float("MONTH_3_TARGET", 200.00),
        4: _float("MONTH_4_TARGET", 500.00),
        5: _float("MONTH_5_TARGET", 1000.00),
    })
    SERVER_BURN_PER_HOUR: float = _float("SERVER_BURN_PER_HOUR", 0.15)
    CYCLE_INTERVAL_MINUTES: int = _int("CYCLE_INTERVAL_MINUTES", 15)
    MAX_CONSECUTIVE_FAILURES: int = _int("MAX_CONSECUTIVE_FAILURES", 5)
    EMERGENCY_RUNWAY_HOURS: float = _float("EMERGENCY_RUNWAY_HOURS", 48.0)
    PANIC_RUNWAY_HOURS: float = _float("PANIC_RUNWAY_HOURS", 12.0)

    GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
    GITHUB_REPO: str = os.environ.get("GITHUB_REPO", "")
    GITHUB_BRANCH: str = os.environ.get("GITHUB_BRANCH", "main")

    LANGSMITH_API_KEY: str = os.environ.get("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.environ.get("LANGSMITH_PROJECT", "survival-agent")
    LANGSMITH_TRACING: bool = _bool("LANGSMITH_TRACING", False)

    STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.environ.get("LOG_FILE", "logs/survival-agent.log")

    WORKING_MEMORY_MAX: int = _int("WORKING_MEMORY_MAX", 20)
    EPISODIC_DB_PATH: str = os.environ.get("EPISODIC_DB_PATH", "state/episodes.json")
    SEMANTIC_DB_PATH: str = os.environ.get("SEMANTIC_DB_PATH", "state/semantic.json")
    SKILLS_DIR: str = os.environ.get("SKILLS_DIR", "state/skills")
    STATE_FILE: str = os.environ.get("STATE_FILE", "state/state.json")

    ENABLE_CACHE: bool = _bool("ENABLE_CACHE", True)
    CACHE_MAX_SIZE: int = _int("CACHE_MAX_SIZE", 1000)

    MISTRAL_KEYS: tuple = field(default_factory=lambda: tuple(
        k for k in (
            os.environ.get(f"MISTRAL_KEY_{i}", "") for i in range(1, 7)
        ) if k
    ))
    GOOGLE_AI_STUDIO_KEY: str = os.environ.get("GOOGLE_AI_STUDIO_KEY", "")
    NVIDIA_NIM_KEY: str = os.environ.get("NVIDIA_NIM_KEY", "")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    OPENROUTER_KEY: str = os.environ.get("OPENROUTER_KEY", "")

    def get_monthly_target(self, month: int) -> float:
        if month in self.MONTHLY_TARGETS:
            return self.MONTHLY_TARGETS[month]
        return self.MONTHLY_TARGETS[max(self.MONTHLY_TARGETS)]

    @property
    def cycle_burn(self) -> float:
        return self.SERVER_BURN_PER_HOUR * self.CYCLE_INTERVAL_MINUTES / 60


CONFIG = Config()
