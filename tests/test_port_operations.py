"""
tests/test_port_operations.py — Port operations Giai đoạn 1, 2 & 3

Covers ROADMAP_PORT_OPERATIONS.md:
  - Giai đoạn 1: CANCEL_FROM_PENDING / CANCEL_FROM_APPROVED admin-only gate.
  - Giai đoạn 2: /atb-atd, /berth-fee, /cargo-ops — staff_function gating,
    the berth-fee-before-cargo-ops hard gate, and the APPROVED precondition.
  - Giai đoạn 3: /api/work-schedule (CANCELLED excluded, ATD hides the row,
    no staff_function gate) and the "lượt gần nhất" column on the port
    vessel register.
"""
from __future__ import annotations

import os

# ── Set test DB FIRST, before any backend import ──────────────────────────────
from tests import _pgdb

_TEST_DB_URL = _pgdb.create_database("kbcv_port_ops")
os.environ["TEST_DATABASE_URL"] = _TEST_DB_URL

import pytest
from fastapi.testclient import TestClient

from backend.models import (
    Base, User, Organization, Declaration, DeclarationEvent, Vessel,
    ReportingUnit, ReportingUnitOrganization, ReportingUnitUser, ReportingUnitVessel,
)
from backend.database import engine, SessionLocal, now_iso
from backend.auth import get_password_hash
from backend.app import app, get_db

Base.metadata.create_all(bind=engine)


def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db

UNIT_ID: int | None = None
ORG_ID: int | None = None


def _seed() -> None:
    global UNIT_ID, ORG_ID
    db = SessionLocal()
    try:
        org = Organization(name="Port Ops Test Org", tax_code="POT-1", created_at=now_iso(), updated_at=now_iso())
        db.add(org)
        db.flush()

        unit = ReportingUnit(name="Port Ops Test Unit", code="POT-UNIT", is_active=1, created_at=now_iso(), updated_at=now_iso())
        db.add(unit)
        db.flush()
        db.add(ReportingUnitOrganization(reporting_unit_id=unit.id, organization_id=org.id, created_at=now_iso()))

        users = [
            ("admin1", "PLATFORM_ADMIN", None, None),
            ("security1", "PORT_STAFF", None, "SECURITY"),
            ("cargo1", "PORT_STAFF", None, "CARGO_OPS"),
            ("noviserved1", "PORT_STAFF", None, None),  # membership nhưng không có staff_function
            ("customer1", "CUSTOMER", org.id, None),
        ]
        for username, role, org_id, staff_function in users:
            user = User(
                username=username, password_hash=get_password_hash("testpass"),
                full_name=username, role=role, organization_id=org_id, is_active=1,
                created_at=now_iso(),
            )
            db.add(user)
            db.flush()
            if role == "PORT_STAFF":
                db.add(ReportingUnitUser(
                    reporting_unit_id=unit.id, user_id=user.id,
                    staff_function=staff_function, created_at=now_iso(),
                ))
        db.commit()
        UNIT_ID = unit.id
        ORG_ID = org.id
    finally:
        db.close()


_seed()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, username: str, with_unit: bool = True) -> dict:
    res = client.post("/api/auth/login", json={"username": username, "password": "testpass"})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if with_unit:
        headers["X-Reporting-Unit-ID"] = str(UNIT_ID)
    return headers


@pytest.fixture(scope="module")
def admin_headers(client):
    return _login(client, "admin1")


@pytest.fixture(scope="module")
def security_headers(client):
    return _login(client, "security1")


@pytest.fixture(scope="module")
def cargo_headers(client):
    return _login(client, "cargo1")


@pytest.fixture(scope="module")
def unaffiliated_headers(client):
    return _login(client, "noviserved1")


@pytest.fixture(scope="module")
def customer_headers(client):
    return _login(client, "customer1", with_unit=False)


