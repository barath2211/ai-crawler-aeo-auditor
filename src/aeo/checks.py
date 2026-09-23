"""Discoverability checks for AI answer engines and search crawlers.

Each check returns a score between 0 and its weight, plus evidence and a fix.
Weights add up to 100. They reflect what most often decides whether an AI
assistant can find, read and quote a page's content.
"""
from __future__ import annotations

import json
import re
import urllib.robotparser
from dataclasses import asdict, dataclass
from typing import Optional

from bs4 import BeautifulSoup

AI_CRAWLERS = ["GPTBot", "OAI-SearchBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "CCBot"]
USEFUL_LD_TYPES = {"Organization", "Corporation", "Dataset", "FAQPage", "Article", "NewsArticle", "Table", "Event", "WebPage"}


@dataclass
class CheckResult:
    id: str
    name: str
    weight: int
    score: float
    status: str  # pass | partial | fail | n/a
    evidence: str
    fix: str = ""


def _status(score: float, weight: int) -> str:
    if score >= weight:
        return "pass"
    return "fail" if score == 0 else "partial"


def visible_text(soup: BeautifulSoup) -> str:
    """Text a crawler that does not execute JavaScript can read."""
    clone = BeautifulSoup(str(soup), "html.parser")
    for tag in clone(["script", "style", "template", "iframe", "svg"]):
        tag.decompose()
    return re.sub(r"\s+", " ", clone.get_text(" ")).strip()


def json_ld_blocks(soup: BeautifulSoup) -> tuple[list[dict], list[str]]:
    blocks, errors = [], []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
            blocks.extend(data if isinstance(data, list) else [data])
        except json.JSONDecodeError as exc:
            errors.append(str(exc))
    return blocks, errors


# --------------------------------------------------------------------- checks
def check_iframes(soup, text_words: int) -> CheckResult:
    frames = soup.find_all("iframe")
    w = 15
    if not frames:
        return CheckResult("I1", "Content not trapped in iframes", w, w, "pass", "no iframes")
    srcs = [f.get("src", "") for f in frames]
    score = 0 if text_words < 150 else w * 0.5
    return CheckResult("I1", "Content not trapped in iframes", w, score, _status(score, w),
                       f"{len(frames)} iframe(s): {srcs[:3]}. Crawlers index iframe content as a separate page, if at all, and credit it to the host domain.",
                       "Render the content natively in the page HTML (server-side), and keep the interactive widget as an enhancement.")


def check_server_text(soup, text_words: int) -> CheckResult:
    w = 15
    empty_mounts = [d.get("id") for d in soup.find_all(["div", "section"]) if d.get("id") and not d.get_text(strip=True) and not d.find_all()]
    if text_words >= 300:
        score = w
    elif text_words >= 150:
        score = w * 0.6
    elif text_words >= 50:
        score = w * 0.3
    else:
        score = 0
    ev = f"{text_words} words readable without JavaScript"
    if empty_mounts:
        ev += f"; empty JS mount points: {empty_mounts[:5]}"
    return CheckResult("S1", "Key content readable without JavaScript", w, score, _status(score, w), ev,
                       "Server-render the key facts (figures, dates, names) as text. Hydrate charts on top." if score < w else "")


def check_structured_data(soup) -> CheckResult:
    w = 15
    blocks, errors = json_ld_blocks(soup)
    types = set()
    for b in blocks:
        t = b.get("@type")
        types.update(t if isinstance(t, list) else [t] if t else [])
    useful = types & USEFUL_LD_TYPES
    if errors:
        return CheckResult("D1", "Valid structured data (JSON-LD)", w, 0, "fail", f"invalid JSON-LD: {errors[0]}", "Fix the JSON syntax; invalid blocks are ignored entirely.")
    if not blocks:
        return CheckResult("D1", "Valid structured data (JSON-LD)", w, 0, "fail", "no JSON-LD found",
                           "Add schema.org JSON-LD (e.g. Organization, Dataset, FAQPage) describing the page's key facts.")
    score = w if len(useful) >= 2 else w * 0.6
    return CheckResult("D1", "Valid structured data (JSON-LD)", w, score, _status(score, w), f"types: {sorted(types)}",
                       "" if score == w else "Add a second relevant type, e.g. FAQPage for common questions.")


def check_headings(soup) -> CheckResult:
    w = 8
    heads = [int(h.name[1]) for h in soup.find_all(re.compile(r"^h[1-6]$"))]
    h1 = heads.count(1)
    skips = [f"h{a}->h{b}" for a, b in zip(heads, heads[1:]) if b - a > 1]
    score = w
    problems = []
    if h1 != 1:
        score -= 5
        problems.append(f"{h1} <h1> elements")
    if skips:
        score -= 3
        problems.append(f"skipped levels {skips}")
    score = max(0, score)
    return CheckResult("H1", "Clear heading structure", w, score, _status(score, w),
                       "; ".join(problems) or f"outline {['h%d' % h for h in heads]}",
                       "Use exactly one <h1> and nest <h2>/<h3> without skipping levels. Styled <div>s are not headings." if problems else "")


def check_meta(soup) -> CheckResult:
    w = 7
    title = (soup.title.string or "").strip() if soup.title else ""
    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc = (desc_tag.get("content") or "").strip() if desc_tag else ""
    score = (3 if 20 <= len(title) <= 70 else 1 if title else 0) + (4 if 70 <= len(desc) <= 170 else 2 if desc else 0)
    return CheckResult("M1", "Descriptive title and meta description", w, score, _status(score, w),
                       f"title={len(title)} chars '{title[:50]}'; description={len(desc)} chars",
                       "Title 20-70 chars naming the entity and topic; description 70-170 chars summarising the key facts." if score < w else "")


def check_canonical(soup) -> CheckResult:
    w = 5
    link = soup.find("link", rel=lambda v: v and "canonical" in v)
    ok = bool(link and link.get("href", "").startswith("http"))
    return CheckResult("M2", "Canonical URL", w, w if ok else 0, "pass" if ok else "fail",
                       link.get("href") if ok else "missing", "" if ok else "Add <link rel=\"canonical\"> with the absolute URL so answers cite one address.")


def check_tables(soup) -> CheckResult:
    w = 8
    tables = soup.find_all("table")
    div_grids = soup.find_all(class_=re.compile(r"\b(grid|row|table)\b"))
    if not tables:
        score = 0 if div_grids else w
        return CheckResult("T1", "Tabular data uses semantic tables", w, score, _status(score, w),
                           f"{len(div_grids)} div-based grid/row elements, no <table>" if div_grids else "no tabular data detected",
                           "Put figures in a <table> with <th> headers and a <caption>." if div_grids else "")
    good = [t for t in tables if t.find("th")]
    captions = [t for t in tables if t.find("caption")]
    score = w * (len(good) / len(tables)) * (1.0 if captions else 0.75)
    return CheckResult("T1", "Tabular data uses semantic tables", w, round(score, 1), _status(round(score, 1), w),
                       f"{len(tables)} table(s), {len(good)} with <th>, {len(captions)} with <caption>",
                       "" if score >= w else "Add <th scope> headers and a <caption> to each data table.")


def check_lang(soup) -> CheckResult:
    w = 3
    lang = soup.html.get("lang") if soup.html else None
    return CheckResult("L1", "Document language declared", w, w if lang else 0, "pass" if lang else "fail",
                       f"lang={lang}", "" if lang else "Add lang=\"en\" (or the right code) to <html>.")


def check_alt(soup) -> CheckResult:
    w = 4
    imgs = soup.find_all("img")
    if not imgs:
        return CheckResult("A1", "Images described with alt text", w, w, "pass", "no images")
    described = [i for i in imgs if (i.get("alt") or "").strip()]
    score = round(w * len(described) / len(imgs), 1)
    return CheckResult("A1", "Images described with alt text", w, score, _status(score, w),
                       f"{len(described)}/{len(imgs)} images have alt text",
                       "" if score == w else "Describe what charts show, including the key numbers.")


def check_robots_meta(soup) -> CheckResult:
    w = 5
    tag = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    content = (tag.get("content") or "").lower() if tag else ""
    blocked = "noindex" in content or "none" in content
    return CheckResult("R1", "Page not marked noindex", w, 0 if blocked else w, "fail" if blocked else "pass",
                       f"robots meta: '{content or 'absent'}'", "Remove noindex for public investor content." if blocked else "")


def check_ai_crawlers(robots_txt: Optional[str], url: str) -> CheckResult:
    w = 10
    if robots_txt is None:
        return CheckResult("R2", "AI crawlers allowed in robots.txt", w, w, "n/a",
                           "robots.txt not provided or not found (treated as allow-all)")
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_txt.splitlines())
    path = url if url.startswith("http") else "https://example.com/"
    blocked = [bot for bot in AI_CRAWLERS if not rp.can_fetch(bot, path)]
    score = round(w * (len(AI_CRAWLERS) - len(blocked)) / len(AI_CRAWLERS), 1)
    return CheckResult("R2", "AI crawlers allowed in robots.txt", w, score, _status(score, w),
                       f"blocked: {blocked}" if blocked else f"all of {AI_CRAWLERS} allowed",
                       "" if not blocked else "Decide deliberately per bot. Blocking GPTBot/ClaudeBot/Google-Extended keeps content out of those assistants' answers.")


