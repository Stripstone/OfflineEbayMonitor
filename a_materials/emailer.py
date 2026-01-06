# emailer.py
"""
EMAILER — SMTP/Mailgun wrapper

Responsibilities:
- Send already-rendered subject + body
- Support HTML emails (for anchor-text links)
- Include a plain-text fallback for clients/notifications that prefer text
"""

from __future__ import annotations

import re
import smtplib
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config


_TAG_RE = re.compile(r"<[^>]+>")


def _html_to_text(html: str) -> str:
    """
    Very conservative HTML -> text fallback.
    Keeps basic readability without trying to be a full HTML parser.
    """
    if not html:
        return ""
    s = html

    # Common line breaks
    s = s.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")

    # Basic block separators
    s = s.replace("</p>", "\n").replace("</div>", "\n").replace("</tr>", "\n")

    # Non-breaking spaces
    s = s.replace("&nbsp;", " ")

    # Strip remaining tags
    s = _TAG_RE.sub("", s)

    # Normalize excessive blank lines
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s


def send_email(subject: str, body_html: str, body_text: Optional[str] = None) -> bool:
    """
    Sends email. Returns True on success, False on failure.

    - body_html: HTML version (used for clickable anchor links)
    - body_text: optional plain-text fallback. If None, we auto-generate from HTML.
    """
    if not getattr(config, "EMAIL_ENABLED", False):
        return True  # treat disabled as "success" for caller simplicity

    from_email = config.FROM_EMAIL
    to_emails = list(config.TO_EMAILS)

    # Build multipart alternative: text first, then html
    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    if body_text is None:
        body_text = _html_to_text(body_html)

    msg.attach(MIMEText(body_text or "", "plain"))
    msg.attach(MIMEText(body_html or "", "html"))

    try:
        server = smtplib.SMTP(config.MAILGUN_SMTP_SERVER, config.MAILGUN_SMTP_PORT)
        server.starttls()
        server.login(config.MAILGUN_SMTP_LOGIN, config.MAILGUN_SMTP_PASSWORD)
        server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[ERROR] Email send failed: {e}")
        return False
