"""Load a page the way a non-JavaScript crawler sees it: raw HTML, robots.txt, llms.txt."""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

UA = "aeo-auditor/1.0 (+https://github.com/barath2211/ai-crawler-aeo-auditor)"


@dataclass
class PageSource:
    target: str
    html: str
    robots_txt: Optional[str]
    llms_txt: Optional[str]
    is_remote: bool


def _get(url: str, timeout: float = 10) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            return resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def load(target: str, robots_path: Optional[str] = None, llms_path: Optional[str] = None) -> PageSource:
    if target.startswith(("http://", "https://")):
        html = _get(target)
        if html is None:
            raise RuntimeError(f"Could not fetch {target}")
        parts = urllib.parse.urlsplit(target)
        root = f"{parts.scheme}://{parts.netloc}"
        robots = Path(robots_path).read_text() if robots_path else _get(f"{root}/robots.txt")
        llms = Path(llms_path).read_text() if llms_path else _get(f"{root}/llms.txt")
        return PageSource(target, html, robots, llms, True)

    html = Path(target).read_text(encoding="utf-8")
    robots = Path(robots_path).read_text(encoding="utf-8") if robots_path else None
    llms = Path(llms_path).read_text(encoding="utf-8") if llms_path else None
    return PageSource(target, html, robots, llms, False)