def check_llms_txt(llms_txt: Optional[str], is_remote: bool) -> CheckResult:
    w = 5
    if llms_txt:
        return CheckResult("R3", "llms.txt guide for AI agents", w, w, "pass", f"{len(llms_txt.splitlines())} lines")
    return CheckResult("R3", "llms.txt guide for AI agents", w, 0, "fail" if is_remote else "n/a",
                       "not found" if is_remote else "not checked for local files",
                       "Optional but cheap: publish /llms.txt listing your key pages in plain markdown.")


def run_all(soup: BeautifulSoup, robots_txt, llms_txt, target: str, is_remote: bool) -> list[CheckResult]:
    words = len(visible_text(soup).split())
    return [
        check_iframes(soup, words),
        check_server_text(soup, words),
        check_structured_data(soup),
        check_headings(soup),
        check_meta(soup),
        check_canonical(soup),
        check_tables(soup),
        check_lang(soup),
        check_alt(soup),
        check_robots_meta(soup),
        check_ai_crawlers(robots_txt, target),
        check_llms_txt(llms_txt, is_remote),
    ]


def score(results: list[CheckResult]) -> dict:
    scored = [r for r in results if r.status != "n/a"]
    possible = sum(r.weight for r in scored)
    got = sum(r.score for r in scored)
    pct = round(100 * got / possible) if possible else 0
    grade = "A" if pct >= 90 else "B" if pct >= 75 else "C" if pct >= 60 else "D" if pct >= 40 else "F"
    return {"score": pct, "grade": grade, "points": round(got, 1), "possible": possible,
            "checks": [asdict(r) for r in results]}
