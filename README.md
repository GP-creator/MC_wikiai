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

More setup instructions coming in later increments.
