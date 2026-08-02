from typing import Optional

from agent.integrations.vercel_client import deploy_static_page
from agent.logger import LOGGER
from agent.router import ROUTER
from agent.utils import slugify


def publish_backlink_article(product: dict, state: Optional[dict] = None) -> Optional[str]:
    """Writes and deploys a short article about the problem `product` solves,
    linking back to its live page — a promotion channel that doesn't depend
    on any third-party platform's API or goodwill (nothing to get banned
    from, nothing that breaks when a form changes). Slow — organic/SEO
    traffic takes time to build — but robust. Returns the article's live URL,
    or None if generation or deploy fails."""
    prompt = (
        f"Write a short, genuine-sounding blog post (a title plus 3-4 short paragraphs) about "
        f"the problem this solves: {product.get('description') or product.get('name')}. "
        f"Write it from the perspective of someone who found a tool for this problem. "
        f"Naturally mention and link to {product['url']} as the tool, using a real <a href> tag. "
        "Return a complete, self-contained single-file HTML page with inline CSS. "
        "Return ONLY the raw HTML — no markdown fences, no commentary."
    )
    try:
        html = ROUTER.call([{"role": "user", "content": prompt}], task_type="marketing", max_tokens=1800, state=state)
    except RuntimeError as e:
        LOGGER.warning(f"Backlink article generation failed for '{product.get('name')}': {e}")
        return None

    live_url = deploy_static_page(f"about-{slugify(product.get('name', 'product'))}", html)
    if not live_url:
        LOGGER.warning(f"Backlink article deploy failed for '{product.get('name')}'")
        return None

    LOGGER.info(f"Backlink article published for '{product.get('name')}': {live_url}")
    return live_url
