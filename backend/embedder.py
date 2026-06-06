"""Embedding utilities backed by sentence-transformers."""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def load_model() -> SentenceTransformer:
    """Load the embedding model once and cache it for reuse."""
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: Iterable[str], batch_size: int = 32) -> np.ndarray:
    """Embed a list of strings, returning a float32 array with L2-normalized rows."""
    model = load_model()
    arr = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return arr.astype(np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string. Returns a 1D normalized float32 vector."""
    return embed_texts([query])[0]
