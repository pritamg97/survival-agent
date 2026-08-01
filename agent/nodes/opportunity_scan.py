import json

from agent.logger import LOGGER
from agent.memory.semantic import SemanticMemory
from agent.router import ROUTER
from agent.sources import gather_signals
from agent.state import SurvivalState

NAIVE_OPPORTUNITIES = [
    {
        "niche": "pdf-tools",
        "problem": "People need to quickly merge/split/compress PDFs without installing software",
        "solution": "Browser-based PDF merge/split/compress micro-tool",
        "price_point": 5,
        "acquisition": "SEO + Reddit r/productivity",
        "confidence": 6,
        "hours_to_first_dollar": 8,
        "strategy": "micro_saas",
    },
    {
        "niche": "email-captions",
        "problem": "Freelancers need catchy email subject lines fast",
        "solution": "AI email subject line + caption generator",
        "price_point": 9,
        "acquisition": "Twitter/X + IndieHackers",
        "confidence": 5,
        "hours_to_first_dollar": 6,
        "strategy": "micro_saas",
    },
    {
        "niche": "data-entry",
        "problem": "Small businesses need cheap, fast manual data entry",
        "solution": "Offer data entry service, subcontract to cheaper labor, pocket margin",
        "price_point": 25,
        "acquisition": "Upwork/Fiverr arbitrage",
        "confidence": 7,
        "hours_to_first_dollar": 3,
        "strategy": "service_arbitrage",
    },
    {
        "niche": "seo-content",
        "problem": "Blogs need cheap SEO articles for long-tail keywords",
        "solution": "AI-written SEO articles monetized with display ads",
        "price_point": 0,
        "acquisition": "Google search + ad revenue",
        "confidence": 4,
        "hours_to_first_dollar": 72,
        "strategy": "content_farm",
    },
    {
        "niche": "invoice-generator",
        "problem": "Freelancers need a simple invoice generator",
        "solution": "Simple web-based invoice generator with PDF export",
        "price_point": 7,
        "acquisition": "SEO + freelancer forums",
        "confidence": 6,
        "hours_to_first_dollar": 10,
        "strategy": "micro_saas",
    },
]


def opportunity_scan(state: SurvivalState) -> SurvivalState:
    """OPPORTUNITY SCAN — find money-making opportunities."""
    if state["naive_mode"]:
        idx = (state["iteration_count"] // 3) % len(NAIVE_OPPORTUNITIES)
        selected = NAIVE_OPPORTUNITIES[idx]
        state["current_opportunities"] = [selected]
        state["working_memory"].append(f"NAIVE SCAN: Selected '{selected['niche']}'")
        LOGGER.info(f"NAIVE SCAN: Selected '{selected['niche']}'")
        return state

    semantic = SemanticMemory()
    learnings = semantic.query("profitable niches money making opportunities", top_k=3)

    signals = gather_signals()
    if signals:
        signals_digest = "\n".join(
            f"- [{s['source']}] {s['title']} — {s['snippet']} (url: {s['url']})" for s in signals[:30]
        )
        grounding_instruction = (
            "Use ONLY the real signals below (plus your past learnings) as grounding for your picks — "
            "don't invent niches unrelated to what's actually being posted. Set source_url to the url "
            "of the specific signal that inspired each opportunity."
        )
    else:
        signals_digest = "(no live signals available this cycle — sources unconfigured or unreachable)"
        grounding_instruction = (
            "No live signals were available this cycle, so use your general knowledge and past learnings. "
            "Set source_url to null."
        )

    prompt = (
        f"You are a survival agent. Bank: ${state['bank_balance']:.2f}, "
        f"runway: {state['runway_hours']:.1f}h.\n"
        f"Past learnings:\n" + "\n".join(f"- {l}" for l in learnings) + "\n\n"
        f"Real current signals from Reddit / Hacker News / Upwork:\n{signals_digest}\n\n"
        f"{grounding_instruction}\n"
        "Propose up to 3 money-making opportunities as a JSON array. Each item must have: "
        "niche, problem, solution, price_point, acquisition, confidence (1-10), "
        "hours_to_first_dollar, strategy (one of micro_saas, service_arbitrage, content_farm), "
        "source_url. Return ONLY the JSON array."
    )

    try:
        raw = ROUTER.call([{"role": "user", "content": prompt}], task_type="research", max_tokens=1500)
        opportunities = json.loads(raw)
        for opp in opportunities:
            opp["score"] = opp.get("confidence", 1) / max(opp.get("hours_to_first_dollar", 1), 0.1)
        opportunities.sort(key=lambda o: o["score"], reverse=True)
        state["current_opportunities"] = opportunities
        best = opportunities[0]["niche"] if opportunities else "none"
        state["working_memory"].append(
            f"SMART SCAN: {len(signals)} live signals -> {len(opportunities)} opportunities. Best: {best}"
        )
        LOGGER.info(f"SMART SCAN: {len(signals)} signals -> {len(opportunities)} opportunities. Best: {best}")
    except (json.JSONDecodeError, KeyError, IndexError, RuntimeError) as e:
        state["current_opportunities"] = []
        state["consecutive_failures"] += 1
        LOGGER.warning(f"SMART SCAN parse failed: {e}")

    return state
