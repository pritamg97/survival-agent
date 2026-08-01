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


def _repair_unescaped_quotes(text: str) -> str:
    """Best-effort repair for a very common LLM JSON mistake: an unescaped
    double-quote inside a string value (models often quote a phrase for
    emphasis — e.g. 'mention "looking for clients" and pitch' — without
    realizing it breaks JSON string boundaries). Walks the text tracking
    whether we're inside a string; a '"' only closes the string if what
    follows (after whitespace) is a JSON structural character (, } ] :) or
    end of input — otherwise it's escaped instead of ending the string.
    A no-op on already-valid JSON (structural quotes are always followed by
    one of those characters)."""
    out = []
    in_string = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n:
            out.append(ch)
            out.append(text[i + 1])
            i += 2
            continue
        if ch == '"':
            if not in_string:
                in_string = True
                out.append(ch)
            else:
                j = i + 1
                while j < n and text[j] in " \t\r\n":
                    j += 1
                if j >= n or text[j] in ",}]:":
                    in_string = False
                    out.append(ch)
                else:
                    out.append('\\"')
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _bracket_variants(candidate: str):
    yield candidate
    if candidate.startswith("{"):
        yield f"[{candidate}]"
        if candidate.endswith("]"):
            yield f"[{candidate}"
    if candidate.startswith("[") and not candidate.endswith("]"):
        yield f"{candidate}]"


def extract_json(text: str) -> str:
    """Strips markdown code fences models commonly wrap JSON in (```json ... ```)
    despite being told to return raw JSON, plus surrounding whitespace/prose.
    Also repairs two of the most common LLM JSON mistakes: dropping one of
    the wrapping [ ] brackets around several {...} objects meant to be array
    elements, and unescaped quotes inside string values — by trying repaired
    variants before falling back to slicing between the first { or [ and the
    matching last }/]."""
    cleaned = _FENCE_RE.sub("", text).strip()

    for base in (cleaned, _repair_unescaped_quotes(cleaned)):
        for candidate in _bracket_variants(base):
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

    for base in (sliced, _repair_unescaped_quotes(sliced)):
        if not base.startswith("{"):
            continue
        # Prefer the bare object if it's already valid on its own (a caller
        # expecting a single object, like execute_build's spec parsing, needs
        # this — don't force-wrap a perfectly good single object into a
        # 1-element array). Only wrap as a last resort, when the slice alone
        # doesn't parse (e.g. multiple concatenated top-level objects).
        bare = _try_parse(base)
        if bare is not None:
            return bare
        wrapped = _try_parse(f"[{base}]")
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
