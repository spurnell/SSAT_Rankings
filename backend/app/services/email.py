"""Thin Resend wrapper. No-op with a log line when RESEND_API_KEY is unset,
so local dev can run without sending real mail."""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_magic_link(to_email: str, url: str) -> None:
    html = f"""\
<!doctype html>
<html>
<body style="font-family: -apple-system, system-ui, sans-serif; max-width: 520px; margin: 0 auto; padding: 24px;">
  <h2 style="margin-bottom: 8px;">Sign in to SSAT Rankings</h2>
  <p>Click the link below to sign in. This link expires in 15 minutes.</p>
  <p style="margin: 24px 0;">
    <a href="{url}" style="background:#0f172a;color:#fff;padding:10px 16px;border-radius:8px;text-decoration:none;">
      Sign in
    </a>
  </p>
  <p style="color:#64748b;font-size:12px;">If you didn't request this, you can ignore it.</p>
</body>
</html>
"""
    text = (
        "Sign in to SSAT Rankings\n\n"
        f"Click this link to sign in (expires in 15 minutes):\n{url}\n\n"
        "If you didn't request this, you can ignore it."
    )

    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY unset — magic link for %s would be: %s",
            to_email,
            url,
        )
        return

    import resend

    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": [to_email],
            "subject": "Sign in to SSAT Rankings",
            "html": html,
            "text": text,
        }
    )
