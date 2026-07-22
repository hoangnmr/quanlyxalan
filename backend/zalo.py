"""Zalo notification adapter — scaffold only, DISABLED by default.

Sending a ZNS (Zalo Notification Service) message requires a verified Zalo
Official Account, a ZNS template that the business creates in Zalo Cloud Account
and gets APPROVED by Zalo, plus a paid balance. None of that exists yet, so this
adapter is a no-op until ``ZALO_ENABLED=true`` and credentials are supplied.

It mirrors the ``integrations.py`` adapter pattern. When the OA + approved
template are ready, implement ``send()`` to call the ZNS API using
``ZALO_OA_TOKEN`` and ``ZALO_TEMPLATE_ID``. Until then it never sends and never
raises.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("kbcv.zalo")
if not logger.handlers:
    logger.setLevel(logging.INFO)


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name, default) or "").strip()


def zalo_enabled() -> bool:
    """True only when explicitly enabled AND credentials + template are present."""
    if _env("ZALO_ENABLED", "false").lower() != "true":
        return False
    return bool(_env("ZALO_OA_TOKEN")) and bool(_env("ZALO_TEMPLATE_ID"))


def send_zns(phone: str, template_data: dict) -> bool:
    """Send a ZNS message. Currently a disabled no-op. Never raises.

    Returns True only if actually sent (never, until enabled + implemented).
    """
    if not zalo_enabled():
        logger.info("Zalo chưa cấu hình — bỏ qua ZNS tới %s", phone)
        return False
    # TODO: khi có OA + mẫu ZNS được Zalo duyệt, gọi API ZNS ở đây bằng
    # ZALO_OA_TOKEN + ZALO_TEMPLATE_ID (ZALO_BASE_URL). Hiện chưa triển khai.
    logger.warning("Zalo được bật nhưng chưa triển khai gửi ZNS — bỏ qua tới %s", phone)
    return False
