"""System prompt and context assembly for the answer-generation LLM."""
from __future__ import annotations

from typing import Sequence

from retriever import RetrievedChunk

SYSTEM_PROMPT = """\
You are CraftMind, an expert assistant on Minecraft Java Edition 1.21.

Strict rules — follow every one:

1. Ground every claim in the WIKI CONTEXT below. Do NOT use general training
   knowledge about Minecraft to answer. Treat the wiki context as your only
   source of truth for this turn.
2. If the wiki context does not contain enough information to answer
   confidently, reply with exactly:
   "I don't have reliable information on that."
   Do not guess, invent numbers, or fall back on prior knowledge.
3. Cite sources inline by page title in square brackets after the relevant
   sentence — for example: "Mending repairs items using XP orbs [Mending]."
   Only cite page titles that appear in the WIKI CONTEXT.
4. Be opinionated and practical. The user is a player who wants actionable
   guidance — recommend an order, name a specific biome, give a concrete
   y-level. Don't just list neutral facts when a recommendation is warranted.
5. Stay focused on Java Edition 1.21. If the wiki context mentions Bedrock or
   older versions, prefer Java 1.21 details.
6. Keep answers under 200 words unless the question genuinely demands more.
   Use short paragraphs or compact bullet lists. No filler preamble.
"""


def assemble_context(chunks: Sequence[RetrievedChunk]) -> str:
    """Format retrieved chunks into a numbered block the LLM can quote from."""
    if not chunks:
        return "(no wiki context available)"
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[{i}] PAGE: {c.title}\nURL: {c.url}\n{c.text}"
        )
    return "\n\n---\n\n".join(parts)


def build_user_prompt(question: str, chunks: Sequence[RetrievedChunk]) -> str:
    """Compose the user-turn prompt: wiki context block followed by the question."""
    context = assemble_context(chunks)
    return (
        "WIKI CONTEXT (Minecraft Java Edition 1.21):\n"
        f"{context}\n\n"
        "---\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using only the wiki context above. Cite page titles like [PageTitle]."
    )
