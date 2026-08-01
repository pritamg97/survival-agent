import re
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(text: str) -> str:
    """Strips markdown code fences models commonly wrap JSON in (```json ... ```)
    despite being told to return raw JSON, plus surrounding whitespace/prose.
    Falls back to slicing between the first { or [ and the matching last
    }/] if the whole string still isn't clean JSON."""
    cleaned = _FENCE_RE.sub("", text).strip()
    try:
        import json

        json.loads(cleaned)
        return cleaned
    except (ValueError, TypeError):
        pass

    start_candidates = [i for i in (cleaned.find("{"), cleaned.find("[")) if i != -1]
    if not start_candidates:
        return cleaned
    start = min(start_candidates)
    end_char = "}" if cleaned[start] == "{" else "]"
    end = cleaned.rfind(end_char)
    if end == -1 or end < start:
        return cleaned
    return cleaned[start : end + 1]


def safe_float(value, default: float = 0.0) -> float:
    """Coerces a possibly-messy LLM-provided value into a float instead of
    raising. Models routinely return numeric fields as '$9/month', '9.99',
    'Free', or similar despite being told to return a plain number — this
    pulls the first numeric substring out, or falls back to default."""
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return default
    match = re.search(r"-?\d+(\.\d+)?", str(value))
    if not match:
        return default
    try:
        return float(match.group())
    except ValueError:
        return default


def slugify(text: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in text)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "product"
