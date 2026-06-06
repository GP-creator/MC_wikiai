"""Manual smoke test for the retriever.

Prints the top retrieved chunks for a handful of hard Minecraft questions so a
human can eyeball relevance. Not a pass/fail test — the eval harness in
Increment 7 does that. Run with: ``python backend/test_retriever.py``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Force UTF-8 stdout so wiki characters (fractions, em-dashes) print on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from retriever import retrieve

QUERIES = [
    "enchanting order for sword",
    "where to find diamonds in 1.21",
    "how does fortune work on ore",
    "what drops from blazes",
    "best biome to start a base",
]


def main() -> None:
    """Run each test query and print the top-3 hits with a short snippet."""
    for q in QUERIES:
        print("=" * 80)
        print(f"Q: {q}")
        hits = retrieve(q, top_k=3)
        for rank, hit in enumerate(hits, 1):
            snippet = hit.text.replace("\n", " ")[:200]
            print(f"  [{rank}] score={hit.score:.3f}  {hit.title}")
            print(f"      url: {hit.url}")
            print(f"      snippet: {snippet}...")
        print()


if __name__ == "__main__":
    main()
