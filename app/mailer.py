import smtplib
from email.message import EmailMessage

from . import config


def smtp_configured() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_FROM)


def send_html(to: str, subject: str, html: str) -> None:
    msg = EmailMessage()
    msg["From"] = config.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("This email requires an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
        s.starttls()
        if config.SMTP_USER:
            s.login(config.SMTP_USER, config.SMTP_PASS)
        s.send_message(msg)
