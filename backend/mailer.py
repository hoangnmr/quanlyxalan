"""SMTP email sending — standard-library transport, fail-soft.

Configuration is resolved in priority order: the DB-stored ``smtp_config`` (edited
from the admin UI) first, then environment variables (``.env``). If SMTP is not
configured or a send fails, this module NEVER raises: it logs the problem and
returns ``False`` so business operations are never blocked by mail delivery.

Transport uses only ``smtplib`` + ``email.message`` (no third-party dependency).
The DB password is stored encrypted; decryption happens in ``get_smtp_config``.
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable, Optional

logger = logging.getLogger("kbcv.mailer")
if not logger.handlers:
    logger.setLevel(logging.INFO)

SMTP_SETTING_KEY = "smtp_config"


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


@dataclass(frozen=True)
class SmtpConfig:
    enabled: bool = False
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    use_tls: bool = True
    source: str = "none"  # "db" | "env" | "none"

    @property
    def ready(self) -> bool:
        return self.enabled and bool(self.host) and bool(self.sender)


def _config_from_env() -> SmtpConfig:
    enabled = _env("SMTP_ENABLED", "false").lower() == "true"
    host = _env("SMTP_HOST")
    return SmtpConfig(
        enabled=enabled,
        host=host,
        port=int(_env("SMTP_PORT", "587") or "587"),
        username=_env("SMTP_USERNAME"),
        password=_env("SMTP_PASSWORD"),
        sender=_env("SMTP_FROM"),
        use_tls=_env("SMTP_USE_TLS", "true").lower() == "true",
        source="env" if host else "none",
    )


def _config_from_db(db) -> Optional[SmtpConfig]:
    """Load SMTP config from the app_settings table; None if absent/unusable."""
    try:
        from .models import AppSetting
        from .crypto_util import decrypt
        row = db.query(AppSetting).filter(AppSetting.key == SMTP_SETTING_KEY).first()
        if not row or not row.value:
            return None
        data = json.loads(row.value)
        return SmtpConfig(
            enabled=bool(data.get("enabled", False)),
            host=str(data.get("host") or "").strip(),
            port=int(data.get("port") or 587),
            username=str(data.get("username") or "").strip(),
            password=decrypt(str(data.get("password_enc") or "")),
            sender=str(data.get("from") or "").strip(),
            use_tls=bool(data.get("use_tls", True)),
            source="db",
        )
    except Exception as exc:  # never let a bad row break email
        logger.warning("Không đọc được cấu hình SMTP từ DB: %s", exc)
        return None


def get_smtp_config(db=None) -> SmtpConfig:
    """Resolve the effective SMTP config: DB first, then environment."""
    if db is not None:
        db_cfg = _config_from_db(db)
        # Use DB config when a host is present there (an explicitly saved row),
        # even if disabled — so the admin's on/off choice is respected.
        if db_cfg is not None and db_cfg.host:
            return db_cfg
    return _config_from_env()


def mailer_enabled(db=None) -> bool:
    """True only when SMTP is explicitly enabled and minimally configured."""
    return get_smtp_config(db).ready


def app_base_url() -> str:
    return _env("APP_BASE_URL", "http://127.0.0.1:8080").rstrip("/")


def _clean_recipients(to: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for addr in to:
        addr = (addr or "").strip()
        if addr and "@" in addr and addr not in seen:
            seen.append(addr)
    return seen


def send_email(
    to: Iterable[str], subject: str, body_text: str,
    body_html: str | None = None, config: Optional[SmtpConfig] = None,
) -> bool:
    """Send an email. Returns True on success, False otherwise. Never raises."""
    recipients = _clean_recipients(to)
    if not recipients:
        return False
    cfg = config if config is not None else _config_from_env()
    if not cfg.ready:
        logger.info("SMTP chưa cấu hình — bỏ qua email '%s' tới %s", subject, ", ".join(recipients))
        return False

    message = EmailMessage()
    message["From"] = cfg.sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body_text)
    if body_html:
        message.add_alternative(body_html, subtype="html")

    try:
        if cfg.use_tls and cfg.port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=15, context=context) as server:
                if cfg.username:
                    server.login(cfg.username, cfg.password)
                server.send_message(message)
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=15) as server:
                if cfg.use_tls:
                    server.starttls(context=ssl.create_default_context())
                if cfg.username:
                    server.login(cfg.username, cfg.password)
                server.send_message(message)
        logger.info("Đã gửi email '%s' tới %s", subject, ", ".join(recipients))
        return True
    except Exception as exc:  # fail-soft: log, never propagate
        logger.warning("Gửi email '%s' thất bại tới %s: %s", subject, ", ".join(recipients), exc)
        return False
