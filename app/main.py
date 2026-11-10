import secrets
import struct
import zlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import config, mailer, tracking
from .db import Base, engine, get_db
from .models import Email, Event, Link, Message

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
security = HTTPBasic()

# 1x1 transparent PNG
def _make_pixel() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"\x00\x00\x00\x00\x00"  # filter byte + one transparent RGBA pixel
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


PIXEL = _make_pixel()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Email Tracker", lifespan=lifespan)


def admin(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username.encode(), config.ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(creds.password.encode(), config.ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})
    return creds.username


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")


def record(db: Session, msg: Message, request: Request, type_: str, link_id=None):
    ua = request.headers.get("user-agent", "")[:500]
    proxy = tracking.is_proxy_open(ua, msg.sent_at) if type_ == "open" else False
    db.add(Event(message_id=msg.id, type=type_, link_id=link_id, ip=client_ip(request),
                 user_agent=ua, is_proxy=proxy))
    db.commit()


# ---------- public tracking endpoints ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/t/{token}.png")
def open_pixel(token: str, request: Request, db: Session = Depends(get_db)):
    msg = db.query(Message).filter_by(token=token).first()
    if msg:
        record(db, msg, request, "open")
    return Response(PIXEL, media_type="image/png",
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})


@app.get("/c/{token}/{link_id}")
def click(token: str, link_id: int, request: Request, db: Session = Depends(get_db)):
    msg = db.query(Message).filter_by(token=token).first()
    link = db.get(Link, link_id)
    if not msg or not link or link.email_id != msg.email_id:
        raise HTTPException(404)
    record(db, msg, request, "click", link_id)
    return RedirectResponse(link.url, status_code=302)


# ---------- admin ----------
def email_stats(e: Email, db: Session) -> dict:
    ids = [m.id for m in e.messages]
    events = db.query(Event).filter(Event.message_id.in_(ids)).all() if ids else []
    opened = {ev.message_id for ev in events if ev.type == "open" and not ev.is_proxy}
    clicked = {ev.message_id for ev in events if ev.type == "click"}
    n = len(ids)
    return {"id": e.id, "subject": e.subject, "created_at": e.created_at, "sent": n,
            "opened": len(opened), "clicked": len(clicked),
            "open_rate": round(100 * len(opened) / n) if n else 0,
            "click_rate": round(100 * len(clicked) / n) if n else 0}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), _=Depends(admin)):
    emails = db.query(Email).order_by(Email.id.desc()).all()
    return templates.TemplateResponse(request, "dashboard.html",
                                      {"stats": [email_stats(e, db) for e in emails]})


@app.get("/api/emails")
def api_emails(db: Session = Depends(get_db), _=Depends(admin)):
    emails = db.query(Email).order_by(Email.id.desc()).all()
    return JSONResponse([{**email_stats(e, db), "created_at": e.created_at.isoformat()} for e in emails])


@app.get("/emails/{email_id}", response_class=HTMLResponse)
def email_detail(email_id: int, request: Request, db: Session = Depends(get_db), _=Depends(admin)):
    e = db.get(Email, email_id)
    if not e:
        raise HTTPException(404)
    rows = []
    for m in e.messages:
        evs = sorted(m.events, key=lambda x: x.ts)
        rows.append({
            "recipient": m.recipient, "token": m.token,
            "opens": sum(1 for x in evs if x.type == "open" and not x.is_proxy),
            "proxy_opens": sum(1 for x in evs if x.type == "open" and x.is_proxy),
            "clicks": sum(1 for x in evs if x.type == "click"),
            "events": evs,
        })
    urls = {l.id: l.url for l in e.links}
    return templates.TemplateResponse(request, "email_detail.html",
                                      {"email": e, "rows": rows, "urls": urls,
                                       "stats": email_stats(e, db)})


@app.get("/compose", response_class=HTMLResponse)
def compose_form(request: Request, _=Depends(admin)):
    return templates.TemplateResponse(request, "compose.html",
                                      {"smtp": mailer.smtp_configured(), "result": None})


@app.post("/compose", response_class=HTMLResponse)
def compose(request: Request, subject: str = Form(...), body_html: str = Form(...),
            recipients: str = Form(...), send: str = Form(""),
            db: Session = Depends(get_db), _=Depends(admin)):
    addrs = [a.strip() for a in recipients.replace(";", ",").replace("\n", ",").split(",") if a.strip()]
    if not addrs:
        raise HTTPException(400, "No recipients")
    email = Email(subject=subject, body_html=body_html)
    db.add(email)
    db.flush()
    link_ids = {}
    for url in tracking.extract_links(body_html):
        link = Link(email_id=email.id, url=url)
        db.add(link)
        db.flush()
        link_ids[url] = link.id
    outputs, errors = [], []
    for addr in addrs:
        msg = Message(email_id=email.id, recipient=addr, token=tracking.new_token())
        db.add(msg)
        db.flush()
        html = tracking.render_tracked(body_html, config.BASE_URL, msg.token, link_ids)
        if send and mailer.smtp_configured():
            try:
                mailer.send_html(addr, subject, html)
            except Exception as exc:  # report per-recipient, keep going
                errors.append(f"{addr}: {exc}")
        outputs.append({"recipient": addr, "html": html})
    db.commit()
    return templates.TemplateResponse(request, "compose.html", {
        "smtp": mailer.smtp_configured(),
        "result": {"email_id": email.id, "outputs": outputs, "errors": errors,
                   "sent": bool(send and mailer.smtp_configured())}})


# ---------- extension API ----------
class TrackIn(BaseModel):
    subject: str = ""
    recipients: list[str] = []
    html: str


@app.post("/api/track")
def api_track(payload: TrackIn, x_api_key: str = Header(""), db: Session = Depends(get_db)):
    """Called by the Gmail extension at send time. Returns the tracked HTML."""
    if not config.API_KEY:
        raise HTTPException(503, "TRACKER_API_KEY not configured")
    if not secrets.compare_digest(x_api_key.encode(), config.API_KEY.encode()):
        raise HTTPException(401, "Bad API key")
    email = Email(subject=payload.subject[:500] or "(no subject)", body_html=payload.html)
    db.add(email)
    db.flush()
    link_ids = {}
    for url in tracking.extract_links(payload.html):
        link = Link(email_id=email.id, url=url)
        db.add(link)
        db.flush()
        link_ids[url] = link.id
    # One body is shared by all recipients of a Gmail send, so one token per send.
    msg = Message(email_id=email.id, recipient=", ".join(payload.recipients)[:320] or "(unknown)",
                  token=tracking.new_token())
    db.add(msg)
    db.flush()
    html = tracking.render_tracked(payload.html, config.BASE_URL, msg.token, link_ids)
    db.commit()
    return {"email_id": email.id, "html": html}
