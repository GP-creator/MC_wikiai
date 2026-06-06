"""One-time wiki ingestion: fetch -> clean -> chunk -> embed -> save.

Pulls a fixed set of Minecraft Java Edition 1.21 wiki pages from the public
MediaWiki API at minecraft.wiki, strips HTML chrome, splits each page into
overlapping token windows, embeds them, and writes the result to
``backend/data/wiki_chunks.json`` for the retriever to load at runtime.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import List
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

# Allow `python backend/ingest.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from embedder import EMBEDDING_DIM, MODEL_NAME, embed_texts, load_model

WIKI_API = "https://minecraft.wiki/api.php"
WIKI_PAGE_BASE = "https://minecraft.wiki/w/"
USER_AGENT = "CraftMind/0.1 (educational; https://github.com/GP-creator/MC_wikiai)"

PAGES = [
    "Enchanting",
    "Fortune",
    "Silk Touch",
    "Unbreaking",
    "Mending",
    "Sharpness",
    "Protection",
    "Efficiency",
    "Looting",
    "Biome",
    "Ore",
    "Stronghold",
    "Nether Fortress",
    "Blaze",
    "Ender Dragon",
    "Crafting",
    "Brewing",
    "Spawning",
    "Diamond",
    "Netherite",
]

CHUNK_TOKENS = 300
CHUNK_OVERLAP = 50

OUT_PATH = Path(__file__).resolve().parent / "data" / "wiki_chunks.json"


def page_url(title: str) -> str:
    """Return the canonical reader-facing URL for a wiki page title."""
    return WIKI_PAGE_BASE + quote(title.replace(" ", "_"))


def fetch_page_html(title: str) -> str:
    """Fetch the rendered HTML body of a wiki page via the MediaWiki parse API."""
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
            "formatversion": "2",
            "redirects": "1",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"wiki api error on {title!r}: {data['error']}")
    return data["parse"]["text"]


# Selectors for navigation / non-prose chrome to strip before text extraction.
_DROP_SELECTORS = [
    "table",            # infoboxes, navboxes, sprite tables
    ".navbox",
    ".infobox",
    ".sidebar",
    ".toc",
    ".mw-editsection",
    ".reference",
    ".references",
    ".reflist",
    ".hatnote",
    ".thumb",
    ".gallery",
    ".mw-cite-backlink",
    ".mw-empty-elt",
    "sup.reference",
    "style",
    "script",
    "noscript",
]


def clean_html(html: str) -> str:
    """Strip wiki chrome from rendered HTML and return readable prose."""
    soup = BeautifulSoup(html, "html.parser")
    for selector in _DROP_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # Preserve section structure by joining block elements with newlines.
    text_parts: List[str] = []
    for el in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        chunk = el.get_text(" ", strip=True)
        if not chunk:
            continue
        if el.name.startswith("h"):
            text_parts.append("\n" + chunk + "\n")
        elif el.name == "li":
            text_parts.append("- " + chunk)
        else:
            text_parts.append(chunk)

    text = "\n".join(text_parts)
    # Collapse runs of whitespace and stray bracketed citations like [1].
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, tokenizer, max_tokens: int = CHUNK_TOKENS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping token windows using the model's tokenizer.

    Decodes each window back to a string so embeddings see the same text a
    reader would. Empty windows are dropped.
    """
    if overlap >= max_tokens:
        raise ValueError("overlap must be smaller than max_tokens")

    token_ids = tokenizer.encode(text, add_special_tokens=False)
    if not token_ids:
        return []

    step = max_tokens - overlap
    windows: List[str] = []
    for start in range(0, len(token_ids), step):
        window_ids = token_ids[start : start + max_tokens]
        if not window_ids:
            break
        piece = tokenizer.decode(window_ids, skip_special_tokens=True).strip()
        if piece:
            windows.append(piece)
        if start + max_tokens >= len(token_ids):
            break
    return windows


def build_chunks() -> List[dict]:
    """Fetch each page in PAGES, clean, chunk, and return chunk records (no embeddings yet)."""
    model = load_model()
    tokenizer = model.tokenizer

    chunks: List[dict] = []
    chunk_id = 0
    for title in PAGES:
        print(f"[fetch] {title}")
        try:
            html = fetch_page_html(title)
        except Exception as exc:
            print(f"  ! failed to fetch {title}: {exc}")
            continue

        text = clean_html(html)
        if not text:
            print(f"  ! empty body for {title}")
            continue

        windows = chunk_text(text, tokenizer)
        url = page_url(title)
        for piece in windows:
            chunks.append({
                "id": chunk_id,
                "title": title,
                "url": url,
                "text": piece,
            })
            chunk_id += 1
        print(f"  -> {len(windows)} chunks ({len(text)} chars)")
        time.sleep(0.3)  # be polite to the API
    return chunks


def main() -> None:
    """Run the full ingestion pipeline and write wiki_chunks.json."""
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    chunks = build_chunks()
    if not chunks:
        raise SystemExit("no chunks produced; aborting")

    print(f"\n[embed] {len(chunks)} chunks with {MODEL_NAME}")
    embeddings = embed_texts([c["text"] for c in chunks])
    if embeddings.shape != (len(chunks), EMBEDDING_DIM):
        raise SystemExit(f"unexpected embedding shape: {embeddings.shape}")

    for chunk, vec in zip(chunks, embeddings):
        chunk["embedding"] = [float(x) for x in vec]

    payload = {
        "model": MODEL_NAME,
        "dim": EMBEDDING_DIM,
        "chunk_tokens": CHUNK_TOKENS,
        "chunk_overlap": CHUNK_OVERLAP,
        "pages": PAGES,
        "chunks": chunks,
    }
    OUT_PATH.write_text(json.dumps(payload), encoding="utf-8")
    print(f"\n[done] wrote {len(chunks)} chunks to {OUT_PATH}")


if __name__ == "__main__":
    main()
