"""
tests/test_user_management.py — PLATFORM_ADMIN user-management endpoints.

Covers listing, creating (CUSTOMER/PORT_STAFF/PLATFORM_ADMIN), resetting
passwords, and enabling/disabling accounts, plus the RBAC boundary that keeps
these operations admin-only.
"""
from __future__ import annotations

import os

# ── Set test DB FIRST, before any backend import ──────────────────────────────
from tests import _pgdb

_TEST_DB_URL = _pgdb.create_database("kbcv_usermgmt")
os.environ["TEST_DATABASE_URL"] = _TEST_DB_URL

import pytest
from fastapi.testclient import TestClient

from backend.models import Base, User, Organization, ReportingUnit, ReportingUnitUser
from backend.database import engine, SessionLocal, now_iso
from backend.auth import get_password_hash, verify_password
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

# ── Seed baseline data ────────────────────────────────────────────────────────
db = SessionLocal()
try:
    org = Organization(name="Org UM", tax_code="TAXUM", created_at=now_iso(), updated_at=now_iso())
    db.add(org)
    db.flush()
    ORG_ID = org.id

    unit = ReportingUnit(name="Unit UM", code="UNIT-UM", is_active=1, created_at=now_iso(), updated_at=now_iso())
    db.add(unit)
    db.flush()
    UNIT_ID = unit.id

    db.add_all([
        User(username="admin_um", password_hash=get_password_hash("adminpass"), full_name="Admin", role="PLATFORM_ADMIN", is_active=1),
        User(username="cust_um", password_hash=get_password_hash("custpass"), full_name="Customer", role="CUSTOMER", organization_id=ORG_ID, is_active=1),
        User(username="port_um", password_hash=get_password_hash("portpass"), full_name="Port", role="PORT_STAFF", is_active=1),
    ])
    db.commit()
finally:
    db.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


# ── RBAC boundary ─────────────────────────────────────────────────────────────

def test_non_admin_cannot_access_user_management(client):
    for username, password in [("cust_um", "custpass"), ("port_um", "portpass")]:
        headers = _auth(client, username, password)
        assert client.get("/api/admin/users", headers=headers).status_code == 403
        assert client.post(
            "/api/admin/users", headers=headers,
            json={"username": "x1", "password": "password123", "role": "CUSTOMER", "organization_id": ORG_ID},
        ).status_code == 403


def test_admin_lists_users(client):
    headers = _auth(client, "admin_um", "adminpass")
    res = client.get("/api/admin/users", headers=headers)
    assert res.status_code == 200
    usernames = {u["username"] for u in res.json()["items"]}
    assert {"admin_um", "cust_um", "port_um"} <= usernames


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_customer_requires_organization(client):
    headers = _auth(client, "admin_um", "adminpass")
    res = client.post(
        "/api/admin/users", headers=headers,
        json={"username": "cust_new", "password": "password123", "role": "CUSTOMER"},
    )
    assert res.status_code == 422


def test_create_customer_and_login(client):
    headers = _auth(client, "admin_um", "adminpass")
    res = client.post(
        "/api/admin/users", headers=headers,
        json={"username": "cust_new", "password": "password123", "full_name": "Khách Mới",
              "role": "CUSTOMER", "organization_id": ORG_ID},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "CUSTOMER"
    assert body["organization_id"] == ORG_ID
    assert body["is_active"] is True
    # The new account can authenticate with the admin-set password.
    assert client.post("/api/auth/login", json={"username": "cust_new", "password": "password123"}).status_code == 200


def test_create_port_staff_with_units(client):
    headers = _auth(client, "admin_um", "adminpass")
    res = client.post(
        "/api/admin/users", headers=headers,
        json={"username": "port_new", "password": "password123", "role": "PORT_STAFF",
              "reporting_unit_ids": [UNIT_ID]},
    )
    assert res.status_code == 201, res.text
    assert {u["id"] for u in res.json()["reporting_units"]} == {UNIT_ID}
    db = SessionLocal()
    try:
        target = db.query(User).filter(User.username == "port_new").one()
        membership = db.query(ReportingUnitUser).filter_by(user_id=target.id).all()
        assert [m.reporting_unit_id for m in membership] == [UNIT_ID]
    finally:
        db.close()


def test_duplicate_username_rejected(client):
    headers = _auth(client, "admin_um", "adminpass")
    res = client.post(
        "/api/admin/users", headers=headers,
        json={"username": "admin_um", "password": "password123", "role": "PLATFORM_ADMIN"},
    )
    assert res.status_code == 409


def test_short_password_rejected(client):
    headers = _auth(client, "admin_um", "adminpass")
    res = client.post(
        "/api/admin/users", headers=headers,
        json={"username": "shortpw", "password": "short", "role": "PLATFORM_ADMIN"},
    )
    assert res.status_code == 422


# ── Reset password ────────────────────────────────────────────────────────────

def test_reset_password(client):
    headers = _auth(client, "admin_um", "adminpass")
    target = client.get("/api/admin/users", headers=headers).json()["items"]
    cust_id = next(u["id"] for u in target if u["username"] == "cust_um")
    res = client.post(
        f"/api/admin/users/{cust_id}/reset-password", headers=headers,
        json={"password": "newpassword1"},
    )
    assert res.status_code == 200
    assert client.post("/api/auth/login", json={"username": "cust_um", "password": "custpass"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "cust_um", "password": "newpassword1"}).status_code == 200


# ── Enable / disable ──────────────────────────────────────────────────────────

def test_disable_and_enable_account(client):
    headers = _auth(client, "admin_um", "adminpass")
    users = client.get("/api/admin/users", headers=headers).json()["items"]
    port_id = next(u["id"] for u in users if u["username"] == "port_um")

    disabled = client.post(f"/api/admin/users/{port_id}/active", headers=headers, json={"is_active": False})
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    # Disabled account cannot log in.
    assert client.post("/api/auth/login", json={"username": "port_um", "password": "portpass"}).status_code == 403

    enabled = client.post(f"/api/admin/users/{port_id}/active", headers=headers, json={"is_active": True})
    assert enabled.status_code == 200
    assert enabled.json()["is_active"] is True
    assert client.post("/api/auth/login", json={"username": "port_um", "password": "portpass"}).status_code == 200


def test_admin_cannot_disable_self(client):
    headers = _auth(client, "admin_um", "adminpass")
    users = client.get("/api/admin/users", headers=headers).json()["items"]
    admin_id = next(u["id"] for u in users if u["username"] == "admin_um")
    res = client.post(f"/api/admin/users/{admin_id}/active", headers=headers, json={"is_active": False})
    assert res.status_code == 400
