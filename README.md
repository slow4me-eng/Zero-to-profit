# ZERO TO PROFIT — autonomous revenue research platform

This is a real deployable application, not a chat simulation. It runs a persistent
worker, calls an AI model when configured, stores its memory and experiments in
SQLite, and exposes a mobile-friendly dashboard.

## Objective
Start with €0 and discover practical, lawful ways to earn revenue. The system uses
separate research roles (market scout, offer designer, growth analyst and critic),
ranks opportunities, proposes experiments, tracks outcomes, and learns from history.

## Important limits
- It cannot guarantee income. Zero capital usually means selling a service, skill,
  useful information, or a digital deliverable before buying tools or ads.
- It does not silently send spam, impersonate people, break platform rules, spend
  money, invest funds, or claim hypothetical sales as received revenue.
- The code-lab can generate proposed code improvements and run tests in an isolated
  temporary copy. Applying arbitrary self-written code to the live service is not
  enabled: a bad patch could destroy the agent or expose credentials.
- Free hosting tiers often sleep or have usage limits. Reliable 24/7 hosting usually
  costs money. This package cannot create a public URL until deployed to a hosting
  account.

## Quick start (computer or cloud shell)
Python 3.11+
1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
2. `pip install -r requirements.txt`
3. `python run.py`
4. Visit `http://localhost:8000`

Without an API key, it runs in demo mode and records sample opportunities. The AI
model name is configurable using `OPENAI_MODEL`.

## Deploy
- Docker: `docker build -t zero-to-profit .` then run with environment variables and
  a persistent volume mounted at `/app/data`.
- Render: use `render.yaml`. Select a persistent disk if available on your plan.
  Free web services may sleep and are not suitable for uninterrupted operation.
- Any host: run `python run.py`, expose port 8000, and persist `/app/data`.

Set `DASHBOARD_PASSWORD` before making the dashboard public. Never commit `.env`.
The dashboard is protected by HTTP Basic Auth when a password is set.

## Dashboard functions
- Live status, cycle count, verified revenue and recorded costs
- Multi-role agent reports and opportunity backlog
- Proposed next experiments and outcome recording
- Revenue/cost ledger (manual verified entries)
- Code-improvement proposals and test results

## GitHub upload
Upload the *contents* of this project directory to your repository. Do not upload
`.env`, API keys, database files, or credentials.