def _make_declaration(status: str = "APPROVED", vessel_id: int | None = None, **overrides) -> int:
    """Insert a Declaration directly at the desired workflow_status."""
    db = SessionLocal()
    try:
        decl = Declaration(
            reference_no=f"POT-{os.urandom(4).hex()}",
            organization_id=ORG_ID,
            reporting_unit_id=UNIT_ID,
            vessel_id=vessel_id,
            declaration_date="2026-07-24",
            company_name="Port Ops Test Org",
            vessel_name="TT PORT OPS",
            registration_no=f"REG-{os.urandom(4).hex()}",
            vessel_type="Tàu container",
            vessel_class="VR-SI",
            last_port="Bến A",
            working_port="Cảng Tân Thuận",
            eta="2026-07-24T08:00",
            etd="2026-07-24T18:00",
            unload_json="{}",
            load_json="{}",
            master_name="Nguyễn Văn A",
            master_phone="0900000000",
            workflow_status=status,
            status="SUBMITTED" if status != "DRAFT" else "DRAFT",
            created_at=now_iso(),
            updated_at=now_iso(),
            **overrides,
        )
        db.add(decl)
        db.commit()
        db.refresh(decl)
        return decl.id
    finally:
        db.close()


def _make_vessel_in_register() -> int:
    db = SessionLocal()
    try:
        vessel = Vessel(
            organization_id=ORG_ID,
            name="SALAN WORK SCHEDULE",
            registration_no=f"WS-{os.urandom(4).hex()}",
            vessel_type="Chở hàng khô",
            vessel_class="VR-SI",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        db.add(vessel)
        db.flush()
        db.add(ReportingUnitVessel(reporting_unit_id=UNIT_ID, vessel_id=vessel.id, created_at=now_iso()))
        db.commit()
        db.refresh(vessel)
        return vessel.id
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# /atb-atd
# ══════════════════════════════════════════════════════════════════════════════

def test_atb_atd_security_can_set_arrival(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/atb-atd",
        json={"actual_arrival_at": "2026-07-24T09:00"},
        headers=security_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["actual_arrival_at"] == "2026-07-24T09:00"

    db = SessionLocal()
    try:
        events = db.query(DeclarationEvent).filter_by(declaration_id=decl_id).all()
        assert len(events) == 1
        event = events[0]
        assert event.action == "ATB_UPDATED"
        # Quy ước Giai đoạn 2: to_status = from_status, KHÔNG đổi workflow_status.
        assert event.to_status == event.from_status == "APPROVED"
    finally:
        db.close()


def test_atb_atd_cargo_ops_can_also_set_departure(client, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/atb-atd",
        json={"actual_departure_at": "2026-07-24T19:00"},
        headers=cargo_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["actual_departure_at"] == "2026-07-24T19:00"


def test_atb_atd_rejects_unaffiliated_staff(client, unaffiliated_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/atb-atd",
        json={"actual_arrival_at": "2026-07-24T09:00"},
        headers=unaffiliated_headers,
    )
    assert res.status_code == 403


def test_atb_atd_admin_can_set_without_staff_function(client, admin_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/atb-atd",
        json={"actual_arrival_at": "2026-07-24T09:00"},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text


def test_atb_atd_requires_approved_status(client, security_headers):
    decl_id = _make_declaration("PENDING_REVIEW")
    res = client.post(
        f"/api/declarations/{decl_id}/atb-atd",
        json={"actual_arrival_at": "2026-07-24T09:00"},
        headers=security_headers,
    )
    assert res.status_code == 409


def test_atb_atd_rejects_empty_body(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(f"/api/declarations/{decl_id}/atb-atd", json={}, headers=security_headers)
    assert res.status_code == 422


def test_atb_atd_rejects_customer(client, customer_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/atb-atd",
        json={"actual_arrival_at": "2026-07-24T09:00"},
        headers=customer_headers,
    )
    assert res.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# /berth-fee
# ══════════════════════════════════════════════════════════════════════════════

def test_berth_fee_confirmed_by_security(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["berth_fee_status"] == "CONFIRMED"
    assert body["berth_fee_confirmed_at"]
    assert body["berth_fee_confirmed_by_user_id"]


def test_berth_fee_rejects_cargo_ops_staff(client, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(f"/api/declarations/{decl_id}/berth-fee", headers=cargo_headers)
    assert res.status_code == 403


def test_berth_fee_rejects_double_confirm(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    first = client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    assert first.status_code == 200
    second = client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    assert second.status_code == 409


def test_berth_fee_requires_approved_status(client, security_headers):
    decl_id = _make_declaration("PENDING_REVIEW")
    res = client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    assert res.status_code == 409


# ══════════════════════════════════════════════════════════════════════════════
# /cargo-ops — cổng cứng: cần berth_fee_status CONFIRMED trước
# ══════════════════════════════════════════════════════════════════════════════

def test_cargo_ops_blocked_until_berth_fee_confirmed(client, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/cargo-ops",
        json={"direction": "unload"},
        headers=cargo_headers,
    )
    assert res.status_code == 409


def test_cargo_ops_confirmed_after_berth_fee(client, security_headers, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    fee = client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    assert fee.status_code == 200

    res = client.post(
        f"/api/declarations/{decl_id}/cargo-ops",
        json={"direction": "unload"},
        headers=cargo_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["unload_status"] == "CONFIRMED"
    assert body["unload_is_adhoc"] == 0
    assert body["load_status"] == "PENDING"


def test_cargo_ops_adhoc_direction(client, security_headers, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)

    res = client.post(
        f"/api/declarations/{decl_id}/cargo-ops",
        json={"direction": "load", "adhoc": True},
        headers=cargo_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["load_status"] == "CONFIRMED"
    assert body["load_is_adhoc"] == 1


def test_cargo_ops_rejects_double_confirm_same_direction(client, security_headers, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    first = client.post(
        f"/api/declarations/{decl_id}/cargo-ops", json={"direction": "unload"}, headers=cargo_headers,
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/declarations/{decl_id}/cargo-ops", json={"direction": "unload"}, headers=cargo_headers,
    )
    assert second.status_code == 409


def test_cargo_ops_rejects_security_staff(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    res = client.post(
        f"/api/declarations/{decl_id}/cargo-ops", json={"direction": "unload"}, headers=security_headers,
    )
    assert res.status_code == 403


def test_cargo_ops_admin_bypasses_staff_function_gate(client, admin_headers, security_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    res = client.post(
        f"/api/declarations/{decl_id}/cargo-ops", json={"direction": "unload"}, headers=admin_headers,
    )
    assert res.status_code == 200, res.text


def test_cargo_ops_rejects_invalid_direction(client, security_headers, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/berth-fee", headers=security_headers)
    res = client.post(
        f"/api/declarations/{decl_id}/cargo-ops", json={"direction": "sideways"}, headers=cargo_headers,
    )
    assert res.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Giai đoạn 1 — WORKFLOW_TRANSITIONS: CANCEL_FROM_PENDING / CANCEL_FROM_APPROVED
# ══════════════════════════════════════════════════════════════════════════════

def test_cancel_from_approved_requires_admin(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/workflow",
        json={"action": "CANCEL_FROM_APPROVED", "note": ""},
        headers=security_headers,
    )
    assert res.status_code == 403


def test_cancel_from_approved_by_admin_succeeds(client, admin_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/workflow",
        json={"action": "CANCEL_FROM_APPROVED", "note": ""},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["workflow_status"] == "CANCELLED"


def test_cancel_from_pending_by_admin_succeeds(client, admin_headers):
    decl_id = _make_declaration("PENDING_REVIEW")
    res = client.post(
        f"/api/declarations/{decl_id}/workflow",
        json={"action": "CANCEL_FROM_PENDING", "note": ""},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["workflow_status"] == "CANCELLED"


def test_cancel_from_pending_wrong_source_status_rejected(client, admin_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(
        f"/api/declarations/{decl_id}/workflow",
        json={"action": "CANCEL_FROM_PENDING", "note": ""},
        headers=admin_headers,
    )
    assert res.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# Giai đoạn 3 — GET /api/work-schedule
# ══════════════════════════════════════════════════════════════════════════════

def test_work_schedule_includes_in_progress_declaration(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.get("/api/work-schedule", headers=security_headers)
    assert res.status_code == 200, res.text
    ids = [item["id"] for item in res.json()["items"]]
    assert decl_id in ids


def test_work_schedule_excludes_cancelled(client, admin_headers, security_headers):
    decl_id = _make_declaration("PENDING_REVIEW")
    cancel = client.post(
        f"/api/declarations/{decl_id}/workflow",
        json={"action": "CANCEL_FROM_PENDING", "note": ""},
        headers=admin_headers,
    )
    assert cancel.status_code == 200

    res = client.get("/api/work-schedule", headers=security_headers)
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert decl_id not in ids


def test_work_schedule_excludes_declaration_with_atd(client, security_headers):
    decl_id = _make_declaration("APPROVED", actual_departure_at="2026-07-24T19:00")
    res = client.get("/api/work-schedule", headers=security_headers)
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert decl_id not in ids


def test_work_schedule_no_staff_function_gate(client, unaffiliated_headers):
    """Roadmap: tab hiện cho MỌI PORT_STAFF, không gate theo staff_function
    (khác 3 endpoint xác nhận cảng — endpoint này chỉ dùng require_port_scope)."""
    decl_id = _make_declaration("APPROVED")
    res = client.get("/api/work-schedule", headers=unaffiliated_headers)
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert decl_id in ids


def test_work_schedule_rejects_customer(client, customer_headers):
    res = client.get("/api/work-schedule", headers=customer_headers)
    assert res.status_code == 403


def test_work_schedule_admin_full_authority_sees_declarations(client, admin_headers):
    decl_id = _make_declaration("PENDING_REVIEW")
    res = client.get("/api/work-schedule", headers=admin_headers)
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["items"]]
    assert decl_id in ids


# ══════════════════════════════════════════════════════════════════════════════
# Giai đoạn 3 — GET /api/port-vessel-register: cột tham khảo "lượt gần nhất"
# ══════════════════════════════════════════════════════════════════════════════

def test_port_register_latest_call_absent_when_no_declaration(client, admin_headers):
    vessel_id = _make_vessel_in_register()
    res = client.get("/api/port-vessel-register", headers=admin_headers)
    assert res.status_code == 200
    item = next(i for i in res.json()["items"] if i["id"] == vessel_id)
    assert item["latest_call"] is None


def test_port_register_latest_call_reflects_most_recent_declaration(client, admin_headers):
    vessel_id = _make_vessel_in_register()
    _make_declaration("APPROVED", vessel_id=vessel_id)
    newest_id = _make_declaration("PENDING_REVIEW", vessel_id=vessel_id)

    res = client.get("/api/port-vessel-register", headers=admin_headers)
    assert res.status_code == 200
    item = next(i for i in res.json()["items"] if i["id"] == vessel_id)
    assert item["latest_call"] is not None
    db = SessionLocal()
    try:
        newest = db.query(Declaration).filter_by(id=newest_id).first()
        assert item["latest_call"]["reference_no"] == newest.reference_no
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# Giai đoạn 4 — POST /cancel-request (nhân viên KHÔNG PHẢI Admin)
# ══════════════════════════════════════════════════════════════════════════════

def test_cancel_request_by_security_staff_succeeds(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["cancel_requested_at"]
    assert body["cancel_requested_by_user_id"]
    assert body["workflow_status"] == "APPROVED"  # KHÔNG đổi workflow_status

    db = SessionLocal()
    try:
        events = db.query(DeclarationEvent).filter_by(declaration_id=decl_id).all()
        assert len(events) == 1
        assert events[0].action == "CANCEL_REQUESTED"
        assert events[0].to_status == events[0].from_status == "APPROVED"
    finally:
        db.close()


def test_cancel_request_by_cargo_ops_staff_succeeds(client, cargo_headers):
    decl_id = _make_declaration("PENDING_REVIEW")
    res = client.post(f"/api/declarations/{decl_id}/cancel-request", headers=cargo_headers)
    assert res.status_code == 200, res.text


def test_cancel_request_rejects_admin(client, admin_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(f"/api/declarations/{decl_id}/cancel-request", headers=admin_headers)
    assert res.status_code == 400


def test_cancel_request_rejects_double_request(client, security_headers):
    decl_id = _make_declaration("APPROVED")
    first = client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)
    assert first.status_code == 200
    second = client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)
    assert second.status_code == 409


def test_cancel_request_rejects_draft_status(client, security_headers):
    decl_id = _make_declaration("DRAFT")
    res = client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)
    assert res.status_code == 409


def test_cancel_request_rejects_customer(client, customer_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(f"/api/declarations/{decl_id}/cancel-request", headers=customer_headers)
    assert res.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Giai đoạn 4 — POST /cancel-request/reject (Admin từ chối)
# ══════════════════════════════════════════════════════════════════════════════

def test_cancel_reject_clears_request_fields(client, security_headers, admin_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)

    res = client.post(f"/api/declarations/{decl_id}/cancel-request/reject", headers=admin_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["cancel_requested_at"] is None
    assert body["cancel_requested_by_user_id"] is None
    assert body["workflow_status"] == "APPROVED"  # phiếu vẫn bình thường, không hủy


def test_cancel_reject_requires_pending_request(client, admin_headers):
    decl_id = _make_declaration("APPROVED")
    res = client.post(f"/api/declarations/{decl_id}/cancel-request/reject", headers=admin_headers)
    assert res.status_code == 409


def test_cancel_reject_rejects_non_admin(client, security_headers, cargo_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)
    res = client.post(f"/api/declarations/{decl_id}/cancel-request/reject", headers=cargo_headers)
    assert res.status_code == 403


# ══════════════════════════════════════════════════════════════════════════════
# Giai đoạn 4 — hủy thật (CANCEL_FROM_*) dọn sạch yêu cầu hủy đang chờ
# ══════════════════════════════════════════════════════════════════════════════

def test_cancel_from_approved_clears_pending_cancel_request(client, security_headers, admin_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)

    res = client.post(
        f"/api/declarations/{decl_id}/workflow",
        json={"action": "CANCEL_FROM_APPROVED", "note": ""},
        headers=admin_headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["workflow_status"] == "CANCELLED"
    assert body["cancel_requested_at"] is None
    assert body["cancel_requested_by_user_id"] is None


# ══════════════════════════════════════════════════════════════════════════════
# Giai đoạn 4 — GET /api/dashboard: cancel_queue (nhánh riêng cho PLATFORM_ADMIN)
# ══════════════════════════════════════════════════════════════════════════════

def test_dashboard_cancel_queue_includes_pending_request_for_admin(client, security_headers, admin_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)

    res = client.get("/api/dashboard", headers=admin_headers)
    assert res.status_code == 200
    queue = res.json()["cancel_queue"]
    assert queue is not None
    ids = [item["id"] for item in queue["items"]]
    assert decl_id in ids


def test_dashboard_cancel_queue_none_for_non_admin(client, security_headers):
    res = client.get("/api/dashboard", headers=security_headers)
    assert res.status_code == 200
    assert res.json()["cancel_queue"] is None


def test_dashboard_cancel_queue_excludes_resolved_request(client, security_headers, admin_headers):
    decl_id = _make_declaration("APPROVED")
    client.post(f"/api/declarations/{decl_id}/cancel-request", headers=security_headers)
    client.post(f"/api/declarations/{decl_id}/cancel-request/reject", headers=admin_headers)

    res = client.get("/api/dashboard", headers=admin_headers)
    ids = [item["id"] for item in res.json()["cancel_queue"]["items"]]
    assert decl_id not in ids
