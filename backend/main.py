"""CraftMind query pipeline.

For Increment 4 this exposes a plain ``answer_question`` function. Increment 5
wraps the same pipeline in FastAPI routes.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Allow `python backend/main.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompt import SYSTEM_PROMPT, build_user_prompt
from retriever import RetrievedChunk, retrieve

# Load .env from the repo root if present.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GEMINI_MODEL_NAME = "gemini-2.5-flash"  # successor to gemini-1.5-flash; the 2.0 line has no free quota on new keys
TOP_K = 5
SNIPPET_LEN = 240
REFUSAL = "I don't have reliable information on that."


@dataclass
class Source:
    """A cited wiki source returned alongside an answer."""
    title: str
    url: str
    snippet: str


@dataclass
class Answer:
    """Final answer plus its citations and a confidence score in [0, 1]."""
    answer: str
    sources: List[Source]
    confidence: float


def _confidence_from_scores(scores: List[float]) -> float:
    """Map the top retrieval similarity into a 0-1 confidence band.

    Cosine sim of ~0.3 on this index means "barely related"; ~0.7 means
    "tightly on-topic". Linear ramp between those points; clamped outside.
    """
    if not scores:
        return 0.0
    top = max(scores)
    return max(0.0, min(1.0, (top - 0.3) / 0.4))


def _dedupe_sources(chunks: List[RetrievedChunk], max_sources: int = 3) -> List[Source]:
    """Keep at most one citation per page title, in score order."""
    seen: set[str] = set()
    sources: List[Source] = []
    for c in chunks:
        if c.title in seen:
            continue
        seen.add(c.title)
        snippet = c.text.replace("\n", " ").strip()
        if len(snippet) > SNIPPET_LEN:
            snippet = snippet[:SNIPPET_LEN].rsplit(" ", 1)[0] + "..."
        sources.append(Source(title=c.title, url=c.url, snippet=snippet))
        if len(sources) >= max_sources:
            break
    return sources


def _call_gemini(user_prompt: str) -> str:
    """Send the assembled prompt to Gemini and return the response text."""
    import google.generativeai as genai  # local import: keeps test_retriever lightweight

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        GEMINI_MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"temperature": 0.2, "max_output_tokens": 800},
    )
    response = model.generate_content(user_prompt)
    # response.text raises if the candidate was blocked; surface a clean refusal.
    try:
        return response.text.strip()
    except Exception:
        return REFUSAL


def answer_question(question: str, top_k: int = TOP_K) -> Answer:
    """Run the full retrieve -> prompt -> Gemini -> cite pipeline for one question."""
    question = (question or "").strip()
    if not question:
        return Answer(answer=REFUSAL, sources=[], confidence=0.0)

    chunks = retrieve(question, top_k=top_k)
    if not chunks:
        return Answer(answer=REFUSAL, sources=[], confidence=0.0)

    confidence = _confidence_from_scores([c.score for c in chunks])
    user_prompt = build_user_prompt(question, chunks)
    answer_text = _call_gemini(user_prompt)
    sources = _dedupe_sources(chunks)
    return Answer(answer=answer_text, sources=sources, confidence=confidence)


def _demo() -> None:
    """Print answers for three calibration questions covering different shapes."""
    queries = [
        "What's the cheapest enchanting order for Sharpness V, Unbreaking III, Mending on a sword?",
        "Where should I dig to find diamonds in Java 1.21?",
        "On diamond ore, should I use Fortune or Silk Touch — what's the tradeoff?",
    ]
    for q in queries:
        print("=" * 80)
        print(f"Q: {q}")
        result = answer_question(q)
        print(f"\nconfidence: {result.confidence:.2f}\n")
        print(result.answer)
        print("\nSources:")
        for s in result.sources:
            print(f"  - {s.title} ({s.url})")
        print()


if __name__ == "__main__":
    # Force UTF-8 stdout so wiki characters render on Windows.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _demo()
