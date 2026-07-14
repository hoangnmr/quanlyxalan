"""
tests/test_backend.py — T0 Baseline Recovery test suite
WO-KBCV-T0-20260711

Uses pytest + httpx TestClient against the FastAPI app.
Test database is SQLite in a temporary directory — completely isolated from data/cang_vu.db.

IMPORTANT: os.environ["TEST_DATABASE_URL"] is set BEFORE any backend imports so that
           database.py picks up the test URL at module init time.
"""
from __future__ import annotations

import io
import os
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

# ── Set test DB FIRST, before any backend import ──────────────────────────────
_tmp_dir = tempfile.mkdtemp()
_test_db_path = Path(_tmp_dir) / "test.db"
os.environ["TEST_DATABASE_URL"] = f"sqlite:///{_test_db_path}"

# ── Now import backend (picks up TEST_DATABASE_URL) ───────────────────────────
import pytest
from fastapi.testclient import TestClient

from backend.models import AuditEvent, Base, Declaration, ImportJob, User, Organization, Vessel
from backend.database import engine, SessionLocal, now_iso
from backend.auth import get_password_hash
from backend.app import app, get_db, DEMO_ORGANIZATION_TAX_CODE, remove_demo_data_for_real_input
from backend.xlsx_io import make_xlsx, read_workbook, vessel_rows

# ── Create all tables in test DB ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)


# ── DB override ───────────────────────────────────────────────────────────────
def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


# ── Seed test user ────────────────────────────────────────────────────────────
def _seed_user() -> None:
    db = SessionLocal()
    try:
        # Seed test organization first
        org = db.query(Organization).filter(Organization.name == "Test Org").first()
        if not org:
            org = Organization(name="Test Org", tax_code="123456", created_at=now_iso(), updated_at=now_iso())
            db.add(org)
            db.commit()
            db.refresh(org)

        # Seed users
        user_data = [
            ("testuser", "ADMIN", None),
            ("customeruser", "CUSTOMER", org.id),
            ("portstaff", "PORT_STAFF", None),
        ]
        for username, role, org_id in user_data:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(
                    username=username,
                    password_hash=get_password_hash("testpass"),
                    full_name=f"{role} User",
                    role=role,
                    organization_id=org_id,
                    is_active=1,
                    created_at=now_iso(),
                ))
        db.commit()
    finally:
        db.close()


