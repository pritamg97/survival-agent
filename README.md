# Survival Agent

An autonomous LangGraph agent that starts with a $100 seed budget and must earn
escalating monthly revenue targets or die permanently. Every action (server time,
infra spend, worker payouts) costs money; every LLM call is routed across free-tier
providers at $0 cost. State is pushed to a GitHub repo every cycle and rendered by a
static Next.js dashboard that polls the raw file.

Full design spec: see the original `SURVIVAL_AGENT_COMPLETE_SPEC.pdf`.

## Layout

- `agent/` — Python LangGraph agent (state machine, metabolism, LLM router, 4-layer memory)
- `ui/` — Next.js dashboard, statically exported and deployed to Vercel/GitHub Pages
- `state/` — persisted state (`state.json`, `episodes.json`, `semantic.json`, `skills/`)

## Quick start

```bash
cd agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # fill in your API keys
python main.py
```

```bash
cd ui
npm install
npm run dev
```

The dashboard reads `https://raw.githubusercontent.com/<user>/<repo>/<branch>/state/state.json`.
Set `NEXT_PUBLIC_GITHUB_USER`, `NEXT_PUBLIC_GITHUB_REPO`, and `NEXT_PUBLIC_GITHUB_BRANCH`
in `ui/.env.local` to point it at your fork. If GitHub push fails (no token/repo
configured), the agent falls back to writing `state/state.json` locally.

## Monthly targets

| Month | Target | Mode |
|---|---|---|
| 1 | $10 | Naive — rotates 5 hardcoded strategies |
| 2 | $50 | Adaptive — uses semantic memory |
| 3 | $200 | Optimized — doubles down on winners |
| 4 | $500 | Professional — builds systems |
| 5 | $1000 | Business — scales |
| 6+ | $1000 | Mature — maintain |

Bank balance `<= 0` or a missed monthly target both mean instant, permanent death:
`alive` flips to `false`, a death certificate is written, and the graph terminates.
