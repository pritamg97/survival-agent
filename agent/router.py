import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.config import CONFIG
from agent.logger import LOGGER

# task_type -> ordered provider priority. Mistral leads everywhere (6 keys,
# highest configured quota) with Google AI Studio as the immediate fallback;
# nvidia-nim/groq/openrouter-free only enter the mix once those keys exist —
# unconfigured providers are simply absent from self.providers, so they're
# skipped automatically rather than needing a separate flag.
TASK_PRIORITY: Dict[str, List[str]] = {
    "coding": ["mistral", "google-ai-studio", "nvidia-nim", "groq", "openrouter-free"],
    "research": ["mistral", "google-ai-studio", "nvidia-nim", "groq"],
    "fast": ["mistral", "google-ai-studio", "groq"],
    "reasoning": ["mistral", "google-ai-studio", "nvidia-nim"],
    "marketing": ["mistral", "google-ai-studio", "openrouter-free"],
    "emergency": ["mistral", "google-ai-studio", "nvidia-nim"],
    "general": ["mistral", "google-ai-studio", "nvidia-nim", "groq"],
}


@dataclass
class ProviderConfig:
    name: str
    api_key: str
    base_url: str
    models: List[str]
    rate_limit_rpm: int = 60
    rate_limit_rpd: int = 1000
    current_requests_today: int = 0
    last_request_time: float = 0.0
    failures_in_row: int = 0
    disabled_until: float = 0.0
    total_tokens_used: int = 0
    _day_reset: float = field(default_factory=lambda: time.time())


