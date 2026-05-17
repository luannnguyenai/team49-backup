from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode

from src.config import settings


def build_password_reset_url(token: str) -> str:
    base_url = settings.frontend_base_url.rstrip("/")
    return f"{base_url}/reset-password?{urlencode({'token': token})}"


async def send_password_reset_email(email: str, token: str) -> None:
    if not settings.email_from or not settings.gmail_app_password:
        raise RuntimeError("Gmail email configuration is missing.")

    reset_url = build_password_reset_url(token)
    ttl = settings.password_reset_token_ttl_minutes

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your password"
    msg["From"] = settings.email_from
    msg["To"] = email
    msg.attach(
        MIMEText(
            f"Use this link to reset your password. The link expires in {ttl} minutes: {reset_url}",
            "plain",
        )
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:Inter,system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" style="max-width:480px;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#4f46e5,#06b6d4,#2dd4bf);border-radius:16px 16px 0 0;padding:32px 40px;text-align:center;">
          <div style="display:inline-block;background:rgba(255,255,255,0.18);border-radius:12px;padding:8px 16px;margin-bottom:12px;">
            <span style="color:#ffffff;font-size:18px;font-weight:700;letter-spacing:0.02em;">VinLearn</span>
          </div>
        </td></tr>

        <!-- Card -->
        <tr><td style="background:#ffffff;border-radius:0 0 16px 16px;border:1px solid rgba(148,163,184,0.24);border-top:none;padding:40px;">

          <h1 style="margin:0 0 12px;font-size:22px;font-weight:700;color:#020617;">Reset your password</h1>
          <p style="margin:0 0 8px;font-size:15px;color:#334155;line-height:1.6;">
            We received a request to reset the password for your account.
            Click the button below to set a new password.
          </p>
          <p style="margin:0 0 28px;font-size:13px;color:#64748b;">
            This link expires in <strong>{ttl} minutes</strong>.
          </p>

          <!-- CTA Button -->
          <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px;">
            <tr><td style="background:#020617;border-radius:9999px;padding:14px 36px;text-align:center;">
              <a href="{reset_url}" style="color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;white-space:nowrap;">
                Reset password
              </a>
            </td></tr>
          </table>

          <!-- Fallback link -->
          <p style="margin:0 0 24px;font-size:12px;color:#64748b;word-break:break-all;text-align:center;">
            Or copy this link:<br>
            <a href="{reset_url}" style="color:#0891b2;">{reset_url}</a>
          </p>

          <hr style="border:none;border-top:1px solid rgba(148,163,184,0.24);margin:0 0 24px;">

          <p style="margin:0;font-size:13px;color:#64748b;line-height:1.6;">
            If you didn't request a password reset, you can safely ignore this email.
            Your password will not be changed.
          </p>

        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 0;text-align:center;">
          <p style="margin:0;font-size:12px;color:#94a3b8;">VinLearn &mdash; Adaptive AI Education Platform</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.email_from, settings.gmail_app_password)
        server.sendmail(settings.email_from, email, msg.as_string())
