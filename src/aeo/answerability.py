"""Answerability eval: can an AI assistant answer real questions from what it can read?

The score in checks.py measures hygiene. This measures the outcome. We give a
model ONLY the text a non-JS crawler sees (visible text + JSON-LD) and ask it
the questions a real investor might ask. If the answer isn't in that text,
the page is invisible to answer engines for that question, however good it
looks in a browser.
"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .checks import json_ld_blocks, visible_text
from .llm import LLMClient

SYSTEM = """Answer the question using ONLY the page content provided.
If the content does not contain the answer, reply exactly: NOT FOUND.
Answer in one short sentence and include the exact figure or date."""


def crawler_view(soup: BeautifulSoup) -> str:
    blocks, _ = json_ld_blocks(soup)
    ld = "\n".join(json.dumps(b) for b in blocks)
    return f"{visible_text(soup)}\n\n[structured data]\n{ld}"


def _mock_answer(context: str, expected: list[str]) -> str:
    for exp in expected:
        idx = context.find(exp)
        if idx >= 0:
            start = max(0, context.rfind(".", 0, idx) + 1)
            end = context.find(".", idx + len(exp))
            return context[start:end + 1 if end > 0 else None].strip()[:200]
    return "NOT FOUND"


def _norm(s: str) -> str:
    """Compare facts, not formatting: '1,204.6', '1204.6' and 'EUR 1 204.6' all match."""
    s = s.lower().replace("\u00a0", " ")
    s = re.sub(r"(?<=\d)[,\s](?=\d{3}\b)", "", s)
    return re.sub(r"\s+", " ", s).strip()


def is_correct(answer: str, expected: list[str]) -> bool:
    """Strict: the model must not hedge with NOT FOUND, and must state an expected value."""
    if "not found" in answer.lower():
        return False
    a = _norm(answer)
    return any(_norm(e) in a for e in expected)


def evaluate(client: LLMClient, soup: BeautifulSoup, questions: list[dict]) -> dict:
    context = crawler_view(soup)[:12000]
    rows = []
    for q in questions:
        resp = client.chat("writer", SYSTEM, f"<page>\n{context}\n</page>\n\nQuestion: {q['question']}",
                           mock=lambda q=q: _mock_answer(context, q["answer_contains"]))
        answer = resp.text.strip()
        correct = is_correct(answer, q["answer_contains"])
        rows.append({"question": q["question"], "answer": answer, "correct": correct, "model": resp.model})
    n_ok = sum(r["correct"] for r in rows)
    return {"answered_pct": round(100 * n_ok / len(rows)) if rows else 0, "answered": n_ok, "total": len(rows), "rows": rows}
