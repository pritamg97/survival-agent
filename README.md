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

## Opportunity discovery & real-world bidding

`opportunity_scan` (month 2+, "smart mode") pulls real, live signals before asking
the LLM to propose opportunities:

- **Reddit** — newest posts from `OPPORTUNITY_SUBREDDITS` (default: `forhire`,
  `slavelabour`, `SaaS`, `Entrepreneur`, `sideproject`). Works with no config at all
  via Reddit's public JSON endpoints; add `REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`
  (a free "script" app at reddit.com/prefs/apps) for higher rate limits.
- **Hacker News** — freelance/hiring threads via the free, keyless Algolia search API.
- **Upwork** — optional. Upwork has no self-serve jobs-search API, so this reads
  the RSS feed URL of a saved search you generate from your own Upwork account
  (`Saved Searches > RSS`) — no scraping, no key.

Month 1 ("naive mode") ignores all of this and just rotates a hardcoded list, by design.

**The agent never acts on these automatically.** For `service_arbitrage` opportunities
sourced from a real listing, it stops before doing anything and emails you
(`APPROVAL_EMAIL_TO`) with the opportunity details and a one-time token. Nothing
happens until you reply **"APPROVE `<token>`"** (or "REJECT") from that inbox — no
reply within `APPROVAL_TIMEOUT_HOURS` (default 24h) counts as a rejection. This
requires `EMAIL_SMTP_*`/`EMAIL_IMAP_*` config; with Gmail, use an
[App Password](https://myaccount.google.com/apppasswords), not your real password.

Even with the approval granted, real posting is off by default. Set
`ENABLE_REAL_BIDDING=true` and provide `REDDIT_USERNAME`/`REDDIT_PASSWORD` to let
an approved bid post a real, visible comment on the sourced Reddit thread offering
to do the job — under your Reddit account. Two things this does *not* do:
it does not submit real Upwork proposals (no such API exists for self-serve use),
and it does not collect payment automatically — a real bid just records the
outreach in `working_memory`; no Stripe/payment wiring exists yet, so any money
that actually comes in from a real client still isn't reflected in `bank_balance`
without further work.

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
