"""
tests/test_rbac.py — T1 Role-Based Access Control and Tenant Isolation Test Suite
WO-KBCV-T1-20260711
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

# ── Set test DB FIRST, before any backend import ──────────────────────────────
_tmp_dir = tempfile.mkdtemp()
_test_db_path = Path(_tmp_dir) / "test_rbac.db"
os.environ["TEST_DATABASE_URL"] = f"sqlite:///{_test_db_path}"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import Base, User, Organization, Vessel, CrewMember, Declaration
from backend.database import engine, SessionLocal, now_iso
from backend.auth import get_password_hash
from backend.app import app, get_db

# ── Create all tables in test DB ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

def _override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = _override_get_db

# Seed data
db = SessionLocal()
try:
    # 1. Seed Organizations
    org_a = Organization(name="Organization A", tax_code="TAXA", created_at=now_iso(), updated_at=now_iso())
    org_b = Organization(name="Organization B", tax_code="TAXB", created_at=now_iso(), updated_at=now_iso())
    db.add_all([org_a, org_b])
    db.commit()
    db.refresh(org_a)
    db.refresh(org_b)

    # 2. Seed Users
    users = [
        User(username="admin", password_hash=get_password_hash("adminpass"), full_name="Admin User", role="ADMIN", is_active=1),
        User(username="cust_a", password_hash=get_password_hash("custpass"), full_name="Customer A", role="CUSTOMER", organization_id=org_a.id, is_active=1),
        User(username="cust_b", password_hash=get_password_hash("custpass"), full_name="Customer B", role="CUSTOMER", organization_id=org_b.id, is_active=1),
        User(username="cust_no_org", password_hash=get_password_hash("custpass"), full_name="No Org Cust", role="CUSTOMER", organization_id=None, is_active=1),
        User(username="disabled_user", password_hash=get_password_hash("pass"), full_name="Disabled", role="CUSTOMER", organization_id=org_a.id, is_active=0),
        User(username="user_cv", password_hash=get_password_hash("cvpass"), full_name="CV Officer", role="CV", is_active=1),
        User(username="user_qlc", password_hash=get_password_hash("qlcpass"), full_name="QLC Officer", role="QLC", is_active=1),
        User(username="user_bp", password_hash=get_password_hash("bppass"), full_name="BP Officer", role="BP", is_active=1),
    ]
    db.add_all(users)
    db.commit()

    # 3. Seed Vessel for Org A
    vessel_a = Vessel(
        organization_id=org_a.id,
        name="Vessel Org A",
        registration_no="REG-A-123",
        vessel_type="Tàu container",
        vessel_class="VR-SI",
        created_at=now_iso(),
        updated_at=now_iso()
    )
    # Seed Vessel for Org B
    vessel_b = Vessel(
        organization_id=org_b.id,
        name="Vessel Org B",
        registration_no="REG-B-123",
        vessel_type="Tàu container",
        vessel_class="VR-SI",
        created_at=now_iso(),
        updated_at=now_iso()
    )
    db.add_all([vessel_a, vessel_b])
    db.commit()
    db.refresh(vessel_a)
    db.refresh(vessel_b)

    # 4. Seed Crew for Org A
    crew_a = CrewMember(
        organization_id=org_a.id,
        vessel_id=vessel_a.id,
        full_name="Crew Member A",
        crew_role="Thủy thủ",
        professional_certificate_type="An toàn",
        professional_certificate_no="CERT-A",
        created_at=now_iso(),
        updated_at=now_iso()
    )
    db.add(crew_a)
    db.commit()
    db.refresh(crew_a)

    # 5. Seed Declarations
    # Draft Declaration for Org A
    decl_a_draft = Declaration(
        organization_id=org_a.id,
        vessel_id=vessel_a.id,
        company_name=org_a.name,
        declaration_date="2026-07-11",
        vessel_name=vessel_a.name,
        registration_no=vessel_a.registration_no,
        vessel_type=vessel_a.vessel_type,
        vessel_class=vessel_a.vessel_class,
        last_port="Port A",
        working_port="Port B",
        eta="2026-07-11T12:00",
        etd="2026-07-11T20:00",
        master_name="Captain A",
        master_phone="0901",
        unload_json="{}",
        load_json="{}",
        workflow_status="DRAFT",
        status="DRAFT",
        reference_no="REF-A-DRAFT-1",
        created_at=now_iso(),
        updated_at=now_iso()
    )
    # Submitted Declaration for Org A
    decl_a_sub = Declaration(
        organization_id=org_a.id,
        vessel_id=vessel_a.id,
        company_name=org_a.name,
        declaration_date="2026-07-11",
        vessel_name=vessel_a.name,
        registration_no=vessel_a.registration_no,
        vessel_type=vessel_a.vessel_type,
        vessel_class=vessel_a.vessel_class,
        last_port="Port A",
        working_port="Port B",
        eta="2026-07-11T12:00",
        etd="2026-07-11T20:00",
        master_name="Captain A",
        master_phone="0901",
        unload_json="{}",
        load_json="{}",
        workflow_status="PENDING_REVIEW",
        status="SUBMITTED",
        reference_no="REF-A-SUB-1",
        created_at=now_iso(),
        updated_at=now_iso()
    )
    db.add_all([decl_a_draft, decl_a_sub])
    db.commit()
finally:
    db.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Token headers helper
def get_auth_header(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    if res.status_code == 200:
        return {"Authorization": f"Bearer {res.json()['access_token']}"}
    return {}

# ══════════════════════════════════════════════════════════════════════════════
# 1. AUTHENTICATION & SECURITY CONTROLS
# ══════════════════════════════════════════════════════════════════════════════

def test_disabled_user_rejected(client):
    """Disabled users must not be allowed to log in or access endpoints."""
    headers = get_auth_header(client, "disabled_user", "pass")
    assert headers == {}  # Login returns 403 Forbidden directly or fails

    # Verify endpoint rejection for disabled users
    res = client.post("/api/auth/login", json={"username": "disabled_user", "password": "pass"})
    assert res.status_code == 403
    assert "Tài khoản đã bị vô hiệu hóa" in res.json()["detail"]

def test_missing_org_fails_closed(client):
    """Customer without organization must fail closed when accessing resources."""
    headers = get_auth_header(client, "cust_no_org", "custpass")
    assert headers != {}
    res = client.get("/api/vessels", headers=headers)
    assert res.status_code == 403
    assert "chưa được liên kết với tổ chức" in res.json()["detail"]

def test_login_rate_limiting(client):
    """Failed login attempts block IP after 5 attempts."""
    # Ensure fresh state
    from backend.app import _login_attempts
    _login_attempts.clear()

    # Try wrong logins 5 times
    for _ in range(5):
        res = client.post("/api/auth/login", json={"username": "cust_a", "password": "wrongpassword"})
        assert res.status_code == 401

    # Sixth attempt should be rate limited with 429
    res = client.post("/api/auth/login", json={"username": "cust_a", "password": "wrongpassword"})
    assert res.status_code == 429
    assert "tạm khóa" in res.json()["detail"]

    # Reset for other tests
    _login_attempts.clear()

# ══════════════════════════════════════════════════════════════════════════════
# 2. TENANT ISOLATION (CUSTOMER A vs CUSTOMER B)
# ══════════════════════════════════════════════════════════════════════════════

def test_tenant_isolation_vessel(client):
    """Customer A cannot read or write Customer B's vessels."""
    headers_a = get_auth_header(client, "cust_a", "custpass")
    headers_b = get_auth_header(client, "cust_b", "custpass")

    # Get B's vessel ID
    db = SessionLocal()
    vessel_b = db.query(Vessel).filter(Vessel.name == "Vessel Org B").first()
    vessel_b_id = vessel_b.id
    db.close()

    # Customer A tries to update Customer B's vessel -> should fail (403 or 404 depending on verify)
    res = client.post("/api/vessels", headers=headers_a, json={
        "id": vessel_b_id,
        "name": "Hacked name",
        "registration_no": "REG-B-123",
        "vessel_type": "Tàu container",
        "vessel_class": "VR-SI"
    })
    assert res.status_code == 403

    # Customer A tries to verify registry of Customer B's vessel -> 403
    res = client.post(f"/api/vessels/{vessel_b_id}/verify-registry", headers=headers_a)
    assert res.status_code == 403

