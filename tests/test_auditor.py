import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aeo import checks  # noqa: E402
from cli import audit  # noqa: E402

F = ROOT / "data" / "fixtures"


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def test_before_scores_low_and_after_scores_high():
    before = audit(str(F / "before.html"), str(F / "robots_before.txt"), provider="mock")
    after = audit(str(F / "after.html"), str(F / "robots_after.txt"), provider="mock")
    assert before["score"] < 30
    assert after["score"] >= 90


def test_answerability_improves():
    q = str(F / "questions.json")
    before = audit(str(F / "before.html"), questions=q, provider="mock")
    after = audit(str(F / "after.html"), questions=q, provider="mock")
    assert before["answerability"]["answered"] == 0
    assert after["answerability"]["answered"] == after["answerability"]["total"]


def test_iframe_detected():
    r = checks.check_iframes(soup('<iframe src="https://x.example/w"></iframe>'), text_words=5)
    assert r.status == "fail"


def test_visible_text_ignores_scripts():
    s = soup("<p>Revenue 10</p><script>var hidden = 'secret figure';</script>")
    assert "secret" not in checks.visible_text(s)


def test_invalid_json_ld_fails():
    r = checks.check_structured_data(soup('<script type="application/ld+json">{bad json}</script>'))
    assert r.status == "fail" and "invalid" in r.evidence


def test_heading_skip_detected():
    r = checks.check_headings(soup("<h1>A</h1><h3>B</h3>"))
    assert r.status == "partial" and "skipped" in r.evidence


def test_robots_blocking_ai_bots():
    robots = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    r = checks.check_ai_crawlers(robots, "https://example.com/page")
    assert "GPTBot" in r.evidence and r.status == "partial"


def test_noindex_fails():
    r = checks.check_robots_meta(soup('<meta name="robots" content="noindex,nofollow">'))
    assert r.status == "fail"


def test_answer_matching_is_strict_but_format_tolerant():
    from aeo.answerability import is_correct
    assert is_correct("Revenue was EUR 1204.6 million.", ["1,204.6"])
    assert is_correct("Revenue was EUR 1 204.6 million.", ["1,204.6"])
    assert not is_correct("NOT FOUND (though 1,204.6 appears elsewhere)", ["1,204.6"])
    assert not is_correct("Revenue was EUR 1,113.3 million.", ["1,204.6"])
