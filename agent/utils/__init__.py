from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(text: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in text)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "product"
