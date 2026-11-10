import os
import re

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ADMIN_USER"] = "a"
os.environ["ADMIN_PASS"] = "b"
os.environ["TRACKER_API_KEY"] = "k"
os.environ["BASE_URL"] = "https://t.example.com"

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import tracking
from app.main import app

HTML = '<p><a href="https://example.com/x">x</a> <a href="mailto:a@b.c">m</a></p>'


def test_tokens_unique():
    assert len({tracking.new_token() for _ in range(500)}) == 500


def test_extract_and_render():
    assert tracking.extract_links(HTML) == ["https://example.com/x"]
    out = tracking.render_tracked(HTML, "https://t", "TOK", {"https://example.com/x": 7})
    assert "https://t/c/TOK/7" in out and "https://t/t/TOK.png" in out
    assert "mailto:a@b.c" in out


def test_proxy_detection():
    old = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert tracking.is_proxy_open("GoogleImageProxy", old)
    assert tracking.is_proxy_open("Mozilla", datetime.now(timezone.utc))
    assert not tracking.is_proxy_open("Mozilla", old)


def test_end_to_end():
    with TestClient(app) as c:
        assert c.get("/").status_code == 401
        r = c.post("/compose", auth=("a", "b"),
                   data={"subject": "Hi", "recipients": "x@y.com", "body_html": HTML})
        assert r.status_code == 200
        token = re.search(r"/t/([\w-]+)\.png", r.text).group(1)
        pix = c.get(f"/t/{token}.png")
        assert pix.headers["content-type"] == "image/png" and pix.content[:4] == b"\x89PNG"
        cl = c.get(re.search(r"/c/[\w-]+/\d+", r.text).group(0), follow_redirects=False)
        assert cl.status_code == 302 and cl.headers["location"] == "https://example.com/x"
        assert c.get("/c/bogus/1", follow_redirects=False).status_code == 404
        stats = c.get("/api/emails", auth=("a", "b")).json()
        assert stats[0]["sent"] == 1 and stats[0]["clicked"] == 1


def test_api_track():
    with TestClient(app) as c:
        body = {"subject": "S", "recipients": ["a@b.com", "c@d.com"], "html": HTML}
        assert c.post("/api/track", json=body).status_code == 401
        assert c.post("/api/track", json=body, headers={"x-api-key": "bad"}).status_code == 401
        r = c.post("/api/track", json=body, headers={"x-api-key": "k"})
        assert r.status_code == 200
        assert "/t/" in r.json()["html"] and "/c/" in r.json()["html"]