def test_tenant_isolation_declaration(client):
    """Customer B cannot read or write Customer A's declarations."""
    headers_b = get_auth_header(client, "cust_b", "custpass")

    db = SessionLocal()
    decl_a = db.query(Declaration).filter(Declaration.reference_no == "REF-A-DRAFT-1").first()
    decl_a_id = decl_a.id
    db.close()

    # Get events of A's declaration -> 403
    res = client.get(f"/api/declarations/{decl_a_id}/events", headers=headers_b)
    assert res.status_code == 403

    # Upload attachment to A's declaration -> 403
    res = client.post(f"/api/declarations/{decl_a_id}/attachments?filename=test.jpg", headers=headers_b, content=b"fakecontent")
    assert res.status_code == 403

# ══════════════════════════════════════════════════════════════════════════════
# 3. ROLE-BASED ACCESS CONTROL (RBAC MATRIX)
# ══════════════════════════════════════════════════════════════════════════════

def test_workflow_transitions_matrix(client):
    """Verify that only the exact workflow roles can perform transitions."""
    headers_cv = get_auth_header(client, "user_cv", "cvpass")
    headers_qlc = get_auth_header(client, "user_qlc", "qlcpass")
    headers_bp = get_auth_header(client, "user_bp", "bppass")
    headers_admin = get_auth_header(client, "admin", "adminpass")

    db = SessionLocal()
    decl = db.query(Declaration).filter(Declaration.reference_no == "REF-A-SUB-1").first()
    decl_id = decl.id
    db.close()

    # 1. QLC tries CV_APPROVE -> 403
    res = client.post(f"/api/declarations/{decl_id}/workflow", headers=headers_qlc, json={
        "action": "CV_APPROVE", "actor_role": "QLC", "actor_name": "Spy Officer"
    })
    assert res.status_code == 403

    # 2. ADMIN tries CV_APPROVE (workflow break-glass check) -> 403
    res = client.post(f"/api/declarations/{decl_id}/workflow", headers=headers_admin, json={
        "action": "CV_APPROVE", "actor_role": "ADMIN", "actor_name": "Admin"
    })
    assert res.status_code == 403

    # 3. CV approves -> 200 (allowed)
    res = client.post(f"/api/declarations/{decl_id}/workflow", headers=headers_cv, json={
        "action": "CV_APPROVE", "actor_role": "CV", "actor_name": "CV officer"
    })
    assert res.status_code == 200
    assert res.json()["workflow_status"] == "PENDING_QLC"

    # 4. CV tries QLC_APPROVE -> 403
    res = client.post(f"/api/declarations/{decl_id}/workflow", headers=headers_cv, json={
        "action": "QLC_APPROVE", "actor_role": "CV", "actor_name": "CV officer"
    })
    assert res.status_code == 403

    # 5. QLC approves -> 200 (allowed)
    res = client.post(f"/api/declarations/{decl_id}/workflow", headers=headers_qlc, json={
        "action": "QLC_APPROVE", "actor_role": "QLC", "actor_name": "QLC officer"
    })
    assert res.status_code == 200
    assert res.json()["workflow_status"] == "PENDING_BP"

    # 6. BP approves -> 200 (allowed)
    res = client.post(f"/api/declarations/{decl_id}/workflow", headers=headers_bp, json={
        "action": "BP_APPROVE", "actor_role": "BP", "actor_name": "BP officer"
    })
    assert res.status_code == 200
    assert res.json()["workflow_status"] == "APPROVED"

