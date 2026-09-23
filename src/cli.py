"""AEO auditor CLI.

  python src/cli.py data/fixtures/before.html --robots data/fixtures/robots_before.txt
  python src/cli.py data/fixtures/after.html  --robots data/fixtures/robots_after.txt --questions data/fixtures/questions.json
  python src/cli.py https://example.com --json report.json --fail-under 70
  python src/cli.py compare data/fixtures/before.html data/fixtures/after.html --questions data/fixtures/questions.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aeo import answerability, checks  # noqa: E402
from aeo.fetch import load  # noqa: E402
from aeo.llm import LLMClient  # noqa: E402

MARK = {"pass": "PASS", "partial": "PART", "fail": "FAIL", "n/a": " n/a"}


def audit(target: str, robots=None, llms=None, questions=None, provider=None) -> dict:
    src = load(target, robots, llms)
    soup = BeautifulSoup(src.html, "html.parser")
    result = checks.score(checks.run_all(soup, src.robots_txt, src.llms_txt, target, src.is_remote))
    result["target"] = target
    if questions:
        qs = json.loads(Path(questions).read_text(encoding="utf-8"))
        client = LLMClient(provider)
        result["answerability"] = answerability.evaluate(client, soup, qs)
        result["provider"] = client.provider
    return result


def render(res: dict) -> str:
    out = [f"\nAEO audit: {res['target']}", f"Score: {res['score']}/100 (grade {res['grade']})", ""]
    for c in res["checks"]:
        out.append(f"  [{MARK[c['status']]}] {c['id']:<3} {c['name']:<42} {c['score']:>4}/{c['weight']:<3} {c['evidence'][:90]}")
        if c["fix"] and c["status"] in ("fail", "partial"):
            out.append(f"         fix: {c['fix']}")
    if "answerability" in res:
        a = res["answerability"]
        out += ["", f"Answerability ({res['provider']}): {a['answered']}/{a['total']} questions answered from crawler-visible content"]
        for r in a["rows"]:
            out.append(f"  [{'OK ' if r['correct'] else 'MISS'}] {r['question']}")
    return "\n".join(out)


def to_markdown(res: dict) -> str:
    lines = [f"# AEO audit: `{res['target']}`", "", f"**Score:** {res['score']}/100 (grade {res['grade']})", "",
             "| Check | Status | Score | Evidence | Fix |", "|---|---|---|---|---|"]
    for c in res["checks"]:
        lines.append(f"| {c['id']} {c['name']} | {c['status']} | {c['score']}/{c['weight']} | {c['evidence']} | {c['fix']} |")
    if "answerability" in res:
        a = res["answerability"]
        lines += ["", f"## Answerability: {a['answered']}/{a['total']}", ""] + [f"- {'OK' if r['correct'] else 'MISS'}: {r['question']}" for r in a["rows"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        ap = argparse.ArgumentParser(prog="cli.py compare")
        ap.add_argument("before")
        ap.add_argument("after")
        ap.add_argument("--robots-before", default=None)
        ap.add_argument("--robots-after", default=None)
        ap.add_argument("--questions")
        ap.add_argument("--provider")
        a = ap.parse_args(sys.argv[2:])
        b = audit(a.before, a.robots_before, None, a.questions, a.provider)
        f = audit(a.after, a.robots_after, None, a.questions, a.provider)
        print(f"\n{'Check':<46}{'Before':>8}{'After':>8}")
        for cb, cf in zip(b["checks"], f["checks"]):
            print(f"{cb['id'] + ' ' + cb['name']:<46}{cb['score']:>8}{cf['score']:>8}")
        print(f"{'TOTAL SCORE':<46}{b['score']:>8}{f['score']:>8}")
        if a.questions:
            print(f"{'Questions answerable':<46}{b['answerability']['answered']:>6}/{b['answerability']['total']}{f['answerability']['answered']:>6}/{f['answerability']['total']}")
        return

    ap = argparse.ArgumentParser(description="Audit a page for AI answer-engine discoverability.")
    ap.add_argument("target", help="URL or local HTML file")
    ap.add_argument("--robots", help="robots.txt to use (defaults to the site's own for URLs)")
    ap.add_argument("--llms", help="llms.txt to use")
    ap.add_argument("--questions", help="JSON list of {question, answer_contains} for the answerability eval")
    ap.add_argument("--provider", choices=["mock", "ollama", "ollama-small", "openai", "gemini", "anthropic"])
    ap.add_argument("--json", help="write JSON report to this path")
    ap.add_argument("--md", help="write markdown report to this path")
    ap.add_argument("--fail-under", type=int, default=0, help="exit 1 if score is below this (for CI)")
    a = ap.parse_args()

    res = audit(a.target, a.robots, a.llms, a.questions, a.provider)
    print(render(res))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=2), encoding="utf-8")
    if a.md:
        Path(a.md).write_text(to_markdown(res), encoding="utf-8")
    sys.exit(1 if res["score"] < a.fail_under else 0)


if __name__ == "__main__":
    main()