class ZeroCostRouter:
    def __init__(self):
        self.providers: Dict[str, ProviderConfig] = {}
        self._clients: Dict[str, OpenAI] = {}
        self._cache: Dict[str, str] = {}
        self._cache_order: List[str] = []
        self._init_providers()

    def _init_providers(self) -> None:
        for i, key in enumerate(CONFIG.MISTRAL_KEYS, start=1):
            self.providers[f"mistral-{i}"] = ProviderConfig(
                name=f"mistral-{i}",
                api_key=key,
                base_url="https://api.mistral.ai/v1",
                models=["mistral-small-latest"],
                rate_limit_rpm=60,
                rate_limit_rpd=500,
            )
        if CONFIG.GOOGLE_AI_STUDIO_KEY:
            # Google AI Studio's per-model quota varies wildly by tier — check
            # your own console (aistudio.google.com/app/apikey -> rate limits)
            # and set GOOGLE_AI_STUDIO_MODEL to whichever "Flash Lite" tier
            # shows the highest requests-per-day; regular Flash tiers are often
            # capped much lower (e.g. 20 RPD) than the Flash Lite tier (e.g. 500 RPD).
            self.providers["google-ai-studio"] = ProviderConfig(
                name="google-ai-studio",
                api_key=CONFIG.GOOGLE_AI_STUDIO_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai",
                models=[CONFIG.GOOGLE_AI_STUDIO_MODEL],
                rate_limit_rpm=CONFIG.GOOGLE_AI_STUDIO_RPM,
                rate_limit_rpd=CONFIG.GOOGLE_AI_STUDIO_RPD,
            )
        if CONFIG.NVIDIA_NIM_KEY:
            self.providers["nvidia-nim"] = ProviderConfig(
                name="nvidia-nim",
                api_key=CONFIG.NVIDIA_NIM_KEY,
                base_url="https://integrate.api.nvidia.com/v1",
                models=["meta/llama-3.1-70b-instruct"],
                rate_limit_rpm=40,
                rate_limit_rpd=5000,
            )
        if CONFIG.GROQ_API_KEY:
            self.providers["groq"] = ProviderConfig(
                name="groq",
                api_key=CONFIG.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
                models=["llama-3.1-8b-instant"],
                rate_limit_rpm=30,
                rate_limit_rpd=14400,
            )
        if CONFIG.OPENROUTER_KEY:
            self.providers["openrouter-free"] = ProviderConfig(
                name="openrouter-free",
                api_key=CONFIG.OPENROUTER_KEY,
                base_url="https://openrouter.ai/api/v1",
                models=["meta-llama/llama-3.1-8b-instruct:free"],
                rate_limit_rpm=20,
                rate_limit_rpd=200,
            )
        LOGGER.info(f"ZeroCostRouter initialized with {len(self.providers)} provider(s)")

    def _client_for(self, provider: ProviderConfig) -> OpenAI:
        if provider.name not in self._clients:
            self._clients[provider.name] = OpenAI(api_key=provider.api_key, base_url=provider.base_url)
        return self._clients[provider.name]

    def _is_available(self, provider: ProviderConfig) -> bool:
        now = time.time()
        if now - provider._day_reset > 86400:
            provider.current_requests_today = 0
            provider._day_reset = now
        if now < provider.disabled_until:
            return False
        if provider.current_requests_today >= provider.rate_limit_rpd:
            return False
        min_gap = 60.0 / max(provider.rate_limit_rpm, 1)
        if now - provider.last_request_time < min_gap:
            return False
        return True

    def _mark_success(self, provider: ProviderConfig, tokens: int) -> None:
        provider.failures_in_row = 0
        provider.current_requests_today += 1
        provider.last_request_time = time.time()
        provider.total_tokens_used += tokens

    def _mark_failure(self, provider: ProviderConfig, error: Exception) -> None:
        provider.failures_in_row += 1
        provider.last_request_time = time.time()
        if provider.failures_in_row >= 3:
            backoff = min(60 * (2 ** (provider.failures_in_row - 3)), 3600)
            provider.disabled_until = time.time() + backoff
            LOGGER.warning(f"Provider {provider.name} disabled for {backoff}s after failure: {error}")
        else:
            LOGGER.warning(f"Provider {provider.name} failed: {error}")

    def _get_cache_key(self, messages: List[dict], model: str) -> str:
        payload = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _ordered_candidates(self, task_type: str) -> List[ProviderConfig]:
        """Full priority-ordered candidate list for a task type (not filtered
        by availability — callers walk it and skip/try as appropriate)."""
        priority = TASK_PRIORITY.get(task_type, TASK_PRIORITY["general"])

        candidates: List[ProviderConfig] = []
        mistral_keys = [p for name, p in self.providers.items() if name.startswith("mistral-")]
        random.shuffle(mistral_keys)  # load-balance across the 6 keys

        for family in priority:
            if family == "mistral":
                candidates.extend(mistral_keys)
            elif family in self.providers:
                candidates.append(self.providers[family])
        return candidates

    def get_provider_for_task(
        self, task_type: str = "general", required_quality: str = "standard"
    ) -> Optional[Tuple[OpenAI, ProviderConfig, str]]:
        """Returns the single best available provider right now, without
        attempting a call. call() below is what actually cascades through
        the full candidate list on failure — this is for inspection/spec
        compatibility."""
        for provider in self._ordered_candidates(task_type):
            if self._is_available(provider):
                return self._client_for(provider), provider, provider.models[0]
        return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def _call_provider(self, client: OpenAI, model: str, messages: List[dict], temperature: float, max_tokens: int):
        return client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
        )

    def call(
        self,
        messages: List[dict],
        task_type: str = "general",
        required_quality: str = "standard",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_cache: bool = True,
        state: Optional[dict] = None,
    ) -> str:
        """Tries every candidate provider for this task type, in priority
        order, until one succeeds. Each provider gets its own exponential
        backoff retry internally (_call_provider, 3 attempts) before this
        method gives up on it and cascades to the next — e.g. a Mistral key
        that times out gets retried with backoff on Mistral first, and only
        moves on to Google (or the next Mistral key) once that key's own
        retries are exhausted. Raises only if every candidate fails.

        Pass the running SurvivalState as `state` to have usage recorded into
        it (total_api_calls, provider_usage, total_tokens_used) via
        Metabolism.burn_llm — this router's own per-provider counters
        (current_requests_today etc.) are internal rate-limiting bookkeeping
        only and were never wired into the state the dashboard reads."""
        cache_key = None
        if use_cache and CONFIG.ENABLE_CACHE:
            cache_key = self._get_cache_key(messages, task_type)
            if cache_key in self._cache:
                LOGGER.debug("Router cache hit")
                return self._cache[cache_key]

        candidates = self._ordered_candidates(task_type)
        if not candidates:
            raise RuntimeError(f"No LLM provider configured for task_type={task_type}")

        last_error: Optional[Exception] = None
        for provider in candidates:
            if not self._is_available(provider):
                continue

            client = self._client_for(provider)
            model = provider.models[0]
            try:
                response = self._call_provider(client, model, messages, temperature, max_tokens)
                content = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
                self._mark_success(provider, input_tokens + output_tokens)

                if state is not None:
                    from agent.metabolism import Metabolism

                    Metabolism(state).burn_llm(provider.name, input_tokens, output_tokens, purpose=task_type)

                LOGGER.info(
                    f"LLM call ok: provider={provider.name} model={model} "
                    f"tokens={input_tokens}+{output_tokens} cost=$0"
                )

                if use_cache and CONFIG.ENABLE_CACHE and cache_key:
                    self._cache[cache_key] = content
                    self._cache_order.append(cache_key)
                    if len(self._cache_order) > CONFIG.CACHE_MAX_SIZE:
                        oldest = self._cache_order.pop(0)
                        self._cache.pop(oldest, None)

                return content
            except Exception as e:  # noqa: BLE001
                self._mark_failure(provider, e)
                last_error = e
                LOGGER.warning(f"{provider.name} exhausted its retries — cascading to next provider")
                continue

        raise RuntimeError(
            f"All LLM providers failed or unavailable for task_type={task_type}: {last_error}"
        )

    def get_stats(self) -> dict:
        return {
            "providers": {
                name: {
                    "requests_today": p.current_requests_today,
                    "total_tokens": p.total_tokens_used,
                    "failures_in_row": p.failures_in_row,
                    "disabled_until": p.disabled_until,
                }
                for name, p in self.providers.items()
            },
            "cache_size": len(self._cache),
            "cache_max": CONFIG.CACHE_MAX_SIZE,
        }


ROUTER = ZeroCostRouter()
