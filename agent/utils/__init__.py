import json
import re
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _try_parse(candidate: str):
    try:
        json.loads(candidate)
        return candidate
    except (ValueError, TypeError):
        return None


def extract_json(text: str) -> str:
    """Strips markdown code fences models commonly wrap JSON in (```json ... ```)
    despite being told to return raw JSON, plus surrounding whitespace/prose.
    Also repairs the single most common array mistake — the model writes
    several {...} objects meant to be array elements but drops one (or both)
    of the wrapping [ ] brackets, e.g. '{...}, {...}, {...}]' with no leading
    '[' — by trying bracket-wrapped variants before falling back to slicing
    between the first { or [ and the matching last }/]."""
    cleaned = _FENCE_RE.sub("", text).strip()

    for candidate in (
        cleaned,
        f"[{cleaned}]" if cleaned.startswith("{") else None,
        f"[{cleaned}" if cleaned.startswith("{") and cleaned.endswith("]") else None,
        f"{cleaned}]" if cleaned.startswith("[") and not cleaned.endswith("]") else None,
    ):
        if candidate is None:
            continue
        fixed = _try_parse(candidate)
        if fixed is not None:
            return fixed

    start_candidates = [i for i in (cleaned.find("{"), cleaned.find("[")) if i != -1]
    if not start_candidates:
        return cleaned
    start = min(start_candidates)
    end_char = "}" if cleaned[start] == "{" else "]"
    end = cleaned.rfind(end_char)
    if end == -1 or end < start:
        return cleaned
    sliced = cleaned[start : end + 1]

    if sliced.startswith("{"):
        # Prefer the bare object if it's already valid on its own (a caller
        # expecting a single object, like execute_build's spec parsing, needs
        # this — don't force-wrap a perfectly good single object into a
        # 1-element array). Only wrap as a last resort, when the slice alone
        # doesn't parse (e.g. multiple concatenated top-level objects).
        bare = _try_parse(sliced)
        if bare is not None:
            return bare
        wrapped = _try_parse(f"[{sliced}]")
        if wrapped is not None:
            return wrapped

    return sliced


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
