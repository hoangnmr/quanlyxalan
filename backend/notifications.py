"""Notification orchestration for declaration workflow events.

Resolves recipients for a declaration event and dispatches email (and, later,
Zalo). Recipient rule (per product decision):

  - Customer side: prefer ``Organization.email``; if empty, fall back to the
    personal emails of the organization's users who opted in.
  - Port side: prefer ``ReportingUnit.notify_email``; if empty, fall back to the
    personal emails of PORT_STAFF users of that unit who opted in.

Everything is fail-soft: if the mailer is disabled or no recipient is found, the
functions return quietly. Sending itself is expected to be scheduled on a
FastAPI ``BackgroundTasks`` by the caller so the request is never blocked.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from .mailer import app_base_url, get_smtp_config, send_email
from .models import (
    Organization, ReportingUnit, ReportingUnitOrganization, ReportingUnitUser, User,
)

logger = logging.getLogger("kbcv.notifications")
if not logger.handlers:
    logger.setLevel(logging.INFO)

# Opt-in flag keys stored inside users.notification_preferences_json.
EMAIL_WORKFLOW_KEY = "email_workflow_updates"


def _wants_workflow_email(user: User) -> bool:
    try:
        stored = json.loads(user.notification_preferences_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return bool(stored.get(EMAIL_WORKFLOW_KEY, False))


def resolve_customer_emails(db: Session, organization_id: int | None) -> list[str]:
    """Emails for a customer organization: org email first, else opted-in users."""
    if not organization_id:
        return []
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org and (org.email or "").strip():
        return [org.email.strip()]
    users = db.query(User).filter(
        User.organization_id == organization_id, User.is_active == 1
    ).all()
    return [u.email.strip() for u in users if (u.email or "").strip() and _wants_workflow_email(u)]


def resolve_port_staff_emails(db: Session, organization_id: int | None) -> list[str]:
    """Emails for the port(s) serving a customer org: unit notify_email first,
    else opted-in PORT_STAFF members of those units."""
    if not organization_id:
        return []
    unit_ids = [
        row[0] for row in db.query(ReportingUnitOrganization.reporting_unit_id)
        .filter(ReportingUnitOrganization.organization_id == organization_id).all()
    ]
    if not unit_ids:
        return []
    emails: list[str] = []
    for unit_id in unit_ids:
        unit = db.query(ReportingUnit).filter(ReportingUnit.id == unit_id).first()
        if unit and (unit.notify_email or "").strip():
            emails.append(unit.notify_email.strip())
            continue
        # Fallback: opted-in PORT_STAFF members of this unit.
        staff = (
            db.query(User)
            .join(ReportingUnitUser, ReportingUnitUser.user_id == User.id)
            .filter(
                ReportingUnitUser.reporting_unit_id == unit_id,
                User.role == "PORT_STAFF",
                User.is_active == 1,
            )
            .all()
        )
        emails.extend(
            u.email.strip() for u in staff
            if (u.email or "").strip() and _wants_workflow_email(u)
        )
    # De-duplicate, preserve order.
    seen: list[str] = []
    for e in emails:
        if e and e not in seen:
            seen.append(e)
    return seen


def _declaration_link(declaration) -> str:
    return f"{app_base_url()}/#declarations"


def notify_declaration_submitted(db: Session, declaration, is_resubmit: bool, background=None) -> None:
    """Event 1 & 2: customer submitted (or re-submitted) → notify port staff."""
    cfg = get_smtp_config(db)
    if not cfg.ready:
        return
    recipients = resolve_port_staff_emails(db, declaration.organization_id)
    if not recipients:
        return
    action_label = "được gửi lại sau khi bổ sung" if is_resubmit else "mới được gửi"
    subject = f"[Phiếu {'gửi lại' if is_resubmit else 'mới'}] {declaration.reference_no} · {declaration.vessel_name}"
    body = (
        f"Có phiếu khai báo {action_label} và đang chờ Cảng xử lý.\n\n"
        f"Số phiếu: {declaration.reference_no}\n"
        f"Phương tiện: {declaration.vessel_name} ({declaration.registration_no})\n"
        f"Doanh nghiệp: {declaration.company_name}\n"
        f"Loại phiếu: {'Rời cảng' if declaration.movement_type == 'DEPARTURE' else 'Vào cảng'}\n\n"
        f"Mở phần mềm để xử lý: {_declaration_link(declaration)}\n"
    )
    _dispatch(background, recipients, subject, body, cfg)


def notify_declaration_workflow(db: Session, declaration, action: str, note: str = "", background=None) -> None:
    """Event 3 & 4: port approved / requested changes → notify customer."""
    cfg = get_smtp_config(db)
    if not cfg.ready:
        return
    if action not in ("PORT_APPROVE", "REQUEST_CHANGES"):
        return
    recipients = resolve_customer_emails(db, declaration.organization_id)
    if not recipients:
        return
    if action == "PORT_APPROVE":
        subject = f"[Đã duyệt] {declaration.reference_no} · {declaration.vessel_name}"
        body = (
            f"Phiếu khai báo của bạn đã được Cảng xác nhận hoàn tất.\n\n"
            f"Số phiếu: {declaration.reference_no}\n"
            f"Phương tiện: {declaration.vessel_name} ({declaration.registration_no})\n\n"
            f"Xem chi tiết: {_declaration_link(declaration)}\n"
        )
    else:  # REQUEST_CHANGES
        subject = f"[Yêu cầu bổ sung] {declaration.reference_no} · {declaration.vessel_name}"
        body = (
            f"Cảng yêu cầu bổ sung cho phiếu khai báo của bạn.\n\n"
            f"Số phiếu: {declaration.reference_no}\n"
            f"Phương tiện: {declaration.vessel_name} ({declaration.registration_no})\n"
            f"Lý do: {note or '(không có ghi chú)'}\n\n"
            f"Vui lòng mở phần mềm để bổ sung và gửi lại: {_declaration_link(declaration)}\n"
        )
    _dispatch(background, recipients, subject, body, cfg)


def _dispatch(background, recipients: list[str], subject: str, body: str, cfg=None) -> None:
    """Schedule the send on BackgroundTasks if available, else send inline.
    Never raises. The resolved SMTP config is passed through so the background
    task doesn't need its own DB session."""
    try:
        if background is not None:
            background.add_task(send_email, list(recipients), subject, body, None, cfg)
        else:
            send_email(recipients, subject, body, config=cfg)
    except Exception as exc:  # fail-soft
        logger.warning("Không thể lên lịch gửi email '%s': %s", subject, exc)
