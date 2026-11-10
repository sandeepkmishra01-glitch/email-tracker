import secrets
from datetime import datetime, timezone

from bs4 import BeautifulSoup

PROXY_MARKERS = ("googleimageproxy", "ggpht.com", "yahoomailproxy")
MIN_SECONDS_AFTER_SEND = 3


def new_token() -> str:
    return secrets.token_urlsafe(16)


def link_url(base_url: str, token: str, link_id: int) -> str:
    return f"{base_url}/c/{token}/{link_id}"


def pixel_tag(base_url: str, token: str) -> str:
    return (
        f'<img src="{base_url}/t/{token}.png" width="1" height="1" '
        'alt="" style="display:none" />'
    )


def extract_links(html: str) -> list[str]:
    """Unique http(s) hrefs in document order."""
    soup = BeautifulSoup(html, "html.parser")
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith(("http://", "https://")) and href not in seen:
            seen.add(href)
            out.append(href)
    return out


def _norm(url: str) -> str:
    return url.strip().rstrip("/").lower()


def render_tracked(html: str, base_url: str, token: str, link_ids: dict[str, int]) -> str:
    soup = BeautifulSoup(html, "html.parser")
    by_norm = {_norm(u): i for u, i in link_ids.items()}
    for a in soup.find_all("a", href=True):
        lid = link_ids.get(a["href"].strip())
        if lid is None:
            lid = by_norm.get(_norm(a["href"]))
        if lid is not None:
            a["href"] = link_url(base_url, token, lid)
    return str(soup) + pixel_tag(base_url, token)


def is_proxy_open(user_agent: str | None, sent_at: datetime | None, now: datetime | None = None) -> bool:
    ua = (user_agent or "").lower()
    if any(m in ua for m in PROXY_MARKERS):
        return True
    if sent_at is not None:
        now = now or datetime.now(timezone.utc)
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        if (now - sent_at).total_seconds() < MIN_SECONDS_AFTER_SEND:
            return True
    return False
