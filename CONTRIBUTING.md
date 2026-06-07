# Contributing to CraftMind

Thanks for your interest! A few quick notes before you open a PR or run the system.

## Data license — minecraft.wiki

CraftMind's answers are grounded in content fetched from **minecraft.wiki** via
its public MediaWiki API. That content is licensed under
[**CC BY-NC-SA 3.0**](https://creativecommons.org/licenses/by-nc-sa/3.0/).

What that means in practice:

- **Attribution** — every answer surface (the answer card, exported text, any
  derivative UI) must credit minecraft.wiki and link back to the source pages.
  The current frontend does this via per-source citation links and a footer
  credit; if you build new surfaces, keep that pattern.
- **NonCommercial** — you may not use CraftMind, the ingested data, or derived
  outputs for commercial purposes without explicit permission from the
  minecraft.wiki maintainers.
- **ShareAlike** — if you redistribute the ingested data or any derivative
  embeddings, you must release them under the same CC BY-NC-SA 3.0 license.

The raw ingested file (`backend/data/wiki_chunks.json`) is intentionally
**not** committed to this repo. Each contributor regenerates it locally with
`python backend/ingest.py`. This keeps redistribution explicit and lets the
wiki update independently of the code.

If you change the ingest script (new pages, different chunking) and want to
share the resulting dataset, package it separately with a clear CC BY-NC-SA
3.0 LICENSE file and a link back to minecraft.wiki.

## Code style

- **Python**: type hints on public functions, docstrings under 3 lines, no
  unnecessary abstractions.
- **React**: function components, Tailwind utility classes, no inline styles,
  no CSS-in-JS libraries.
- Keep comments to the *why*, not the *what*. Self-documenting names beat
  prose every time.

## Running locally

See the main [README](README.md) for setup. Before pushing:

```bash
python backend/test_ingest.py     # ingestion artifact sanity check
python backend/test_retriever.py  # retrieval relevance spot-check
python evals/run_evals.py         # full pipeline graded on 20 golden queries
```

## Reporting issues

Please open issues on
[GitHub](https://github.com/GP-creator/MC_wikiai/issues) with:

- The query you ran
- The answer + cited sources you got
- What you expected
- Whether the wiki page actually contains the information

Wrong citations and hallucinations are the highest-priority bugs.