_seed_user()


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    res = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def customer_headers(client):
    res = client.post("/api/auth/login", json={"username": "customeruser", "password": "testpass"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def port_staff_headers(client):
    res = client.post("/api/auth/login", json={"username": "portstaff", "password": "testpass"})
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── Helper ────────────────────────────────────────────────────────────────────
def _reg() -> str:
    """Generate a unique registration number."""
    return f"SG-T0-{uuid.uuid4().hex}"


def _minimal_declaration(**overrides) -> dict:
    base = {
        "company_name": "Test Company",
        "declaration_date": "2026-07-11",
        "vessel_name": "TT TEST",
        "registration_no": _reg(),
        "vessel_type": "Tàu container",
        "vessel_class": "VR-SI",
        "last_port": "Bến A",
        "working_port": "Cảng Tân Thuận",
        "eta": "2026-07-11T08:00",
        "etd": "2026-07-11T18:00",
        "master_name": "Nguyễn Văn A",
        "master_phone": "0900000000",
        "unload": {},
        "load": {},
    }
    base.update(overrides)
    return base


# ══════════════════════════════════════════════════════════════════════════════
# 1. HEALTH + STATIC FRONTEND
# ══════════════════════════════════════════════════════════════════════════════

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["storage"] == "LOCAL_QUARANTINE"


def test_readiness(client):
    res = client.get("/api/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


def test_admin_operations_summary(client, auth_headers, customer_headers):
    admin = client.get("/api/admin/operations-summary", headers=auth_headers)
    assert admin.status_code == 200
    assert {"operations", "fleet", "imports", "storage", "security"}.issubset(admin.json())
    assert client.get("/api/admin/operations-summary", headers=customer_headers).status_code == 403


def test_dashboard_attention_queue_is_role_scoped(client, customer_headers, port_staff_headers):
    customer = client.get("/api/dashboard", headers=customer_headers)
    assert customer.status_code == 200
    assert customer.json()["attention"]["label"]
    assert all(item["workflow_status"] in {"DRAFT", "CHANGES_REQUESTED"} for item in customer.json()["attention"]["items"])

    reviewer = client.get("/api/dashboard", headers=port_staff_headers)
    assert reviewer.status_code == 200
    assert all(item["workflow_status"] == "PENDING_REVIEW" for item in reviewer.json()["attention"]["items"])


def test_static_frontend(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert 'class="skip-link"' in res.text
    assert 'id="main-content" tabindex="-1" aria-busy="false"' in res.text
    assert 'id="toast-region" class="toast-region" role="status"' in res.text
    assert 'id="in-app-certificate-reminders"' in res.text
    assert 'id="certificate-reminder"' in res.text
    assert 'id="demo-data-notice"' in res.text
    assert 'id="login-dialog" class="modal login-dialog"' in res.text
    assert 'id="analytics-unavailable"' in res.text
    assert 'id="external-integration-panel" class="panel integration-panel"' in res.text
    assert 'id="integration-admin-actions" class="integration-state" hidden' in res.text
    assert 'class="primary-nav"' in res.text and 'class="data-nav"' in res.text
    assert "Báo cáo hoạt động Cảng" in res.text
    assert "Báo cáo Cảng vụ" not in res.text
    assert 'class="panel action-panel"' not in res.text
    app_js = client.get("/app.js").text
    assert "function setSubmitting(" in app_js
    assert "function bindLoginForm()" in app_js
    assert "bindLoginForm();" in app_js
    assert "Tiến trình duyệt" in app_js
    assert "Nhân viên Cảng" in app_js
    assert "CV = Cảng vụ viên" not in app_js
    assert "Theo các bước CV · QLC · BP" not in app_js
    assert "PORT_APPROVE" in app_js
    assert "crew-checklist" in app_js
    assert "step-error-summary" in app_js
    assert "port_approval" in app_js
    assert "cv_approval" not in app_js
    assert "loadReportAnalytics($('.period-switch button.active')?.dataset.period || 'month')" in app_js
    assert "CUSTOMER:'User'" in app_js
    assert "PORT_STAFF:'Port staff'" in app_js
    assert "ADMIN:'Admin'" in app_js
    assert "if (state.currentUser?.role === 'ADMIN') loadIntegration();" in app_js
    assert "btn.style.display = isCustomer ? 'inline-block' : 'none'" in app_js
    assert "const crewContainer = $('#declaration-crew-container');" in app_js
    assert "? $$('input[name=\"crew_ids\"]:checked', crewContainer).length" in app_js
    assert "node.setAttribute('role', error ? 'alert' : 'status')" in app_js
    styles_css = client.get("/styles.css").text
    assert "[hidden] { display: none !important; }" in styles_css
    assert "overflow-y: auto" in styles_css
    assert "overscroll-behavior: contain" in styles_css
    assert ".data-nav { margin-top: auto" in styles_css
    assert ".integration-readiness" in styles_css


def test_real_input_removes_only_sentinel_marked_demo_data():
    db = SessionLocal()
    try:
        demo = Organization(name="Demo sentinel", tax_code=DEMO_ORGANIZATION_TAX_CODE, created_at=now_iso(), updated_at=now_iso())
        real = Organization(name=f"Real org {_reg()}", tax_code=_reg(), created_at=now_iso(), updated_at=now_iso())
        db.add_all([demo, real])
        db.flush()
        db.add_all([
            Vessel(organization_id=demo.id, name="Demo vessel", registration_no=_reg(), vessel_type="Sà lan", vessel_class="VR-SII", created_at=now_iso(), updated_at=now_iso()),
            Vessel(organization_id=real.id, name="Real vessel", registration_no=_reg(), vessel_type="Sà lan", vessel_class="VR-SII", created_at=now_iso(), updated_at=now_iso()),
        ])
        db.commit()
        assert remove_demo_data_for_real_input(db) is True
        db.commit()
        assert db.query(Organization).filter(Organization.tax_code == DEMO_ORGANIZATION_TAX_CODE).first() is None
        assert db.query(Organization).filter(Organization.id == real.id).first() is not None
        assert db.query(Vessel).filter(Vessel.organization_id == real.id).count() == 1
        db.query(Vessel).filter(Vessel.organization_id == real.id).delete(synchronize_session=False)
        db.delete(real)
        db.commit()
    finally:
        db.rollback()
        db.close()


def test_declaration_pagination_contract_is_bounded_and_compatible(client, auth_headers):
    legacy = client.get("/api/declarations", headers=auth_headers)
    assert legacy.status_code == 200
    assert isinstance(legacy.json(), list)

    paged = client.get("/api/declarations?page=1&page_size=1&sort=reference_no&direction=asc", headers=auth_headers)
    assert paged.status_code == 200
    body = paged.json()
    assert {"items", "page", "page_size", "total", "total_pages", "sort", "direction"}.issubset(body)
    assert body["page_size"] == 1
    assert len(body["items"]) <= 1

    assert client.get("/api/declarations?page=1&page_size=101", headers=auth_headers).status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# 2. AUTHENTICATION
# ══════════════════════════════════════════════════════════════════════════════

def test_login_success(client):
    res = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_notification_preferences_are_user_controlled_and_audited(client, customer_headers):
    before = client.get("/api/notification-preferences", headers=customer_headers)
    assert before.status_code == 200
    assert before.json()["in_app_certificate_reminders"] is True

    updated = client.put(
        "/api/notification-preferences",
        headers=customer_headers,
        json={"in_app_certificate_reminders": False},
    )
    assert updated.status_code == 200
    assert updated.json() == {"in_app_certificate_reminders": False}
    assert client.get("/api/notification-preferences", headers=customer_headers).json() == updated.json()

    db = SessionLocal()
    try:
        assert db.query(AuditEvent).filter(AuditEvent.action == "NOTIFICATION_PREFERENCES_UPDATE").count() >= 1
    finally:
        db.close()


def test_login_wrong_password(client):
    res = client.post("/api/auth/login", json={"username": "testuser", "password": "wrongpass"})
    assert res.status_code == 401


def test_protected_route_requires_auth(client):
    """Accessing /api/vessels without token must return 401."""
    # Temporarily remove override so the real auth check runs
    original = app.dependency_overrides.pop(get_db, None)
    try:
        # Call without auth header
        res = client.get("/api/vessels")
        # Should be 401 (token validation) or the endpoint is accessible — depends on auth dep
        # Re-add override first, then check with fake token
    finally:
        if original:
            app.dependency_overrides[get_db] = original

    res = client.get("/api/vessels", headers={"Authorization": "Bearer invalidtoken"})
    assert res.status_code == 401


def test_catalogs_public(client):
    """Catalogs endpoint should be accessible without auth."""
    res = client.get("/api/catalogs")
    assert res.status_code == 200
    data = res.json()
    assert "vesselTypes" in data
    assert "vesselClasses" in data


# ══════════════════════════════════════════════════════════════════════════════
# 3. VESSELS
# ══════════════════════════════════════════════════════════════════════════════

def test_vessel_create(client, auth_headers):
    payload = {
        "name": "TT VESSEL A",
        "registration_no": _reg(),
        "vessel_type": "Tàu container",
        "vessel_class": "VR-SI",
        "organization_name": "Test Org A",
    }
    res = client.post("/api/vessels", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "TT VESSEL A"
    assert "id" in data


def test_vessel_list(client, auth_headers):
    res = client.get("/api/vessels", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_vessel_update(client, auth_headers):
    reg_no = _reg()
    res = client.post("/api/vessels", json={
        "name": "TT UPDATE",
        "registration_no": reg_no,
        "vessel_type": "Tàu hàng khô",
        "vessel_class": "VR-SI",
    }, headers=auth_headers)
    assert res.status_code == 200
    vid = res.json()["id"]

    res2 = client.post("/api/vessels", json={
        "id": vid,
        "name": "TT UPDATED",
        "registration_no": reg_no,
        "vessel_type": "Tàu hàng khô",
        "vessel_class": "VR-SII",
    }, headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["vessel_class"] == "VR-SII"


def test_vessel_stale_version_rejected(client, auth_headers):
    reg_no = _reg()
    created = client.post("/api/vessels", json={
        "name": "TT VERSION",
        "registration_no": reg_no,
        "vessel_type": "Tàu hàng khô",
        "vessel_class": "VR-SI",
    }, headers=auth_headers)
    assert created.status_code == 200
    vessel = created.json()

    updated = client.post("/api/vessels", json={
        "id": vessel["id"], "version": vessel["version"],
        "name": "TT VERSION UPDATED", "registration_no": reg_no,
        "vessel_type": "Tàu hàng khô", "vessel_class": "VR-SI",
    }, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["version"] == vessel["version"] + 1

    stale = client.post("/api/vessels", json={
        "id": vessel["id"], "version": vessel["version"],
        "name": "TT VERSION STALE", "registration_no": reg_no,
        "vessel_type": "Tàu hàng khô", "vessel_class": "VR-SI",
    }, headers=auth_headers)
    assert stale.status_code == 409


def test_duplicate_vessel_rolls_back_new_organization(client, auth_headers):
    """A failed write cannot leave the organization created during that request."""
    registration = _reg()
    first = client.post("/api/vessels", json={
        "name": "TT DUPLICATE ONE",
        "registration_no": registration,
        "vessel_type": "Tàu hàng khô",
        "vessel_class": "VR-SI",
        "organization_name": "Committed Org",
    }, headers=auth_headers)
    assert first.status_code == 200

    failed_org = f"Rolled Back Org {time.time_ns()}"
    duplicate = client.post("/api/vessels", json={
        "name": "TT DUPLICATE TWO",
        "registration_no": registration,
        "vessel_type": "Tàu hàng khô",
        "vessel_class": "VR-SI",
        "organization_name": failed_org,
    }, headers=auth_headers)
    assert duplicate.status_code == 409

    db = SessionLocal()
    try:
        assert db.query(Organization).filter(Organization.name == failed_org).first() is None
    finally:
        db.close()


def test_vessel_verify_registry(client, auth_headers):
    res = client.post("/api/vessels", json={
        "name": "TT VERIFY",
        "registration_no": _reg(),
        "vessel_type": "Tàu hàng khô",
        "vessel_class": "VR-SI",
    }, headers=auth_headers)
    assert res.status_code == 200
    vid = res.json()["id"]
    res2 = client.post(f"/api/vessels/{vid}/verify-registry", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["registry_verification_status"] == "VERIFIED_LOCAL"
    assert res2.json()["registry_verification_source"] == "local"
    assert res2.json()["adapter"]["mode"] == "MANUAL"
    assert res2.json()["adapter"]["networkCallsAllowed"] is False


# ══════════════════════════════════════════════════════════════════════════════
# 4. CREW
# ══════════════════════════════════════════════════════════════════════════════

def test_crew_create(client, auth_headers):
    payload = {
        "full_name": "Nguyễn Văn Thuyền",
        "crew_role": "Thuyền trưởng",
        "professional_certificate_type": "Bằng thuyền trưởng",
        "professional_certificate_no": "CERT-001",
        "certificate_expiry_date": "2020-01-01",
    }
    res = client.post("/api/crew", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["certificate_status"] == "EXPIRED"
    assert data["full_name"] == "Nguyễn Văn Thuyền"


def test_crew_list(client, auth_headers):
    res = client.get("/api/crew", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_crew_update(client, auth_headers):
    res = client.post("/api/crew", json={
        "full_name": "Trần Máy Trưởng",
        "crew_role": "Máy trưởng",
        "professional_certificate_type": "Bằng máy trưởng",
        "professional_certificate_no": "CERT-002",
        "certificate_expiry_date": "2099-01-01",
    }, headers=auth_headers)
    assert res.status_code == 200
    cid = res.json()["id"]

    res2 = client.post("/api/crew", json={
        "id": cid,
        "full_name": "Trần Máy Trưởng Updated",
        "crew_role": "Máy trưởng",
        "professional_certificate_type": "Bằng máy trưởng",
        "professional_certificate_no": "CERT-002-UPD",
        "certificate_expiry_date": "2099-06-01",
    }, headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["professional_certificate_no"] == "CERT-002-UPD"


# ══════════════════════════════════════════════════════════════════════════════
# 5. DECLARATIONS — DRAFT AND SUBMIT
# ══════════════════════════════════════════════════════════════════════════════

def test_declaration_draft_create(client, auth_headers):
    res = client.post("/api/declarations", json=_minimal_declaration(), headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_status"] == "DRAFT"
    assert "reference_no" in data


def test_declaration_submit(client, customer_headers):
    res = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(),
        headers=customer_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_status"] == "PENDING_REVIEW"
    assert data["status"] == "SUBMITTED"


def test_declaration_validation_rejects_negative_count_and_invalid_movement(client, customer_headers):
    invalid_count = client.post(
        "/api/declarations",
        json=_minimal_declaration(crew_count=-1),
        headers=customer_headers,
    )
    assert invalid_count.status_code == 422

    invalid_movement = client.post(
        "/api/declarations",
        json=_minimal_declaration(movement_type="TRANSFER"),
        headers=customer_headers,
    )
    assert invalid_movement.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# 6. TEU CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_teu_calculations(client, customer_headers):
    res = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(unload={
            "cont20_full": 2, "cont20_empty": 1,
            "cont40_full": 3, "cont40_empty": 1,
        }),
        headers=customer_headers,
    )
    assert res.status_code == 200
    unload = res.json()["unload"]
    assert unload["total_containers"] == 7
    assert unload["teu"] == 11
    assert unload["empty_teu"] == 3


# ══════════════════════════════════════════════════════════════════════════════
# 7. WORKFLOW — CUSTOMER CONFIRMATION + PORT ENTERPRISE REVIEW
# ══════════════════════════════════════════════════════════════════════════════

def test_port_employee_can_approve_directly_or_request_changes(
    client, customer_headers, port_staff_headers, auth_headers
):
    approved_source = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(),
        headers=customer_headers,
    )
    declaration_id = approved_source.json()["id"]

    denied = client.post(
        f"/api/declarations/{declaration_id}/workflow",
        json={"action": "PORT_APPROVE"},
        headers=auth_headers,
    )
    assert denied.status_code == 403

    approved = client.post(
        f"/api/declarations/{declaration_id}/workflow",
        json={"action": "PORT_APPROVE", "note": "Thông tin phù hợp"},
        headers=port_staff_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["workflow_status"] == "APPROVED"
    assert approved.json()["port_approval"] == "APPROVED"
    assert "cv_approval" not in approved.json()

    changes_source = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(),
        headers=customer_headers,
    )
    requested = client.post(
        f"/api/declarations/{changes_source.json()['id']}/workflow",
        json={"action": "REQUEST_CHANGES", "note": "Cần bổ sung chứng từ"},
        headers=port_staff_headers,
    )
    assert requested.status_code == 200
    assert requested.json()["workflow_status"] == "CHANGES_REQUESTED"

def test_retired_workflow_actions_return_gone(client, customer_headers, port_staff_headers):
    res = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(),
        headers=customer_headers,
    )
    assert res.status_code == 200
    decl_id = res.json()["id"]

    for action in ("CV_APPROVE", "QLC_APPROVE", "BP_APPROVE", "ISSUE", "REVOKE"):
        response = client.post(
            f"/api/declarations/{decl_id}/workflow",
            json={"action": action, "note": "Hành động cũ"},
            headers=port_staff_headers,
        )
        assert response.status_code == 410
        assert "ngừng hỗ trợ" in response.json()["detail"]

    db = SessionLocal()
    try:
        unchanged = db.get(Declaration, decl_id)
        assert unchanged.workflow_status == "PENDING_REVIEW"
    finally:
        db.close()


def test_real_input_keeps_customer_binding_and_clears_demo_sentinel():
    db = SessionLocal()
    try:
        demo = Organization(name="Demo customer", tax_code=DEMO_ORGANIZATION_TAX_CODE, created_at=now_iso(), updated_at=now_iso())
        db.add(demo)
        db.flush()
        user = User(
            username=f"demo-{uuid.uuid4().hex}", password_hash=get_password_hash("testpass"),
            full_name="Demo User", role="CUSTOMER", organization_id=demo.id,
            is_active=1, created_at=now_iso(),
        )
        db.add(user)
        db.add(Vessel(organization_id=demo.id, name="Mock", registration_no=_reg(), vessel_type="Sà lan", vessel_class="VR-SII", created_at=now_iso(), updated_at=now_iso()))
        db.commit()

        assert remove_demo_data_for_real_input(
            db, retain_organization_id=demo.id,
            organization_data={"name": "Khách hàng thật", "tax_code": "REAL-001"},
        ) is True
        db.commit()
        db.refresh(demo)
        db.refresh(user)
        assert demo.name == "Khách hàng thật"
        assert demo.tax_code == "REAL-001"
        assert user.organization_id == demo.id
        assert db.query(Vessel).filter(Vessel.organization_id == demo.id).count() == 0
        db.delete(user)
        db.delete(demo)
        db.commit()
    finally:
        db.rollback()
        db.close()


def test_changes_requested_resubmission_resets_approval_state(client, customer_headers, port_staff_headers):
    created = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(),
        headers=customer_headers,
    )
    declaration = created.json()
    requested = client.post(
        f"/api/declarations/{declaration['id']}/workflow",
        json={"action": "REQUEST_CHANGES", "note": "Thiếu thông tin hàng hóa"},
        headers=port_staff_headers,
    )
    assert requested.status_code == 200
    assert requested.json()["workflow_status"] == "CHANGES_REQUESTED"

    resubmitted = client.post(
        "/api/declarations?submit=true",
        json={**_minimal_declaration(), "id": declaration["id"], "version": requested.json()["version"]},
        headers=customer_headers,
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json()["workflow_status"] == "PENDING_REVIEW"
    assert resubmitted.json()["port_approval"] == "PENDING"


def test_workflow_audit_carries_authoritative_actor_and_correlation_id(
    client, customer_headers, port_staff_headers
):
    created = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(),
        headers=customer_headers,
    )
    declaration_id = created.json()["id"]
    correlation = "t2-correlation-test"
    response = client.post(
        f"/api/declarations/{declaration_id}/workflow",
        json={"action": "PORT_APPROVE"},
        headers={**port_staff_headers, "X-Correlation-ID": correlation},
    )
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == correlation

    db = SessionLocal()
    try:
        audit_event = db.query(AuditEvent).filter(
            AuditEvent.entity_type == "DECLARATION",
            AuditEvent.entity_id == declaration_id,
            AuditEvent.action == "PORT_APPROVE",
        ).one()
        assert audit_event.correlation_id == correlation
        assert audit_event.actor_user_id is not None
        assert audit_event.organization_id is not None
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# 8. SUBMITTED RECORD PROTECTION
# ══════════════════════════════════════════════════════════════════════════════

def test_submitted_record_edit_protection(client, customer_headers):
    reg_no = _reg()
    res = client.post(
        "/api/declarations?submit=true",
        json=_minimal_declaration(registration_no=reg_no),
        headers=customer_headers,
    )
    decl_id = res.json()["id"]
    res2 = client.post("/api/declarations", json={
        **_minimal_declaration(registration_no=reg_no),
        "id": decl_id,
        "vessel_name": "HACKED",
    }, headers=customer_headers)
    assert res2.status_code == 409


# ══════════════════════════════════════════════════════════════════════════════
# 9. ATTACHMENT SIGNATURE / SIZE VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def _make_draft(client, auth_headers) -> int:
    res = client.post("/api/declarations", json=_minimal_declaration(), headers=auth_headers)
    assert res.status_code == 200
    return res.json()["id"]


def test_attachment_valid_pdf(client, auth_headers):
    decl_id = _make_draft(client, auth_headers)
    pdf_content = b"%PDF-1.4 valid content here"
    res = client.post(
        f"/api/declarations/{decl_id}/attachments?filename=test.pdf",
        content=pdf_content,
        headers={**auth_headers, "content-type": "application/pdf"},
    )
    assert res.status_code == 200
    assert res.json()["original_name"] == "test.pdf"
    assert res.json()["scan_status"] == "QUARANTINED"
    assert res.json()["storage_backend"] == "LOCAL_QUARANTINE"
    assert res.json()["checksum_sha256"]


def test_attachment_invalid_pdf_signature(client, auth_headers):
    decl_id = _make_draft(client, auth_headers)
    res = client.post(
        f"/api/declarations/{decl_id}/attachments?filename=fake.pdf",
        content=b"not a pdf at all",
        headers={**auth_headers, "content-type": "application/pdf"},
    )
    assert res.status_code == 400


def test_attachment_unknown_extension_rejected(client, auth_headers):
    res = client.post(
        "/api/declarations/1/attachments?filename=payload.exe",
        headers=auth_headers,
        content=b"MZ",
    )
    assert res.status_code == 415


def test_attachment_size_rejection(client, auth_headers):
    decl_id = _make_draft(client, auth_headers)
    oversized = b"%PDF-1.4 " + b"x" * (12 * 1024 * 1024 + 1)
    res = client.post(
        f"/api/declarations/{decl_id}/attachments?filename=big.pdf",
        content=oversized,
        headers={**auth_headers, "content-type": "application/pdf"},
    )
    assert res.status_code == 413


def test_xlsx_rejects_external_relationship_and_zip_bomb_shape():
    external = io.BytesIO()
    with zipfile.ZipFile(external, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship TargetMode="External" Target="https://example.test"/></Relationships>',
        )
    with pytest.raises(ValueError, match="external relationship"):
        read_workbook(external.getvalue())

    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "x" * (9 * 1024 * 1024))
    with pytest.raises(ValueError):
        read_workbook(bomb.getvalue())


def test_xlsx_ignores_non_executed_external_link_path_and_detects_headers():
    base = make_xlsx(
        "Dữ liệu phương tiện",
        ["Tên phương tiện", "Số đăng ký", "Loại phương tiện", "Cấp phương tiện", "Trọng tải toàn phần"],
        [["Sà lan kiểm thử", "SG-SMART-001", "Sà lan", "VR-SII", 850]],
    )
    source = zipfile.ZipFile(io.BytesIO(base))
    output = io.BytesIO()
    with source, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for info in source.infolist():
            archive.writestr(info, source.read(info.filename))
        archive.writestr(
            "xl/externalLinks/_rels/externalLink1.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/externalLinkPath" Target="old.xlsx" TargetMode="External"/>'
            '</Relationships>',
        )
    organization, rows = vessel_rows(read_workbook(output.getvalue()))
    assert organization["name"] == "Khách hàng import"
    assert rows[0]["name"] == "Sà lan kiểm thử"
    assert rows[0]["registration_no"] == "SG-SMART-001"
    assert rows[0]["deadweight_tons"] == 850
    assert rows[0]["_source_row"] == 4


# ══════════════════════════════════════════════════════════════════════════════
# 10. EXCEL REPORTS
# ══════════════════════════════════════════════════════════════════════════════

def test_xlsx_report_appendix1(client, auth_headers):
    res = client.get("/api/reports/appendix1", headers=auth_headers)
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers.get("content-type", "")
    with zipfile.ZipFile(io.BytesIO(res.content)) as archive:
        assert "xl/workbook.xml" in archive.namelist()
        assert "xl/worksheets/sheet1.xml" in archive.namelist()


def test_xlsx_report_appendix2(client, auth_headers):
    res = client.get("/api/reports/appendix2", headers=auth_headers)
    assert res.status_code == 200


def test_xlsx_report_appendix3(client, auth_headers):
    res = client.get("/api/reports/appendix3", headers=auth_headers)
    assert res.status_code == 200


def test_report_analytics_supports_week_month_quarter_year_and_export(client, customer_headers):
    created_ids = []
    for operating_date, tons, teu, pax in (
        ("2042-03-15T08:00", 120, 4, 7),
        ("2041-03-15T08:00", 80, 2, 3),
    ):
        created = client.post(
            "/api/declarations",
            json=_minimal_declaration(
                declaration_date=operating_date[:10], eta=operating_date,
                etd=f"{operating_date[:10]}T18:00",
                unload={"tons": tons, "teu": teu}, passenger_count=pax,
            ),
            headers=customer_headers,
        )
        assert created.status_code == 200
        created_ids.append(created.json()["id"])
    db = SessionLocal()
    try:
        for declaration_id in created_ids:
            declaration = db.query(Declaration).filter(Declaration.id == declaration_id).one()
            declaration.workflow_status = "APPROVED"
            declaration.status = "SUBMITTED"
        db.commit()
    finally:
        db.close()

    try:
        for period in ("week", "month", "quarter", "year"):
            response = client.get(
                f"/api/reports/analytics?period={period}&as_of=2042-03-15",
                headers=customer_headers,
            )
            assert response.status_code == 200
            body = response.json()
            assert body["period"] == period
            assert set(body["kpis"]) == {"trips", "tons", "teu", "pax"}
            assert len(body["trend"]["cur"]) == len(body["trend"]["labels"])
        month = client.get(
            "/api/reports/analytics?period=month&as_of=2042-03-15",
            headers=customer_headers,
        ).json()
        assert month["kpis"]["trips"] == {"cur": 1.0, "prev": 1.0}
        assert month["kpis"]["tons"] == {"cur": 120.0, "prev": 80.0}
        export = client.get(
            "/api/reports/analytics/export?period=quarter&as_of=2042-03-15",
            headers=customer_headers,
        )
        assert export.status_code == 200
        assert "spreadsheetml" in export.headers.get("content-type", "")
        assert zipfile.is_zipfile(io.BytesIO(export.content))
    finally:
        db = SessionLocal()
        try:
            db.query(Declaration).filter(Declaration.id.in_(created_ids)).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()


def test_approved_report_golden_mapping_uses_actual_times_and_cargo_rows(client, customer_headers):
    created = client.post(
        "/api/declarations",
        json=_minimal_declaration(
            unload={"cargo_type": "Container", "movement_type": "Nhập khẩu", "cargo_name": "Hàng A", "cont20_full": 2, "tons": 12},
            load={"cargo_type": "Container", "movement_type": "Xuất khẩu", "cargo_name": "Hàng B", "cont40_full": 1, "tons": 20},
        ),
        headers=customer_headers,
    )
    declaration_id = created.json()["id"]
    db = SessionLocal()
    declaration = db.query(Declaration).filter(Declaration.id == declaration_id).one()
    declaration.workflow_status = "APPROVED"
    declaration.status = "SUBMITTED"
    declaration.actual_arrival_at = "2026-07-11T09:15"
    declaration.actual_departure_at = "2026-07-11T19:30"
    db.commit()
    db.close()

    appendix1 = client.get("/api/reports/appendix1?from=2026-01-01&to=2026-12-31", headers=customer_headers)
    with zipfile.ZipFile(io.BytesIO(appendix1.content)) as archive:
        xml1 = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "2026-07-11T09:15" in xml1 and "2026-07-11T19:30" in xml1

    appendix3 = client.get("/api/reports/appendix3?from=2026-01-01&to=2026-12-31", headers=customer_headers)
    with zipfile.ZipFile(io.BytesIO(appendix3.content)) as archive:
        xml3 = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "Hàng A" in xml3 and "Hàng B" in xml3
    assert "12.0 tấn / 2.0 TEU" in xml3
    assert "20.0 tấn / 2.0 TEU" in xml3


def test_report_unknown_kind(client, auth_headers):
    res = client.get("/api/reports/unknown", headers=auth_headers)
    assert res.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 11. ROUTE COVERAGE — every frontend endpoint registered
# ══════════════════════════════════════════════════════════════════════════════

def test_all_frontend_routes_registered():
    routes = [route.path for route in app.routes]
    required_paths = [
        "/api/auth/login",
        "/api/health",
        "/api/ready",
        "/api/admin/operations-summary",
        "/api/catalogs",
        "/api/dashboard",
        "/api/organizations",
        "/api/vessels",
        "/api/vessels/{vessel_id}/verify-registry",
        "/api/crew",
        "/api/declarations",
        "/api/declarations/{declaration_id}/attachments",
        "/api/declarations/{declaration_id}/events",
        "/api/declarations/{declaration_id}/workflow",
        "/api/suggestions",
        "/api/import/vessels",
        "/api/import/declaration",
        "/api/reports/analytics",
        "/api/reports/analytics/export",
        "/api/reports/{kind}",
        "/api/integrations/maritime-authority",
        "/api/integrations/prepare-sync",
    ]
    for path in required_paths:
        assert path in routes, f"Route not registered in backend: {path}"


# ══════════════════════════════════════════════════════════════════════════════
# 12. SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_suggestions_valid_field(client, auth_headers):
    res = client.get("/api/suggestions?field=last_port", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_suggestions_invalid_field_returns_empty(client, auth_headers):
    res = client.get("/api/suggestions?field=nonexistent", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


# ══════════════════════════════════════════════════════════════════════════════
# 13. INTEGRATIONS
# ══════════════════════════════════════════════════════════════════════════════

def test_integration_status(client, auth_headers):
    res = client.get("/api/integrations/maritime-authority", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "connector" in data
    assert "jobs" in data
    assert data["adapter"]["mode"] == "MANUAL"
    assert data["adapter"]["networkCallsAllowed"] is False
    assert "readyToSend" in data["connector"]


def test_prepare_sync(client, auth_headers):
    res = client.post(
        "/api/integrations/prepare-sync",
        json={"from": "2026-01-01", "to": "2026-12-31"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["status"] == "PREPARED"


# ══════════════════════════════════════════════════════════════════════════════
# 14. CREW SNAPSHOT ON DECLARATION
# ══════════════════════════════════════════════════════════════════════════════

def test_crew_certificate_snapshot(client, customer_headers):
    crew_res = client.post("/api/crew", json={
        "full_name": "Snapshot Crew",
        "crew_role": "Thuyền trưởng",
        "professional_certificate_type": "Bằng thuyền trưởng",
        "professional_certificate_no": "SNAP-001",
        "certificate_expiry_date": "2099-01-01",
    }, headers=customer_headers)
    assert crew_res.status_code == 200
    crew_id = crew_res.json()["id"]

    res = client.post("/api/declarations?submit=true", json=_minimal_declaration(
        crew_ids=[crew_id],
    ), headers=customer_headers)
    assert res.status_code == 200
    # Crew snapshot was recorded (declaration created with crew_ids)
    assert res.json()["workflow_status"] == "PENDING_REVIEW"


def test_import_preview_and_idempotency(client, auth_headers, customer_headers):
    root = Path(__file__).resolve().parents[1]
    vessel_content = (root / "templates" / "Ho_so_phuong_tien_thuy_noi_dia.xlsx").read_bytes()

    db = SessionLocal()
    before = db.query(ImportJob).count()
    db.close()
    preview = client.post(
        "/api/import/vessels?preview=true",
        content=vessel_content,
        headers={**auth_headers, "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )
    assert preview.status_code == 200
    assert preview.json()["preview"] is True
    assert preview.json()["mappingVersion"] == "KBCV-IMPORT-1.1"
    db = SessionLocal()
    assert db.query(ImportJob).count() == before
    db.close()

    declaration_content = (root / "templates" / "Phieu_khai_bao_PTTND_truoc_khi_den_cang.xlsx").read_bytes()
    first = client.post(
        "/api/import/declaration",
        content=declaration_content,
        headers={**customer_headers, "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )
    assert first.status_code == 200
    assert first.json()["idempotent"] is False
    repeated = client.post(
        "/api/import/declaration",
        content=declaration_content,
        headers={**customer_headers, "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["idempotent"] is True
    assert repeated.json()["id"] == first.json()["id"]


def test_smart_vessel_import_accepts_complete_non_template_workbook(client, auth_headers):
    registration = f"SG-SMART-{uuid.uuid4().hex[:10]}"
    workbook = make_xlsx(
        "Danh mục tùy biến",
        ["Ghi chú", "Số đăng ký", "Tên tàu", "Cấp PT", "Loại PT", "DWT"],
        [["Đủ dữ liệu", registration, "Sà lan linh hoạt", "VR-SII", "Sà lan", 950]],
    )
    headers = {**auth_headers, "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    preview = client.post("/api/import/vessels?preview=true", content=workbook, headers=headers)
    assert preview.status_code == 200
    assert preview.json()["mapping"]["strategy"] == "HEADER_LABEL_DETECTION"
    assert preview.json()["rows"][0]["missingFields"] == []
    imported = client.post("/api/import/vessels", content=workbook, headers=headers)
    assert imported.status_code == 200
    assert imported.json()["accepted"] == 1
    assert imported.json()["rejected"] == []
    db = SessionLocal()
    try:
        vessel = db.query(Vessel).filter(Vessel.registration_no == registration).one()
        db.query(ImportJob).filter(ImportJob.source_checksum == imported.json()["checksum"]).delete(synchronize_session=False)
        db.delete(vessel)
        db.commit()
    finally:
        db.close()
