"""Cosine-similarity retrieval over the ingested wiki chunks.

Loads ``backend/data/wiki_chunks.json`` lazily on first call, embeds the
incoming query with the same MiniLM model, and returns the top-k chunks ranked
by dot product (which equals cosine similarity since embeddings are
L2-normalized at ingest time).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np

from embedder import EMBEDDING_DIM, MODEL_NAME, embed_query

DATA_PATH = Path(__file__).resolve().parent / "data" / "wiki_chunks.json"


@dataclass
class RetrievedChunk:
    """One retrieval hit with its source metadata and similarity score."""
    title: str
    url: str
    text: str
    score: float


@lru_cache(maxsize=1)
def _load_index() -> tuple[list[dict], np.ndarray]:
    """Load chunks + embedding matrix once; cached for subsequent queries."""
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"missing {DATA_PATH}. Run `python backend/ingest.py` first."
        )
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if payload.get("model") != MODEL_NAME:
        raise RuntimeError(
            f"index was built with {payload.get('model')}, but embedder uses {MODEL_NAME}"
        )
    if payload.get("dim") != EMBEDDING_DIM:
        raise RuntimeError(f"unexpected embedding dim: {payload.get('dim')}")

    chunks = payload["chunks"]
    matrix = np.asarray([c["embedding"] for c in chunks], dtype=np.float32)
    return chunks, matrix


def retrieve(query: str, top_k: int = 5) -> List[RetrievedChunk]:
    """Return the top-k chunks for ``query`` ordered by descending similarity."""
    query = (query or "").strip()
    if not query:
        return []
    if top_k <= 0:
        return []

    chunks, matrix = _load_index()
    q_vec = embed_query(query)
    # Embeddings and query are L2-normalized, so dot product == cosine sim.
    scores = matrix @ q_vec
    k = min(top_k, len(chunks))
    # argpartition for speed, then sort just the top-k slice.
    top_idx = np.argpartition(-scores, k - 1)[:k]
    top_idx = top_idx[np.argsort(-scores[top_idx])]

    return [
        RetrievedChunk(
            title=chunks[i]["title"],
            url=chunks[i]["url"],
            text=chunks[i]["text"],
            score=float(scores[i]),
        )
        for i in top_idx
    ]


def warmup() -> None:
    """Force-load the index and model so the first user query is fast."""
    _load_index()
    embed_query("warmup")
