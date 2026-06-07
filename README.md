# CraftMind

A semantic search AI for the **Minecraft Java Edition 1.21** wiki. Ask natural
language questions; get grounded, cited answers pulled from real wiki data —
not LLM training memory.

> *"What's the cheapest enchanting order for Sharpness V, Unbreaking III,
> Mending on a sword?"*
> *"Where should I dig to find diamonds in 1.21?"*
> *"On diamond ore, should I use Fortune or Silk Touch?"*

## Why this exists

Stock LLMs hallucinate Minecraft mechanics constantly — they confuse Java with
Bedrock, use deprecated y-levels, invent enchantment costs. CraftMind grounds
every answer in retrieved chunks from minecraft.wiki and forces the model to
cite the page it pulled from. If the wiki doesn't say it, the model says
*"I don't have reliable information on that"* instead of making something up.

## Architecture

```
                ┌────────────────┐
   user query → │   React UI     │
                │  (Vite + TW)   │
                └───────┬────────┘
                        │ POST /query
                ┌───────▼────────┐
                │   FastAPI      │
                │   backend      │
                └───────┬────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐   ┌─────────────┐   ┌──────────┐
   │embedder │   │  retriever  │   │  prompt  │
   │MiniLM   │   │  cosine sim │   │  system  │
   │384-d    │   │  top-5      │   │  + ctx   │
   └─────────┘   └──────┬──────┘   └─────┬────┘
                        │                │
                        ▼                ▼
                ┌────────────────────────────┐
                │  wiki_chunks.json (109)    │
                │  built once by ingest.py   │
                └────────────────────────────┘
                                 │
                                 ▼
                        ┌────────────────┐
                        │   Groq LLM     │
                        │ llama-3.1-8b   │
                        └────────────────┘
```

**Pipeline:**

1. `ingest.py` fetches 20 wiki pages, strips HTML chrome, chunks each into
   ~300-token windows with 50-token overlap, embeds with
   `sentence-transformers/all-MiniLM-L6-v2`, saves to `wiki_chunks.json`.
2. `retriever.py` loads the chunks at startup, embeds the user's query, returns
   the top-5 chunks by cosine similarity.
3. `prompt.py` assembles those chunks into a context block + system prompt that
   forbids ungrounded answers and requires inline `[PageTitle]` citations.
4. `main.py` (FastAPI) glues it together and exposes `/query` and `/health`.
5. React frontend posts the question to `/query`, renders the answer card with
   cited sources and a confidence badge.

## Setup

You need Python 3.10+, Node 18+, and a free Groq API key
(<https://console.groq.com/keys>).

```bash
# 1. Clone
git clone https://github.com/GP-creator/MC_wikiai.git
cd MC_wikiai

# 2. Python env + deps
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r backend/requirements.txt

# 3. Add your Groq key
cp .env.example .env
#   then edit .env, set GROQ_API_KEY=gsk_...

# 4. Build the wiki index (one-time, ~1 min)
python backend/ingest.py

# 5. Start the backend
uvicorn backend.main:app --reload
#   → http://127.0.0.1:8000

# 6. In a separate terminal, start the frontend
cd frontend
npm install
npm run dev
#   → http://127.0.0.1:5173
```

Open <http://127.0.0.1:5173> and start asking.

## Example queries

- "What does the Mending enchantment do?"
- "How does Fortune affect ore drops?"
- "Where can I find a Stronghold and how many are there per world?"
- "Walk me through brewing a basic potion."
- "Is it worth upgrading from diamond to netherite gear?"

## Evals

20 golden queries across 4 categories grade every answer on three axes:

- **topic** — does the answer mention an expected keyword?
- **cite** — does it cite the expected wiki page?
- **ground** — does it answer (or refuse) as expected?

```bash
python evals/run_evals.py
```

**Result: 19/20 passed (95%)** with `llama-3.1-8b-instant` via Groq.

| Category   | Passed |
|------------|--------|
| enchanting | 5 / 5  |
| location   | 5 / 5  |
| mechanics  | 5 / 5  |
| tradeoff   | 4 / 5  |

The one failure is a `should_not_hallucinate=false` query (bed vs beacons in
the Nether) where the model answered instead of refusing. All citations were
correct.

## Quick tests

```bash
python backend/test_ingest.py     # validates wiki_chunks.json shape
python backend/test_retriever.py  # 5 hard queries, prints top-3 hits
```

## Known limitations

- **Knowledge boundary** — limited to the 20 pages ingested. Questions about
  pages we don't index (mobs other than Blaze/Ender Dragon, redstone, etc.)
  will refuse or retrieve weakly. Edit `PAGES` in `backend/ingest.py` to
  expand coverage.
- **Refusal calibration** — the model occasionally answers tangential
  tradeoff questions it should refuse (1/20 on the eval set).
- **Bedrock vs Java** — chunks may contain Bedrock notes; the system prompt
  tells the LLM to prefer Java 1.21 but ambiguous chunks can leak.
- **Wiki freshness** — the index is a snapshot; re-run `ingest.py` to refresh.
- **LLM provider** — original spec called for Gemini, but Gemini's 10 RPM free
  tier made evals impractical. Switched to Groq for 30 RPM headroom and
  sub-second responses. See `backend/main.py:_call_llm`.

## Stack

| Layer        | Tool                                          |
|--------------|-----------------------------------------------|
| Backend      | FastAPI + uvicorn                             |
| Embeddings   | `sentence-transformers/all-MiniLM-L6-v2`      |
| Vector store | NumPy matrix in memory (109 × 384)            |
| LLM          | Groq `llama-3.1-8b-instant`                   |
| Frontend     | React 18 + Vite + Tailwind CSS                |
| Data source  | minecraft.wiki MediaWiki API (CC BY-NC-SA 3.0)|

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — covers code style, the wiki data
license, and reporting issues.

## License

Code: MIT (see [LICENSE](LICENSE) if/when added).
Wiki content used in answers: **CC BY-NC-SA 3.0** via minecraft.wiki —
attribution required, non-commercial only, share-alike on derivatives.
