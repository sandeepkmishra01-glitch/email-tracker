import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "")  # no default: the dashboard stays locked until this is set
API_KEY = os.getenv("TRACKER_API_KEY", "")
# Privacy: store truncated IPs (/24 for IPv4, /48 for IPv6) unless STORE_FULL_IP=true.
STORE_FULL_IP = os.getenv("STORE_FULL_IP", "false").lower() in ("1", "true", "yes")
# Privacy: blank the IP and user agent of events older than this many days (0 = keep forever).
SCRUB_AFTER_DAYS = int(os.getenv("SCRUB_AFTER_DAYS", "90"))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite:///./tracker.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url
