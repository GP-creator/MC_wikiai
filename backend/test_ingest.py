"""Sanity checks on the ingested wiki_chunks.json artifact.

Verifies the file exists, the model/dim metadata matches the embedder, every
chunk has the expected fields, and embeddings are L2-normalized 384-d vectors.
Run with: ``python backend/test_ingest.py``.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from embedder import EMBEDDING_DIM, MODEL_NAME

DATA_PATH = Path(__file__).resolve().parent / "data" / "wiki_chunks.json"
EXPECTED_PAGES = {
    "Enchanting", "Fortune", "Silk Touch", "Unbreaking", "Mending",
    "Sharpness", "Protection", "Efficiency", "Looting", "Biome",
    "Ore", "Stronghold", "Nether Fortress", "Blaze", "Ender Dragon",
    "Crafting", "Brewing", "Spawning", "Diamond", "Netherite",
}


def main() -> None:
    """Run all sanity checks and print a pass summary."""
    assert DATA_PATH.exists(), f"missing artifact: {DATA_PATH} — run ingest.py first"

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    assert payload["model"] == MODEL_NAME, f"model mismatch: {payload['model']}"
    assert payload["dim"] == EMBEDDING_DIM, f"dim mismatch: {payload['dim']}"

    chunks = payload["chunks"]
    assert len(chunks) >= 80, f"expected >=80 chunks, got {len(chunks)}"

    titles_seen = set()
    for chunk in chunks:
        for key in ("id", "title", "url", "text", "embedding"):
            assert key in chunk, f"chunk missing key {key!r}"
        assert chunk["text"].strip(), f"empty text in chunk {chunk['id']}"
        assert chunk["url"].startswith("https://minecraft.wiki/w/"), chunk["url"]
        vec = chunk["embedding"]
        assert len(vec) == EMBEDDING_DIM, f"bad dim: {len(vec)}"
        norm = math.sqrt(sum(x * x for x in vec))
        assert 0.99 < norm < 1.01, f"embedding not normalized: norm={norm}"
        titles_seen.add(chunk["title"])

    missing = EXPECTED_PAGES - titles_seen
    assert not missing, f"missing pages: {missing}"

    print(f"PASS  chunks={len(chunks)}  dim={payload['dim']}  pages={len(titles_seen)}")


if __name__ == "__main__":
    main()