def test_actor_identity_audit_protection(client):
    """Verify that client-supplied actor fields are ignored and derived from JWT."""
    headers_cv = get_auth_header(client, "user_cv", "cvpass")
    
    # We will query another declaration for Org A (let's create a submitted declaration)
    db = SessionLocal()
    org_a = db.query(Organization).filter(Organization.name == "Organization A").first()
    vessel_a = db.query(Vessel).filter(Vessel.organization_id == org_a.id).first()
    decl_2 = Declaration(
        organization_id=org_a.id,
        vessel_id=vessel_a.id,
        company_name=org_a.name,
        declaration_date="2026-07-11",
        vessel_name=vessel_a.name,
        registration_no=vessel_a.registration_no,
        vessel_type=vessel_a.vessel_type,
        vessel_class=vessel_a.vessel_class,
        last_port="Port A",
        working_port="Port B",
        eta="2026-07-11T12:00",
        etd="2026-07-11T20:00",
        master_name="Captain A",
        master_phone="0901",
        unload_json="{}",
        load_json="{}",
        workflow_status="PENDING_REVIEW",
        status="SUBMITTED",
        reference_no="REF-A-SUB-AUDIT-TEST",
        created_at=now_iso(),
        updated_at=now_iso()
    )
    db.add(decl_2)
    db.commit()
    decl_id = decl_2.id
    db.close()

    # Perform workflow transition and inject fake role & name
    res = client.post(f"/api/declarations/{decl_id}/workflow", headers=headers_cv, json={
        "action": "CV_APPROVE",
        "actor_role": "BP",  # Fake role
        "actor_name": "Hacker Officer"  # Fake name
    })
    assert res.status_code == 200

    # Retrieve events and verify the actual actor from DB
    res_events = client.get(f"/api/declarations/{decl_id}/events", headers=headers_cv)
    assert res_events.status_code == 200
    events = res_events.json()
    cv_approve_event = [e for e in events if e["action"] == "CV_APPROVE"][0]
    
    assert cv_approve_event["actor_role"] == "CV"  # derived from JWT user_cv role
    assert cv_approve_event["actor_name"] == "CV Officer"  # derived from JWT user_cv full_name

# ══════════════════════════════════════════════════════════════════════════════
# 4. FAIL-FAST CONFIGURATION TEST
# ══════════════════════════════════════════════════════════════════════════════

def test_fail_fast_outside_test_mode():
    """Verify that auth module triggers fail-fast check outside local test/db mode."""
    # Temporarily unset TEST_DATABASE_URL to trigger fail-fast condition
    original_db_url = os.environ.pop("TEST_DATABASE_URL", None)
    try:
        # Reloading auth inside try-except should fail with SystemExit
        import importlib
        import backend.auth
        with pytest.raises(SystemExit):
            importlib.reload(backend.auth)
    finally:
        # Restore environment variable
        if original_db_url:
            os.environ["TEST_DATABASE_URL"] = original_db_url
