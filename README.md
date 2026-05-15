# GardenAI Streamlit MVP

W1-W2 Concierge MVP for Amazon DE 園藝 AI 運營官.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
op run --env-file=.env -- streamlit run app.py
```

`ADMIN_PASSWORD` comes from the environment. Initial local fallback is `changeme-on-first-run`.

## Deploy Later

Use Streamlit Community Cloud: https://share.streamlit.io

## Architecture

```text
Streamlit app.py
  |
  +-- pages/
  |     +-- Dashboard / SKU / GPSR / Rewrite / Weekly Report
  |
  +-- core/
        +-- scraper.py      amazon.de public listing scrape via httpx + selectolax
        +-- compliance.py   deterministic GPSR rule set + optional Gemini judgement
        +-- llm.py          google-genai wrapper, 24h SQLite cache, call logging
        +-- memory.py       SQLModel tables, partner-scoped SQLite DBs
        +-- prompts.py      GPSR, Listing rewrite, Rufus, Weekly report prompt v1

data/partners/{slug}.db keeps each partner isolated and preserves a Postgres migration path
through SQLModel/SQLAlchemy engines.
```
