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


def _list(name: str, default: tuple) -> tuple:
    val = os.environ.get(name)
    if val is None:
        return default
    return tuple(v.strip() for v in val.split(",") if v.strip())


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

    # Opportunity discovery — read-only signal sources for opportunity_scan.
    # Reddit: create a free "script" app at reddit.com/prefs/apps (no card required).
    # If client id/secret are unset, falls back to Reddit's unauthenticated public
    # JSON endpoints (lower rate limits, still free, still no key needed).
    REDDIT_CLIENT_ID: str = os.environ.get("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.environ.get("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = os.environ.get("REDDIT_USER_AGENT", "survival-agent/1.0")
    OPPORTUNITY_SUBREDDITS: tuple = field(default_factory=lambda: _list(
        "OPPORTUNITY_SUBREDDITS",
        ("forhire", "slavelabour", "SaaS", "Entrepreneur", "sideproject"),
    ))
    # Upwork has no self-serve public jobs-search API. This reads a saved-search
    # RSS feed URL you generate from your own Upwork account (Upwork > Saved
    # Searches > RSS) — no scraping, no key, ToS-compliant. Optional.
    UPWORK_RSS_URL: str = os.environ.get("UPWORK_RSS_URL", "")

    # Human-in-the-loop approval gate: before the agent takes any real-world
    # action under your identity (currently: posting a Reddit reply offering
    # services), it emails you the opportunity and waits for a reply containing
    # APPROVE/REJECT + the token. No SMTP/IMAP config -> the gate can never
    # resolve, so gated actions simply never fire (fail closed, not open).
    EMAIL_SMTP_HOST: str = os.environ.get("EMAIL_SMTP_HOST", "")
    EMAIL_SMTP_PORT: int = _int("EMAIL_SMTP_PORT", 587)
    EMAIL_SMTP_USER: str = os.environ.get("EMAIL_SMTP_USER", "")
    EMAIL_SMTP_PASSWORD: str = os.environ.get("EMAIL_SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.environ.get("EMAIL_FROM", "")
    EMAIL_IMAP_HOST: str = os.environ.get("EMAIL_IMAP_HOST", "")
    EMAIL_IMAP_PORT: int = _int("EMAIL_IMAP_PORT", 993)
    EMAIL_IMAP_USER: str = os.environ.get("EMAIL_IMAP_USER", "")
    EMAIL_IMAP_PASSWORD: str = os.environ.get("EMAIL_IMAP_PASSWORD", "")
    APPROVAL_EMAIL_TO: str = os.environ.get("APPROVAL_EMAIL_TO", "")
    APPROVAL_TIMEOUT_HOURS: float = _float("APPROVAL_TIMEOUT_HOURS", 24.0)

    # Master safety switch for any real-world action taken under your identity
    # (e.g. posting a real Reddit comment). Defaults to False. Even when True,
    # every gated action STILL requires a fresh per-opportunity email approval —
    # this flag alone does not let the agent act.
    ENABLE_REAL_BIDDING: bool = _bool("ENABLE_REAL_BIDDING", False)

    # Write-scope Reddit credentials, only needed if ENABLE_REAL_BIDDING=true.
    # Separate from REDDIT_CLIENT_ID/SECRET's read-only app-only usage above.
    REDDIT_USERNAME: str = os.environ.get("REDDIT_USERNAME", "")
    REDDIT_PASSWORD: str = os.environ.get("REDDIT_PASSWORD", "")

    def get_monthly_target(self, month: int) -> float:
        if month in self.MONTHLY_TARGETS:
            return self.MONTHLY_TARGETS[month]
        return self.MONTHLY_TARGETS[max(self.MONTHLY_TARGETS)]

    @property
    def cycle_burn(self) -> float:
        return self.SERVER_BURN_PER_HOUR * self.CYCLE_INTERVAL_MINUTES / 60


CONFIG = Config()
