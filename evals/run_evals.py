"""Eval harness for CraftMind.

Runs every query in ``evals/test_queries.json`` through the full pipeline and
grades each result on three axes:

  topic   — at least one expected topic word appears in the answer (case-insensitive)
  cite    — the named page title is present in answer text or in cited sources
  ground  — when ``should_not_hallucinate`` is true, the answer must NOT be the
            refusal string; when false, the answer MUST be the refusal string

A query "passes" only if all three checks pass. Prints a per-query line and a
summary breakdown by category.

Usage: ``python evals/run_evals.py``
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from main import REFUSAL, answer_question  # noqa: E402

QUERIES_PATH = Path(__file__).resolve().parent / "test_queries.json"

# Pause between LLM calls. Groq free tier allows ~30 RPM on llama-3.1-8b-instant,
# so 2.5s ⇒ 24 RPM with comfortable headroom.
CALL_DELAY_SEC = 2.5
# Fallback backoff when 429 hits and we can't parse a retry-delay hint.
RATE_LIMIT_BACKOFF_SEC = 30
# How many times to retry a single query when we get rate-limited.
RATE_LIMIT_RETRIES = 3


def _contains_any(haystack: str, needles: List[str]) -> bool:
    """True if any of ``needles`` appears in ``haystack`` (case-insensitive)."""
    h = haystack.lower()
    return any(n.lower() in h for n in needles)


def _cited(answer: str, sources: List[dict], expected: str) -> bool:
    """True if the expected page title appears in citations or inline brackets."""
    expected_l = expected.lower()
    for s in sources:
        if s["title"].lower() == expected_l:
            return True
    # Inline citation like [Mending] also counts.
    bracketed = re.findall(r"\[([^\]]+)\]", answer)
    return any(b.strip().lower() == expected_l for b in bracketed)


def _is_refusal(answer: str) -> bool:
    """True if ``answer`` is (substantially) the canonical refusal string."""
    return REFUSAL.lower().strip(".") in answer.lower()


def _parse_retry_delay(msg: str) -> float:
    """Pull the server-suggested retry delay (seconds) out of a 429 error message."""
    m = re.search(r"retry in (\d+(?:\.\d+)?)\s*s", msg, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.search(r"retry_delay\s*\{[^}]*seconds:\s*(\d+)", msg)
    if m:
        return float(m.group(1))
    return RATE_LIMIT_BACKOFF_SEC


def run_query(item: dict) -> dict:
    """Run one eval item end-to-end, retrying on rate-limit errors."""
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        try:
            result = answer_question(item["query"])
            return {
                "answer": result.answer,
                "sources": [{"title": s.title, "url": s.url} for s in result.sources],
                "confidence": result.confidence,
            }
        except Exception as exc:
            msg = str(exc)
            rate_limited = "429" in msg or "quota" in msg.lower()
            if rate_limited and attempt < RATE_LIMIT_RETRIES:
                # Server hints at how long to wait; honor it plus a small buffer.
                delay = _parse_retry_delay(msg) + 3
                print(f"  ! rate-limited, backing off {delay:.0f}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue
            return {"answer": f"<error: {msg[:160]}>", "sources": [], "confidence": 0.0}


def grade(item: dict, result: dict) -> Dict[str, bool]:
    """Score one (item, result) pair on topic / cite / ground."""
    answer = result["answer"]
    sources = result["sources"]

    topic_ok = _contains_any(answer, item["expected_topics"])
    cite_ok = _cited(answer, sources, item["should_cite"])

    refusing = _is_refusal(answer)
    if item["should_not_hallucinate"]:
        # Answerable from wiki — we expect a real, cited answer.
        ground_ok = not refusing
    else:
        # Not in scope — we expect the model to refuse and we can't grade citation.
        ground_ok = refusing
        cite_ok = True  # refusals don't need to cite

    return {"topic": topic_ok, "cite": cite_ok, "ground": ground_ok}


def main() -> None:
    """Run all eval queries, print per-query results, and summarize by category."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    items = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    print(f"Running {len(items)} eval queries (delay {CALL_DELAY_SEC}s between calls)\n")

    rows: List[dict] = []
    for i, item in enumerate(items, 1):
        print(f"[{i:02d}/{len(items)}] ({item['category']}) {item['query'][:70]}")
        result = run_query(item)
        scores = grade(item, result)
        passed = all(scores.values())
        marks = "".join("✓" if scores[k] else "✗" for k in ("topic", "cite", "ground"))
        verdict = "PASS" if passed else "FAIL"
        print(f"        {verdict}  [{marks}]  conf={result['confidence']:.2f}")
        rows.append({"item": item, "result": result, "scores": scores, "passed": passed})
        if i < len(items):
            time.sleep(CALL_DELAY_SEC)

    # Aggregate.
    total = len(rows)
    passed = sum(r["passed"] for r in rows)
    by_cat: Dict[str, List[bool]] = {}
    for r in rows:
        by_cat.setdefault(r["item"]["category"], []).append(r["passed"])

    print("\n" + "=" * 60)
    print(f"OVERALL: {passed}/{total} passed ({passed / total * 100:.0f}%)")
    print("By category:")
    for cat, results in sorted(by_cat.items()):
        p = sum(results)
        n = len(results)
        print(f"  {cat:12s}  {p}/{n}")

    failures = [r for r in rows if not r["passed"]]
    if failures:
        print("\nFailures:")
        for r in failures:
            failed_checks = [k for k, v in r["scores"].items() if not v]
            print(f"  - [{','.join(failed_checks)}] {r['item']['query'][:80]}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
