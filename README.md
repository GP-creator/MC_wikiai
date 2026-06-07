# CraftMind

A semantic search AI for the Minecraft Java Edition 1.21 wiki — ask natural language questions and get grounded, cited answers pulled from real wiki data.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r backend/requirements.txt
```

## Ingest the wiki

Run once to fetch, chunk, embed, and cache the source pages. Produces
`backend/data/wiki_chunks.json` (not committed).

```bash
python backend/ingest.py
python backend/test_ingest.py   # quick sanity check
```

The ingester pulls 20 pages (enchantments, ores, structures, mobs, mechanics)
from the public minecraft.wiki MediaWiki API, splits each page into ~300 token
windows with 50 token overlap, and embeds them with
`sentence-transformers/all-MiniLM-L6-v2` (384-d).

## Evals

20 golden queries across 4 categories (enchanting / location / mechanics / tradeoff)
grade every answer on three axes:

- **topic** — does the answer mention an expected keyword?
- **cite** — does it cite the expected wiki page?
- **ground** — does it answer (or refuse) as expected?

```bash
python evals/run_evals.py
```

**Current result: 19/20 passed (95%)** with `llama-3.1-8b-instant` via Groq.

| Category   | Passed |
|------------|--------|
| enchanting | 5 / 5  |
| location   | 5 / 5  |
| mechanics  | 5 / 5  |
| tradeoff   | 4 / 5  |

The one failure is a `should_not_hallucinate=false` query ("bed vs beacons in
the Nether") where the model answered instead of refusing — a known weakness
when the wiki context is tangential. All citations were correct.

More setup instructions coming in later increments.
