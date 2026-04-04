"""Email service for sending invitation emails via SMTP.

Keycloak can only send its own internal emails (password reset, email
verification, etc.) and cannot send arbitrary custom emails with custom
URLs.  This service sends invitation emails directly from the Backend SDK
using Python's ``smtplib``.

Design note (M-1):
    Keycloak は任意メール送信不可のため Backend SDK が SMTP 直接送信する。
    設定は ``AuthConfig`` の ``smtp_*`` フィールドから読み込む。
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial

logger = logging.getLogger(__name__)


class EmailService:
    """SMTP-based email delivery for invitation flows.

    Runs ``smtplib`` (sync) in a thread pool via ``asyncio.to_thread`` so it
    does not block the event loop.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_addr: str,
        *,
        use_tls: bool = False,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_addr = from_addr
        self.use_tls = use_tls
        self.username = username
        self.password = password

    # ── Public API ────────────────────────────────────────────────────────────

    async def send_invitation(
        self,
        *,
        to_email: str,
        token: str,
        invited_by_name: str,
        tenant_name: str,
        base_url: str,
        custom_message: str | None = None,
    ) -> None:
        """Send an invitation email with the accept URL.

        Args:
            to_email:       Recipient email address.
            token:          Invitation token (URL-safe Base64, 43 chars).
            invited_by_name: Display name of the person who sent the invite.
            tenant_name:    Human-readable tenant / organisation name.
            base_url:       Frontend base URL (e.g. ``https://app.example.com``).
            custom_message: Optional personal note from the inviter.
        """
        accept_url = f"{base_url.rstrip('/')}/invite/accept?token={token}"
        subject = f"{tenant_name} への招待"
        html_body = self._build_html(
            invited_by_name=invited_by_name,
            tenant_name=tenant_name,
            accept_url=accept_url,
            custom_message=custom_message,
        )
        text_body = self._build_text(
            invited_by_name=invited_by_name,
            tenant_name=tenant_name,
            accept_url=accept_url,
            custom_message=custom_message,
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to_email
        # Referrer漏洩対策: メールクライアントのプリフェッチによるトークン消費を防ぐ
        # MailHog等のHTTPS非対応環境ではX-Prefetch-Imageは不要だが設定しておく
        msg["X-Entity-Ref-ID"] = token[:8]  # 短縮IDのみログ記録

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        await asyncio.to_thread(self._send_sync, to_email, msg)
        logger.info("Invitation email sent to %s (token prefix: %s)", to_email, token[:8])

    # ── Internal ──────────────────────────────────────────────────────────────

    def _send_sync(self, to_email: str, msg: MIMEMultipart) -> None:
        """Blocking SMTP send — called from a thread pool."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.sendmail(self.from_addr, [to_email], msg.as_string())

    @staticmethod
    def _build_html(
        *,
        invited_by_name: str,
        tenant_name: str,
        accept_url: str,
        custom_message: str | None,
    ) -> str:
        """Build the HTML body of the invitation email."""
        custom_block = ""
        if custom_message:
            escaped = custom_message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            custom_block = f'<p style="color:#555;font-style:italic;">"{escaped}"</p>'

        return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"></head>
<body style="font-family:sans-serif;background:#f8fafc;padding:24px;">
  <div style="max-width:520px;margin:auto;background:#fff;border-radius:8px;
              padding:32px;border:1px solid #e2e8f0;">
    <h2 style="color:#1e293b;margin-top:0;">{tenant_name} への招待</h2>
    <p><strong>{invited_by_name}</strong> さんから <strong>{tenant_name}</strong>
       への参加招待が届いています。</p>
    {custom_block}
    <p>以下のボタンからアカウントを作成してください。<br>
       <small style="color:#64748b;">このリンクの有効期限は 72 時間です。</small></p>
    <a href="{accept_url}"
       style="display:inline-block;background:#2563eb;color:#fff;padding:12px 24px;
              border-radius:6px;text-decoration:none;font-weight:bold;margin:16px 0;">
      招待を承諾する
    </a>
    <p style="font-size:12px;color:#94a3b8;margin-top:24px;">
      このメールに心当たりがない場合は無視してください。
    </p>
  </div>
</body>
</html>"""

    @staticmethod
    def _build_text(
        *,
        invited_by_name: str,
        tenant_name: str,
        accept_url: str,
        custom_message: str | None,
    ) -> str:
        """Build the plain-text fallback body."""
        lines = [
            f"{tenant_name} への招待",
            "",
            f"{invited_by_name} さんから {tenant_name} への参加招待が届いています。",
        ]
        if custom_message:
            lines += ["", f'"{custom_message}"']
        lines += [
            "",
            "以下の URL からアカウントを作成してください（有効期限: 72 時間）:",
            accept_url,
            "",
            "このメールに心当たりがない場合は無視してください。",
        ]
        return "\n".join(lines)
