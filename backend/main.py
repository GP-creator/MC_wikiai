"""CraftMind FastAPI backend.

Exposes:
  - POST /query   {question} -> {answer, sources, confidence}
  - GET  /health  -> {status, chunks, model}

Run with: ``uvicorn backend.main:app --reload`` from the repo root.
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Allow `python backend/main.py` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prompt import SYSTEM_PROMPT, build_user_prompt
from retriever import RetrievedChunk, retrieve, warmup

# Load .env from the repo root if present.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GEMINI_MODEL_NAME = "gemini-2.5-flash"  # successor to gemini-1.5-flash; 2.0 has no free quota on new keys
TOP_K = 5
SNIPPET_LEN = 240
REFUSAL = "I don't have reliable information on that."

log = logging.getLogger("craftmind")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------

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
    """Send the assembled prompt to Gemini and return the response text.

    Raises RuntimeError on auth/quota/network failures so the route handler
    can convert it to a clean HTTP 502.
    """
    import google.generativeai as genai  # local import keeps test_retriever lightweight

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
    try:
        response = model.generate_content(user_prompt)
    except Exception as exc:
        raise RuntimeError(f"gemini call failed: {exc}") from exc
    try:
        return response.text.strip()
    except Exception:
        # Blocked or empty candidate — surface a clean refusal instead of crashing.
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


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="CraftMind", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # CRA default
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    """POST /query body."""
    question: str = Field(..., min_length=1, max_length=1000)


class SourceModel(BaseModel):
    title: str
    url: str
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceModel]
    confidence: float


@app.on_event("startup")
def _startup() -> None:
    """Warm the retriever index and embedding model so the first query is fast."""
    try:
        warmup()
        log.info("retriever warmed up")
    except Exception as exc:
        log.warning("warmup skipped: %s", exc)


@app.get("/health")
def health() -> dict:
    """Liveness probe; also reports index size if loaded."""
    try:
        from retriever import _load_index
        chunks, _ = _load_index()
        return {"status": "ok", "chunks": len(chunks), "model": GEMINI_MODEL_NAME}
    except FileNotFoundError:
        return {"status": "degraded", "reason": "wiki_chunks.json not built", "model": GEMINI_MODEL_NAME}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    """Answer a natural-language question grounded in retrieved wiki chunks."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")
    try:
        result = answer_question(question)
    except RuntimeError as exc:
        msg = str(exc)
        log.error("query failed: %s", msg)
        if "GEMINI_API_KEY" in msg:
            raise HTTPException(status_code=500, detail=msg)
        raise HTTPException(status_code=502, detail="LLM provider error")
    return QueryResponse(
        answer=result.answer,
        sources=[SourceModel(**asdict(s)) for s in result.sources],
        confidence=result.confidence,
    )


# ---------------------------------------------------------------------------
# CLI demo (kept from Increment 4 for terminal smoke testing)
# ---------------------------------------------------------------------------

def _demo() -> None:
    """Print answers for three calibration questions covering different shapes."""
    queries = [
        "What's the cheapest enchanting order for Sharpness V, Unbreaking III, Mending on a sword?",
        "Where should I dig to find diamonds in Java 1.21?",
        "On diamond ore, should I use Fortune or Silk Touch -- what's the tradeoff?",
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _demo()
