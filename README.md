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
to do the job — under your Reddit account. This does *not* submit real Upwork
proposals (no such API exists for self-serve use).

## Real deployment (Stripe + Vercel)

By default, `execute_build` (micro_saas) and `execute_content` (content_farm)
are pure simulation: fabricated URLs, dice-roll "sales." Set
`ENABLE_REAL_DEPLOYMENT=true` (plus `VERCEL_TOKEN` and `STRIPE_SECRET_KEY`) to make
them real:

- **micro_saas** generates a real single-page site, creates a **real Stripe
  product + price + payment link**, deploys the page live to Vercel with the
  payment link wired into the buy button, and stores the product with
  `real: true` in `state.products`.
- **content_farm** generates and actually deploys the article to a live Vercel
  URL. There's no ad-network integration, so a real publish earns $0
  automatically — monetizing it for real needs an ads account wired up separately.
- A `service_arbitrage` real bid (see above) also gets a real Stripe payment
  link attached to the outreach message, so an interested client has somewhere
  real to pay.

Just like real bidding, real deployment is gated by the same email approval —
the agent stops and asks before creating a real Stripe product or publishing
real content under your identity, not just before posting on Reddit. Deploying
the *same* niche twice is a no-op (checked against already-live products) so
naive-mode's 3-cycle niche rotation doesn't spam duplicate Stripe products.

`collect_revenue` reflects the split automatically: any product or bid with a
`stripe_payment_link_id` is reconciled against **actual confirmed Stripe
Checkout Sessions** (polled each cycle, deduped by session id so nothing is
double-counted) — no more dice rolls for that item. Everything else keeps
rolling dice as before. `STRIPE_SECRET_KEY` can be a `sk_test_` key to rehearse
with Stripe's test cards, or `sk_live_` once you actually want to charge real
customers — the code doesn't care which, it just uses whatever's configured.

What's still not automated even in real mode: the server-burn number
(`SERVER_BURN_PER_HOUR`) is a configured assumption, not metered against
whatever you're actually hosting this on; and nothing in `execute_build`
maintains the deployed product after launch (bug fixes, customer support,
etc. — it just deploys once and waits for `collect_revenue` to poll for sales).

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
