"""
Khai-bao-Cang-vu FastAPI backend — T0 Baseline Recovery
WO-KBCV-T0-20260711

Entry point: python -m uvicorn backend.app:app --host 127.0.0.1 --port 8080
"""
from __future__ import annotations

import json
import hashlib
import logging
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlalchemy import desc, func, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, get_password_hash, verify_password
from .integrations import maritime_authority_adapter, registry_adapter
from .logging_config import configure_local_logging
from .rbac import require_roles, verify_organization_ownership
from .storage import ScannerNotConfigured, get_attachment_storage
from .database import DB_PATH, SessionLocal, audit, cargo, correlation_id, engine, now_iso
from .models import (
    Attachment, AuditEvent, Base, CrewMember, Declaration,
    DeclarationCrew, DeclarationEvent, ImportJob, IntegrationConnector, Organization,
    SyncJob, User, Vessel,
)
from .xlsx_io import declaration_row, make_xlsx, read_workbook, vessel_rows, excel_date

IMPORT_MAPPING_VERSION = "KBCV-IMPORT-1.0"

ROOT = Path(__file__).resolve().parents[1]
access_logger = configure_local_logging(ROOT)
ATTACHMENT_DIR = ROOT / "data" / "attachments"
ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
attachment_storage = get_attachment_storage(ATTACHMENT_DIR / "quarantine")
attachment_scanner = ScannerNotConfigured()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Khai-bao-Cang-vu API", version="1.0.0")


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    request_id = request.headers.get("X-Correlation-ID", "").strip() or str(uuid.uuid4())
    token = correlation_id.set(request_id[:128])
    started = datetime.now()
    try:
        response = await call_next(request)
    finally:
        correlation_id.reset(token)
    response.headers["X-Correlation-ID"] = request_id[:128]
    access_logger.info(
        "%s %s status=%s duration_ms=%s correlation_id=%s",
        request.method, request.url.path, response.status_code,
        int((datetime.now() - started).total_seconds() * 1000), request_id[:128],
    )
    return response


@app.exception_handler(IntegrityError)
async def database_constraint_error(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Dữ liệu xung đột với một bản ghi đã tồn tại."},
    )

origins_env = os.getenv("ALLOWED_ORIGINS")
if origins_env:
    origins = [o.strip() for o in origins_env.split(",") if o.strip()]
else:
    origins = ["http://127.0.0.1:8080", "http://localhost:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB dependency ──────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ── Attachment signature rules ─────────────────────────────────────────────────
MAGIC_BYTES: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG",
    ".xlsx": b"PK\x03\x04",
    ".xls": b"\xd0\xcf",
    ".doc": b"\xd0\xcf",
    ".docx": b"PK\x03\x04",
    ".webp": b"RIFF",
}
ALLOWED_ATTACHMENT_EXTENSIONS = frozenset(MAGIC_BYTES)
MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024  # 12 MB


def validate_attachment_content(extension: str, content: bytes) -> None:
    extension = extension.lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Phần mở rộng file không được hỗ trợ.")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="File vượt quá giới hạn 12 MB.")
    expected = MAGIC_BYTES[extension]
    if not content.startswith(expected):
        raise HTTPException(
            status_code=400,
            detail=f"File không đúng định dạng {extension} (magic bytes không khớp).",
        )


# ── Certificate helper ─────────────────────────────────────────────────────────
def certificate_status(value: Optional[str], warning_days: int = 30) -> str:
    if not value:
        return "UNKNOWN"
    try:
        expiry = date.fromisoformat(value[:10])
    except ValueError:
        return "UNKNOWN"
    remaining = (expiry - date.today()).days
    if remaining < 0:
        return "EXPIRED"
    if remaining <= warning_days:
        return "EXPIRING"
    return "VALID"


# ── Workflow state machine ─────────────────────────────────────────────────────
WORKFLOW_TRANSITIONS: dict[str, dict[str, str]] = {
    "CV_APPROVE":        {"from": "PENDING_REVIEW",  "to": "PENDING_QLC"},
    "QLC_APPROVE":       {"from": "PENDING_QLC",     "to": "PENDING_BP"},
    "BP_APPROVE":        {"from": "PENDING_BP",       "to": "APPROVED"},
    "ISSUE":             {"from": "APPROVED",         "to": "ISSUED"},
    "REQUEST_CHANGES":   {"from": None,               "to": "CHANGES_REQUESTED"},
    "REVOKE":            {"from": None,               "to": "REVOKED"},
}


def _apply_workflow_transition(
    db: Session, declaration: Declaration, action: str, actor_role: str,
    actor_name: str, actor_user_id: int, note: str = "", permit_no: str = ""
) -> Declaration:
    rule = WORKFLOW_TRANSITIONS.get(action)
    if not rule:
        raise HTTPException(status_code=400, detail=f"Hành động '{action}' không hợp lệ.")

    current = declaration.workflow_status
    required_from = rule["from"]
    if required_from and current != required_from:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể thực hiện '{action}' từ trạng thái '{current}'. "
                   f"Cần trạng thái '{required_from}'.",
        )
    if action in ("REQUEST_CHANGES", "REVOKE") and not note.strip():
        raise HTTPException(status_code=400, detail="Cần nhập lý do cho thao tác này.")

    new_status = rule["to"]
    from_status = current
    declaration.workflow_status = new_status

    if action == "CV_APPROVE":
        declaration.cv_approval = "APPROVED"
    elif action == "QLC_APPROVE":
        declaration.qlc_approval = "APPROVED"
    elif action == "BP_APPROVE":
        declaration.bp_approval = "APPROVED"
    elif action == "ISSUE":
        if not permit_no.strip():
            raise HTTPException(status_code=400, detail="Cần cung cấp permit_no khi phát hành.")
        declaration.permit_no = permit_no.strip()
        declaration.issued_at = now_iso()
    elif action == "REVOKE":
        declaration.revoked_at = now_iso()

    declaration.updated_at = now_iso()
    declaration.version += 1

    event = DeclarationEvent(
        declaration_id=declaration.id,
        action=action,
        from_status=from_status,
        to_status=new_status,
        actor_name=actor_name,
        actor_role=actor_role,
        actor_user_id=actor_user_id,
        correlation_id=correlation_id.get(),
        note=note,
        created_at=now_iso(),
    )
    db.add(event)
    return declaration


# ── Pydantic request models ────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class CargoPayload(BaseModel):
    cargo_type: str = ""
    movement_type: str = ""
    cargo_name: str = ""
    cont20_full: int = 0
    cont20_empty: int = 0
    cont40_full: int = 0
    cont40_empty: int = 0
    tons: float = 0.0

    @field_validator("cont20_full", "cont20_empty", "cont40_full", "cont40_empty")
    @classmethod
    def non_negative_containers(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Số lượng container không được âm.")
        return value

    @field_validator("tons")
    @classmethod
    def non_negative_tons(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Khối lượng không được âm.")
        return value


class VesselSaveRequest(BaseModel):
    id: Optional[int] = None
    version: Optional[int] = None
    organization_name: Optional[str] = None
    organization: Optional[Dict[str, Any]] = None
    name: str
    registration_no: str
    registry_or_imo: str = ""
    vessel_type: str
    vessel_class: str
    shell_material: str = ""
    build_year: Optional[int] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    side_height_m: Optional[float] = None
    draft_m: Optional[float] = None
    deadweight_tons: Optional[float] = None
    gross_tonnage: Optional[float] = None
    engine_power_cv: Optional[float] = None
    cargo_capacity_tons: Optional[float] = None
    container_capacity_teu: Optional[float] = None
    passenger_capacity: Optional[int] = None
    min_crew: Optional[int] = None
    safety_certificate_no: str = ""
    certificate_issue_date: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    notes: str = ""

    @field_validator("name", "registration_no")
    @classmethod
    def required_vessel_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value

    @field_validator("length_m", "width_m", "side_height_m", "draft_m", "deadweight_tons", "gross_tonnage", "engine_power_cv", "cargo_capacity_tons", "container_capacity_teu")
    @classmethod
    def non_negative_measurements(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("Thông số không được âm.")
        return value

    @field_validator("build_year", "passenger_capacity", "min_crew")
    @classmethod
    def non_negative_integer_fields(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Thông số không được âm.")
        return value


class CrewSaveRequest(BaseModel):
    id: Optional[int] = None
    version: Optional[int] = None
    vessel_id: Optional[int] = None
    full_name: str
    crew_role: str
    phone: str = ""
    identity_no: str = ""
    professional_certificate_type: str = ""
    professional_certificate_no: str = ""
    certificate_issue_date: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    notes: str = ""

    @field_validator("full_name", "crew_role", "professional_certificate_type", "professional_certificate_no")
    @classmethod
    def required_crew_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value


class DeclarationSaveRequest(BaseModel):
    id: Optional[int] = None
    version: Optional[int] = None
    vessel_id: Optional[int] = None
    company_name: str
    declaration_date: str
    vessel_name: str
    registration_no: str
    vessel_type: str
    vessel_class: str
    length_m: Optional[float] = None
    deadweight_tons: Optional[float] = None
    gross_tonnage: Optional[float] = None
    certificate_expiry_date: Optional[str] = None
    crew_count: int = 0
    passenger_count: int = 0
    last_port: str
    working_port: str
    destination_port: str = ""
    eta: str
    etd: str
    master_name: str
    master_phone: str
    movement_type: str = "ARRIVAL"
    purpose: str = ""
    cargo_description: str = ""
    actual_arrival_at: Optional[str] = None
    actual_departure_at: Optional[str] = None
    unload: CargoPayload = CargoPayload()
    load: CargoPayload = CargoPayload()
    crew_ids: List[int] = []

    @field_validator("crew_count", "passenger_count")
    @classmethod
    def non_negative_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Số lượng không được âm.")
        return value

    @field_validator("movement_type")
    @classmethod
    def valid_movement_type(cls, value: str) -> str:
        if value not in {"ARRIVAL", "DEPARTURE"}:
            raise ValueError("Loại phiếu không hợp lệ.")
        return value

    @field_validator(
        "company_name", "vessel_name", "registration_no", "vessel_type", "vessel_class",
        "last_port", "working_port", "master_name", "master_phone",
    )
    @classmethod
    def required_declaration_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value

    @model_validator(mode="after")
    def eta_before_etd(self) -> "DeclarationSaveRequest":
        try:
            if self.eta and self.etd and self.eta[:16] > self.etd[:16]:
                raise ValueError("ETA phải trước ETD.")
        except (TypeError, AttributeError):
            pass
        return self


class WorkflowActionRequest(BaseModel):
    action: str
    note: str = ""
    permit_no: str = ""


class PrepareSyncRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: Optional[str] = None
    to: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PrepareSyncRequest":
        return cls(from_=data.get("from"), to=data.get("to"))


# ── Catalog constants ──────────────────────────────────────────────────────────
VESSEL_TYPES = [
    "Tàu hàng khô", "Tàu container", "Tàu hàng lỏng/dầu", "Tàu khách",
    "Tàu kéo/đẩy", "Sà lan tự hành", "Sà lan", "Khác",
]
VESSEL_CLASSES = ["VR-SI", "VR-SII", "VR-SIII", "Khác"]
SHELL_MATERIALS = ["Thép", "Gỗ", "Composite/GRP", "Xi măng lưới thép", "Nhôm", "Khác"]
CARGO_TYPES = ["Container", "Hàng khô", "Hàng lỏng"]
UNLOAD_MOVEMENTS = [
    "Nội địa", "Nhập khẩu", "Chuyển tải", "Quá cảnh có bốc dỡ", "Quá cảnh không bốc dỡ",
]
LOAD_MOVEMENTS = ["Nội địa", "Xuất khẩu"]


# Rate limiting tracker for login: {ip: {"failures": count, "blocked_until": datetime}}
_login_attempts: Dict[str, Dict[str, Any]] = {}

@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    now = datetime.now()

    # Rate limiting check
    tracker = _login_attempts.get(ip)
    if tracker and tracker["failures"] >= 5:
        if now < tracker["blocked_until"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Tài khoản hoặc IP bị tạm khóa do đăng nhập sai nhiều lần. Vui lòng thử lại sau 5 phút."
            )
        else:
            # Block expired, reset tracker
            _login_attempts[ip] = {"failures": 0, "blocked_until": now}

    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        # Register failure
        if ip not in _login_attempts:
            _login_attempts[ip] = {"failures": 1, "blocked_until": now}
        else:
            _login_attempts[ip]["failures"] += 1
            if _login_attempts[ip]["failures"] >= 5:
                from datetime import timedelta
                _login_attempts[ip]["blocked_until"] = now + timedelta(minutes=5)

        # Audit failure (NO password/token printed)
        audit(db, "auth", 0, "LOGIN_FAILURE", f"Đăng nhập thất bại từ IP={ip}")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không đúng."
        )

    # Check active status
    if not getattr(user, "is_active", True):
        audit(db, "auth", user.id, "LOGIN_FAILURE_DISABLED", f"Đăng nhập thất bại do tài khoản bị vô hiệu hóa từ IP={ip}")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa."
        )

    # Reset failure tracker on successful login
    if ip in _login_attempts:
        _login_attempts[ip] = {"failures": 0, "blocked_until": now}

    # Generate token containing username (sub), role, and org_id
    token = create_access_token(data={
        "sub": user.username,
        "role": user.role,
        "org_id": user.organization_id
    })

    # Audit success
    audit(db, "user", user.id, "LOGIN_SUCCESS", f"Đăng nhập thành công từ IP={ip}")
    db.commit()
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": user.organization.name if user.organization else None
    }


@app.post("/api/auth/logout")
def logout(user: User = Depends(get_current_user)):
    # Local client-side stateless token removal is primary, but we return 200 OK.
    return {"status": "ok", "detail": "Đăng xuất thành công."}


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health_check():
    return {"status": "ok", "database": "sqlite-sqlalchemy", "storage": attachment_storage.backend_name, "version": "1.0.0"}


@app.get("/api/ready")
def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok", "storage": attachment_storage.backend_name}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database readiness check failed.") from exc


# ══════════════════════════════════════════════════════════════════════════════
# CATALOGS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/catalogs")
def get_catalogs():
    return {
        "vesselTypes": VESSEL_TYPES,
        "vesselClasses": VESSEL_CLASSES,
        "shellMaterials": SHELL_MATERIALS,
        "cargoTypes": CARGO_TYPES,
        "unloadMovements": UNLOAD_MOVEMENTS,
        "loadMovements": LOAD_MOVEMENTS,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ORGANIZATIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/organizations")
def get_organizations(db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN"))):
    orgs = db.query(Organization).order_by(Organization.name).all()
    return [
        {c.name: getattr(o, c.name) for c in o.__table__.columns}
        for o in orgs
    ]


@app.get("/api/admin/operations-summary")
def admin_operations_summary(
    db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN")),
):
    today = date.today()
    year_start = date(today.year, 1, 1).isoformat()
    declaration_query = db.query(Declaration).filter(Declaration.declaration_date >= year_start)
    declarations = declaration_query.all()
    approved = [item for item in declarations if item.workflow_status in {"APPROVED", "ISSUED"}]
    pending = [item for item in declarations if item.workflow_status.startswith("PENDING_")]
    tons = teu = 0.0
    for item in approved:
        for cargo_item in (json.loads(item.unload_json or "{}"), json.loads(item.load_json or "{}")):
            tons += float(cargo_item.get("tons") or 0)
            teu += float(cargo_item.get("teu") or 0)

    expiring = sum(
        1 for vessel in db.query(Vessel).all()
        if certificate_status(vessel.certificate_expiry_date) in {"EXPIRING", "EXPIRED"}
    )
    backup_dir = ROOT / "data" / "backups"
    backups = list(backup_dir.glob("*.db")) if backup_dir.exists() else []
    latest_backup = max(backups, key=lambda item: item.stat().st_mtime).name if backups else None
    return {
        "period": {"from": year_start, "to": today.isoformat()},
        "operations": {"declarations": len(declarations), "approved": len(approved), "pending": len(pending), "tons": tons, "teu": teu},
        "fleet": {"vessels": db.query(Vessel).count(), "certificateWarnings": expiring},
        "imports": {"jobs": db.query(ImportJob).count(), "rejectedRows": db.query(func.coalesce(func.sum(ImportJob.rejected_count), 0)).scalar()},
        "storage": {"attachments": db.query(Attachment).count(), "backups": len(backups), "latestBackup": latest_backup},
        "security": {"failedLogins": db.query(AuditEvent).filter(AuditEvent.action.like("LOGIN_FAILURE%")).count(), "disabledUsers": db.query(User).filter(User.is_active == 0).count()},
    }


def _get_or_create_org(db: Session, name: Optional[str]) -> Optional[Organization]:
    if not name:
        return None
    org = db.query(Organization).filter(Organization.name == name).first()
    if not org:
        org = Organization(name=name, updated_at=now_iso(), created_at=now_iso())
        db.add(org)
        db.flush()
    return org


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
def get_dashboard(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    today_iso = date.today().isoformat()

    # Base queries
    vessels_q = db.query(Vessel)
    drafts_q = db.query(Declaration).filter(Declaration.workflow_status == "DRAFT")
    submitted_q = db.query(Declaration).filter(Declaration.workflow_status.notin_(["DRAFT", "CHANGES_REQUESTED"]))
    arriving_q = db.query(Declaration).filter(Declaration.eta.startswith(today_iso))
    warnings_q = db.query(Vessel).filter(Vessel.certificate_expiry_date.isnot(None))
    recent_q = db.query(Declaration)
    vessel_search_q = db.query(Vessel)

    # Scoping
    if user.role == "CUSTOMER":
        vessels_q = vessels_q.filter(Vessel.organization_id == user.organization_id)
        drafts_q = drafts_q.filter(Declaration.organization_id == user.organization_id)
        submitted_q = submitted_q.filter(Declaration.organization_id == user.organization_id)
        arriving_q = arriving_q.filter(Declaration.organization_id == user.organization_id)
        warnings_q = warnings_q.filter(Vessel.organization_id == user.organization_id)
        recent_q = recent_q.filter(Declaration.organization_id == user.organization_id)
        vessel_search_q = vessel_search_q.filter(Vessel.organization_id == user.organization_id)
    elif user.role in ("CV", "QLC", "BP"):
        # Reviewers see all submitted/approved/issued/revoked, but not drafts
        drafts_q = drafts_q.filter(Declaration.id == -1)  # Drafts count is 0
        recent_q = recent_q.filter(Declaration.workflow_status != "DRAFT")

    # Counts
    vessels_count = vessels_q.with_entities(func.count(Vessel.id)).scalar()
    drafts_count = drafts_q.with_entities(func.count(Declaration.id)).scalar()
    submitted_count = submitted_q.with_entities(func.count(Declaration.id)).scalar()
    arriving_today = arriving_q.with_entities(func.count(Declaration.id)).scalar()
    cert_warnings = warnings_q.with_entities(func.count(Vessel.id)).scalar()

    recent_decls = recent_q.order_by(desc(Declaration.updated_at)).limit(8).all()

    matches: list[dict] = []
    if q:
        search = f"%{q}%"
        vessels = (
            vessel_search_q
            .filter(or_(Vessel.registration_no.like(search), Vessel.name.like(search)))
            .order_by(desc(Vessel.updated_at))
            .limit(12)
            .all()
        )
        for v in vessels:
            v_dict = {c.name: getattr(v, c.name) for c in v.__table__.columns}
            v_dict["organization_name"] = v.organization.name if v.organization else None
            v_dict["certificate_status"] = certificate_status(v.certificate_expiry_date)
            matches.append(v_dict)

    recent = []
    for d in recent_decls:
        d_dict = {c.name: getattr(d, c.name) for c in d.__table__.columns}
        d_dict["unload"] = json.loads(d_dict.pop("unload_json", "{}"))
        d_dict["load"] = json.loads(d_dict.pop("load_json", "{}"))
        recent.append(d_dict)

    return {
        "stats": {
            "vessels": vessels_count,
            "drafts": drafts_count,
            "submitted": submitted_count,
            "arrivingToday": arriving_today,
            "certificateWarnings": cert_warnings,
        },
        "recent": recent,
        "matches": matches,
    }


# ══════════════════════════════════════════════════════════════════════════════
# VESSELS
# ══════════════════════════════════════════════════════════════════════════════

def _vessel_dict(v: Vessel) -> dict:
    d = {c.name: getattr(v, c.name) for c in v.__table__.columns}
    d["organization_name"] = v.organization.name if v.organization else None
    d["certificate_status"] = certificate_status(v.certificate_expiry_date)
    return d


@app.get("/api/vessels")
def get_vessels(db: Session = Depends(get_db), user: User = Depends(require_roles("CUSTOMER", "CV", "QLC", "BP", "ADMIN"))):
    if user.role == "CUSTOMER":
        vessels = db.query(Vessel).filter(Vessel.organization_id == user.organization_id).order_by(desc(Vessel.updated_at)).all()
    else:
        vessels = db.query(Vessel).order_by(desc(Vessel.updated_at)).all()
    return [_vessel_dict(v) for v in vessels]


@app.post("/api/vessels")
def save_vessel(
    payload: VesselSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "ADMIN")),
):
    if user.role == "CUSTOMER":
        # Force organization to the customer's bound organization
        org_id = user.organization_id
    else:
        # ADMIN can specify organization name
        org_name = (
            (payload.organization or {}).get("name") if isinstance(payload.organization, dict)
            else payload.organization_name
        )
        org = _get_or_create_org(db, org_name)
        org_id = org.id if org else None

    data = payload.model_dump(exclude={"id", "version", "organization", "organization_name"})
    data["organization_id"] = org_id
    data["updated_at"] = now_iso()

    if payload.id:
        vessel = db.query(Vessel).filter(Vessel.id == payload.id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
        if payload.version is not None and payload.version != vessel.version:
            raise HTTPException(status_code=409, detail="Hồ sơ phương tiện đã được cập nhật bởi người dùng khác.")
        # Tenant isolation check
        verify_organization_ownership(user, vessel.organization_id)

        for k, v in data.items():
            if hasattr(vessel, k):
                setattr(vessel, k, v)
        vessel.version += 1
        audit(
            db, "VESSEL", vessel.id, "UPDATE", f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=user.id, organization_id=vessel.organization_id,
        )
        db.commit()
        db.refresh(vessel)
    else:
        data["created_at"] = now_iso()
        vessel = Vessel(**{k: v for k, v in data.items() if hasattr(Vessel, k)})
        db.add(vessel)
        db.flush()
        audit(
            db, "VESSEL", vessel.id, "CREATE", f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=user.id, organization_id=vessel.organization_id,
        )
        db.commit()
        db.refresh(vessel)

    return _vessel_dict(vessel)


@app.post("/api/vessels/{vessel_id}/verify-registry")
def verify_vessel_registry(
    vessel_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "ADMIN")),
):
    """
    Local-only registry date check. Does NOT call any external Maritime Authority API.
    Records verification source as 'local' and updates certificate_status.
    External registry integration is out of scope until T6.
    """
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")

    # Tenant isolation check
    verify_organization_ownership(user, vessel.organization_id)

    adapter_status = registry_adapter().status()
    vessel.registry_verification_status = "VERIFIED_LOCAL"
    vessel.registry_verified_at = now_iso()
    vessel.registry_verification_source = "local"
    vessel.updated_at = now_iso()
    db.commit()
    db.refresh(vessel)
    result = _vessel_dict(vessel)
    result["adapter"] = adapter_status
    return result


# ══════════════════════════════════════════════════════════════════════════════
# CREW
# ══════════════════════════════════════════════════════════════════════════════

def _crew_dict(c: CrewMember, db: Session) -> dict:
    d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    d["certificate_status"] = certificate_status(c.certificate_expiry_date)
    if c.vessel_id:
        vessel = db.query(Vessel).filter(Vessel.id == c.vessel_id).first()
        d["vessel_name"] = vessel.name if vessel else None
        d["registration_no"] = vessel.registration_no if vessel else None
    else:
        d["vessel_name"] = None
        d["registration_no"] = None
    return d


@app.get("/api/crew")
def get_crew(db: Session = Depends(get_db), user: User = Depends(require_roles("CUSTOMER", "CV", "QLC", "BP", "ADMIN"))):
    if user.role == "CUSTOMER":
        crews = db.query(CrewMember).filter(CrewMember.organization_id == user.organization_id).order_by(CrewMember.full_name).all()
    else:
        crews = db.query(CrewMember).order_by(CrewMember.full_name).all()
    return [_crew_dict(c, db) for c in crews]


@app.post("/api/crew")
def save_crew(
    payload: CrewSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "ADMIN")),
):
    # Verify vessel ownership if provided
    if payload.vessel_id:
        vessel = db.query(Vessel).filter(Vessel.id == payload.vessel_id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện được gán.")
        verify_organization_ownership(user, vessel.organization_id)

    data = payload.model_dump(exclude={"id", "version"})
    data["updated_at"] = now_iso()

    if user.role == "CUSTOMER":
        data["organization_id"] = user.organization_id

    if payload.id:
        member = db.query(CrewMember).filter(CrewMember.id == payload.id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Không tìm thấy thuyền viên.")
        if payload.version is not None and payload.version != member.version:
            raise HTTPException(status_code=409, detail="Hồ sơ thuyền viên đã được cập nhật bởi người dùng khác.")
        verify_organization_ownership(user, member.organization_id)

        # If user is ADMIN, organization_id can be updated, but for CUSTOMER we keep it same
        if user.role == "CUSTOMER":
            data.pop("organization_id", None)

        for k, v in data.items():
            if hasattr(member, k):
                setattr(member, k, v)
        member.version += 1
        audit(
            db, "CREW", member.id, "UPDATE", f"{member.full_name} / {member.crew_role}",
            actor_user_id=user.id, organization_id=member.organization_id,
        )
        db.commit()
        db.refresh(member)
    else:
        data["created_at"] = now_iso()
        member = CrewMember(**{k: v for k, v in data.items() if hasattr(CrewMember, k)})
        db.add(member)
        db.flush()
        audit(
            db, "CREW", member.id, "CREATE", f"{member.full_name} / {member.crew_role}",
            actor_user_id=user.id, organization_id=member.organization_id,
        )
        db.commit()
        db.refresh(member)

    return _crew_dict(member, db)


# ══════════════════════════════════════════════════════════════════════════════
# DECLARATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _declaration_dict(d: Declaration) -> dict:
    result = {c.name: getattr(d, c.name) for c in d.__table__.columns}
    result["unload"] = json.loads(result.pop("unload_json", "{}"))
    result["load"] = json.loads(result.pop("load_json", "{}"))
    return result


@app.get("/api/declarations")
def get_declarations(
    q: Optional[str] = None,
    movement_type: Optional[str] = None,
    workflow_status: Optional[str] = None,
    master_name: Optional[str] = None,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    page: Optional[int] = Query(default=None, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default="updated_at"),
    direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "CV", "QLC", "BP", "ADMIN")),
):
    query = db.query(Declaration)

    if user.role == "CUSTOMER":
        query = query.filter(Declaration.organization_id == user.organization_id)
    elif user.role in ("CV", "QLC", "BP"):
        # Reviewers cannot see draft declarations
        query = query.filter(Declaration.workflow_status != "DRAFT")

    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Declaration.vessel_name.like(search),
                Declaration.registration_no.like(search),
                Declaration.reference_no.like(search),
            )
        )
    if movement_type:
        query = query.filter(Declaration.movement_type == movement_type)
    if workflow_status:
        query = query.filter(Declaration.workflow_status == workflow_status)
    if master_name:
        query = query.filter(Declaration.master_name.like(f"%{master_name}%"))
    if from_:
        query = query.filter(Declaration.declaration_date >= from_)
    if to:
        query = query.filter(Declaration.declaration_date <= to)
    sort_columns = {
        "updated_at": Declaration.updated_at,
        "declaration_date": Declaration.declaration_date,
        "reference_no": Declaration.reference_no,
        "workflow_status": Declaration.workflow_status,
    }
    order_column = sort_columns.get(sort, Declaration.updated_at)
    ordered = query.order_by(order_column.asc() if direction == "asc" else order_column.desc(), Declaration.id.desc())
    if page is None:
        # Compatibility mode for existing consumers. New UI clients must opt in
        # to the bounded envelope by sending an explicit page number.
        return [_declaration_dict(d) for d in ordered.all()]

    total = query.order_by(None).count()
    decls = ordered.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_declaration_dict(d) for d in decls],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "sort": sort if sort in sort_columns else "updated_at",
        "direction": direction,
    }


@app.post("/api/declarations")
def save_declaration(
    payload: DeclarationSaveRequest,
    submit: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "ADMIN")),
):
    if submit and user.role != "CUSTOMER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ chủ phương tiện (CUSTOMER) mới có quyền nộp phiếu khai báo."
        )

    if user.role == "CUSTOMER":
        # Force organization to the customer's bound organization
        org_id = user.organization_id
        company_name = user.organization.name if user.organization else "N/A"
    else:
        # ADMIN can specify organization name
        org = _get_or_create_org(db, payload.company_name)
        org_id = org.id if org else None
        company_name = payload.company_name

    # IDOR prevention: check vessel ownership
    if payload.vessel_id:
        vessel = db.query(Vessel).filter(Vessel.id == payload.vessel_id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
        verify_organization_ownership(user, vessel.organization_id)

    # IDOR prevention: check crew members ownership
    if payload.crew_ids:
        for crew_id in payload.crew_ids:
            crew_member = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
            if not crew_member:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy thuyền viên ID {crew_id}.")
            verify_organization_ownership(user, crew_member.organization_id)

    unload_data = cargo(payload.unload.model_dump())
    load_data = cargo(payload.load.model_dump())

    if payload.id:
        decl = db.query(Declaration).filter(Declaration.id == payload.id).first()
        if not decl:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiếu khai báo.")
        if payload.version is not None and payload.version != decl.version:
            raise HTTPException(status_code=409, detail="Phiếu khai báo đã được cập nhật bởi người dùng khác.")
        # Tenant isolation check
        verify_organization_ownership(user, decl.organization_id)

        if decl.workflow_status not in ("DRAFT", "CHANGES_REQUESTED"):
            raise HTTPException(
                status_code=409,
                detail="Không thể chỉnh sửa phiếu đã nộp. Dùng luồng REQUEST_CHANGES để điều chỉnh.",
            )
        # Update fields
        for field_name in (
            "declaration_date", "vessel_name", "registration_no",
            "vessel_type", "vessel_class", "length_m", "deadweight_tons", "gross_tonnage",
            "certificate_expiry_date", "crew_count", "passenger_count", "last_port",
            "working_port", "destination_port", "eta", "etd", "master_name", "master_phone",
            "movement_type", "purpose", "cargo_description",
            "actual_arrival_at", "actual_departure_at", "vessel_id",
        ):
            val = getattr(payload, field_name, None)
            if val is not None and hasattr(decl, field_name):
                setattr(decl, field_name, val)

        decl.company_name = company_name
        decl.unload_json = json.dumps(unload_data, ensure_ascii=False)
        decl.load_json = json.dumps(load_data, ensure_ascii=False)
        decl.organization_id = org_id
        decl.updated_at = now_iso()
        decl.version += 1
    else:
        ref_no = f"TT-{datetime.now():%Y%m%d-%H%M%S}-{datetime.now().microsecond:06d}"
        decl = Declaration(
            reference_no=ref_no,
            organization_id=org_id,
            vessel_id=payload.vessel_id,
            company_name=company_name,
            declaration_date=payload.declaration_date,
            vessel_name=payload.vessel_name,
            registration_no=payload.registration_no,
            vessel_type=payload.vessel_type,
            vessel_class=payload.vessel_class,
            length_m=payload.length_m,
            deadweight_tons=payload.deadweight_tons,
            gross_tonnage=payload.gross_tonnage,
            certificate_expiry_date=payload.certificate_expiry_date,
            crew_count=payload.crew_count,
            passenger_count=payload.passenger_count,
            last_port=payload.last_port,
            working_port=payload.working_port,
            destination_port=payload.destination_port,
            eta=payload.eta,
            etd=payload.etd,
            master_name=payload.master_name,
            master_phone=payload.master_phone,
            movement_type=payload.movement_type,
            purpose=payload.purpose,
            cargo_description=payload.cargo_description,
            actual_arrival_at=payload.actual_arrival_at,
            actual_departure_at=payload.actual_departure_at,
            unload_json=json.dumps(unload_data, ensure_ascii=False),
            load_json=json.dumps(load_data, ensure_ascii=False),
            workflow_status="DRAFT",
            status="DRAFT",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        db.add(decl)
        db.flush()

    # Sync crew snapshot
    if payload.crew_ids is not None:
        db.query(DeclarationCrew).filter(DeclarationCrew.declaration_id == decl.id).delete()
        for crew_id in payload.crew_ids:
            member = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
            if member:
                db.add(DeclarationCrew(
                    declaration_id=decl.id,
                    crew_member_id=member.id,
                    crew_role_snapshot=member.crew_role,
                    certificate_no_snapshot=member.professional_certificate_no,
                    certificate_expiry_snapshot=member.certificate_expiry_date,
                ))

    if submit:
        if payload.id and decl.workflow_status == "CHANGES_REQUESTED":
            decl.cv_approval = "PENDING"
            decl.qlc_approval = "PENDING"
            decl.bp_approval = "PENDING"
        decl.workflow_status = "PENDING_REVIEW"
        decl.status = "SUBMITTED"
        decl.submitted_at = now_iso()
        event = DeclarationEvent(
            declaration_id=decl.id,
            action="SUBMIT",
            from_status="DRAFT",
            to_status="PENDING_REVIEW",
            actor_name=user.full_name or user.username,
            actor_role=user.role,
            actor_user_id=user.id,
            correlation_id=correlation_id.get(),
            note="Nộp phiếu khai báo",
            created_at=now_iso(),
        )
        db.add(event)

    audit(
        db, "DECLARATION", decl.id, "SUBMIT" if submit else ("UPDATE" if payload.id else "CREATE"),
        f"{decl.reference_no} / {decl.workflow_status}",
        actor_user_id=user.id, organization_id=decl.organization_id,
    )

    db.commit()
    db.refresh(decl)

    result = _declaration_dict(decl)
    result["id"] = decl.id
    result["status"] = decl.status
    return result


# ══════════════════════════════════════════════════════════════════════════════
# DECLARATION EVENTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/declarations/{declaration_id}/events")
def get_declaration_events(
    declaration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "CV", "QLC", "BP", "ADMIN")),
):
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")

    # Tenant isolation check
    verify_organization_ownership(user, decl.organization_id)

    events = (
        db.query(DeclarationEvent)
        .filter(DeclarationEvent.declaration_id == declaration_id)
        .order_by(DeclarationEvent.created_at)
        .all()
    )
    return [
        {col.name: getattr(e, col.name) for col in e.__table__.columns}
        for e in events
    ]


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/declarations/{declaration_id}/workflow")
def declaration_workflow(
    declaration_id: int,
    payload: WorkflowActionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CV", "QLC", "BP")),  # Deny CUSTOMER and ADMIN by default
):
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")

    # Role checks per action
    if payload.action == "CV_APPROVE" and user.role != "CV":
        raise HTTPException(status_code=403, detail="Chỉ CV mới có quyền thực hiện hành động này.")
    if payload.action == "QLC_APPROVE" and user.role != "QLC":
        raise HTTPException(status_code=403, detail="Chỉ QLC mới có quyền thực hiện hành động này.")
    if payload.action in ("BP_APPROVE", "ISSUE", "REVOKE") and user.role != "BP":
        raise HTTPException(status_code=403, detail="Chỉ BP mới có quyền thực hiện hành động này.")

    if payload.action == "REQUEST_CHANGES":
        current = decl.workflow_status
        if current == "PENDING_REVIEW" and user.role != "CV":
            raise HTTPException(status_code=403, detail="Chỉ CV mới có quyền yêu cầu chỉnh sửa ở giai đoạn này.")
        elif current == "PENDING_QLC" and user.role != "QLC":
            raise HTTPException(status_code=403, detail="Chỉ QLC mới có quyền yêu cầu chỉnh sửa ở giai đoạn này.")
        elif current == "PENDING_BP" and user.role != "BP":
            raise HTTPException(status_code=403, detail="Chỉ BP mới có quyền yêu cầu chỉnh sửa ở giai đoạn này.")
        elif current not in ("PENDING_REVIEW", "PENDING_QLC", "PENDING_BP"):
            raise HTTPException(status_code=400, detail="Không thể yêu cầu chỉnh sửa từ trạng thái hiện tại.")

    # Derive actor details strictly from JWT
    actor_role = user.role
    actor_name = user.full_name or user.username

    updated = _apply_workflow_transition(
        db=db,
        declaration=decl,
        action=payload.action,
        actor_role=actor_role,
        actor_name=actor_name,
        actor_user_id=user.id,
        note=payload.note,
        permit_no=payload.permit_no,
    )
    audit(
        db, "DECLARATION", declaration_id, payload.action,
        f"{actor_name} / {actor_role} / {updated.workflow_status}",
        actor_user_id=user.id, organization_id=updated.organization_id,
    )
    db.commit()
    db.refresh(updated)
    return _declaration_dict(updated)


# ══════════════════════════════════════════════════════════════════════════════
# ATTACHMENTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/declarations/{declaration_id}/attachments")
async def upload_attachment(
    declaration_id: int,
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "ADMIN")),
):
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")

    # Tenant isolation check
    verify_organization_ownership(user, decl.organization_id)

    content = await request.body()
    ext = Path(filename).suffix.lower()
    validate_attachment_content(ext, content)

    safe_name = f"{declaration_id}_{uuid.uuid4().hex}{ext}"
    stored_name = attachment_storage.put_quarantined(safe_name, content)
    scan_status = attachment_scanner.scan(stored_name)

    content_type = request.headers.get("content-type", "application/octet-stream")
    att = Attachment(
        declaration_id=declaration_id,
        original_name=filename[:255],
        stored_name=stored_name,
        content_type=content_type,
        size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        scan_status=scan_status,
        storage_backend=attachment_storage.backend_name,
        created_at=now_iso(),
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return {col.name: getattr(att, col.name) for col in att.__table__.columns}


# ══════════════════════════════════════════════════════════════════════════════
# SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════════════

_SUGGESTION_FIELDS = {
    "last_port": Declaration.last_port,
    "working_port": Declaration.working_port,
    "destination_port": Declaration.destination_port,
    "master_name": Declaration.master_name,
}


@app.get("/api/suggestions")
def get_suggestions(
    field: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "CV", "QLC", "BP", "ADMIN")),
):
    col = _SUGGESTION_FIELDS.get(field)
    if not col:
        return []

    query = db.query(col).filter(col.isnot(None), col != "")
    if user.role == "CUSTOMER":
        query = query.filter(Declaration.organization_id == user.organization_id)

    rows = (
        query
        .distinct()
        .order_by(col)
        .limit(50)
        .all()
    )
    return [r[0] for r in rows if r[0]]


# ══════════════════════════════════════════════════════════════════════════════
# IMPORT (Excel)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/import/vessels")
async def import_vessels(
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "ADMIN")),
):
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        sheets = read_workbook(content)
        org_data, rows = vessel_rows(sheets)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    # Scoping organization based on role
    if user.role == "CUSTOMER":
        org_id = user.organization_id
    else:
        org = _get_or_create_org(db, org_data.get("name"))
        org_id = org.id if org else None

    checksum = hashlib.sha256(content).hexdigest()
    if preview:
        db.rollback()
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "organization": org_data,
            "rows": [{"sourceRow": index, **row} for index, row in enumerate(rows, 11)],
            "accepted": 0,
            "rejected": [],
        }
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == org_id,
        ImportJob.import_kind == "VESSELS",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    accepted = 0
    rejected: list[dict] = []
    for source_row, row in enumerate(rows, 11):
        try:
            with db.begin_nested():
                existing = db.query(Vessel).filter(
                    Vessel.registration_no == row.get("registration_no")
                ).first()
                if existing:
                    verify_organization_ownership(user, existing.organization_id)
                    for k, v in row.items():
                        if hasattr(existing, k) and k not in ("id", "created_at", "organization_id"):
                            setattr(existing, k, excel_date(v) if "date" in k else v)
                    existing.organization_id = org_id
                    existing.updated_at = now_iso()
                    existing.version += 1
                else:
                    safe = {
                        k: (excel_date(v) if "date" in k else v)
                        for k, v in row.items()
                        if hasattr(Vessel, k) and k not in ("id", "organization_id")
                    }
                    safe["organization_id"] = org_id
                    safe["created_at"] = now_iso()
                    safe["updated_at"] = now_iso()
                    db.add(Vessel(**safe))
                db.flush()
            accepted += 1
        except Exception as exc:
            rejected.append({"sourceRow": source_row, "row": row.get("name"), "error": str(exc) or type(exc).__name__})
    result = {
        "accepted": accepted,
        "rejected": rejected,
        "mappingVersion": IMPORT_MAPPING_VERSION,
        "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=org_id, import_kind="VESSELS", source_checksum=checksum,
        mapping_version=IMPORT_MAPPING_VERSION, accepted_count=accepted,
        rejected_count=len(rejected), result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id, created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    result["importJobId"] = job.id
    return result


@app.post("/api/import/declaration")
async def import_declaration(
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER")),
):
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        sheets = read_workbook(content)
        row = declaration_row(sheets)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    checksum = hashlib.sha256(content).hexdigest()
    if preview:
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "row": row,
            "accepted": 0,
            "rejected": [],
        }
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == user.organization_id,
        ImportJob.import_kind == "DECLARATION",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    row["created_at"] = now_iso()
    row["updated_at"] = now_iso()
    row["reference_no"] = f"TT-IMP-{datetime.now():%Y%m%d-%H%M%S}-{datetime.now().microsecond:06d}"
    row["workflow_status"] = "DRAFT"
    row["status"] = "DRAFT"
    row["unload_json"] = json.dumps(cargo(row.pop("unload", {})), ensure_ascii=False)
    row["load_json"] = json.dumps(cargo(row.pop("load", {})), ensure_ascii=False)

    safe = {k: v for k, v in row.items() if hasattr(Declaration, k)}
    if not safe.get("declaration_date"):
        safe["declaration_date"] = date.today().isoformat()
    for required in ("company_name", "vessel_name", "registration_no", "vessel_type",
                     "vessel_class", "last_port", "working_port", "eta", "etd",
                     "master_name", "master_phone"):
        if not safe.get(required):
            safe[required] = "N/A"

    # Enforce CUSTOMER organization binding
    safe["organization_id"] = user.organization_id
    if user.organization:
        safe["company_name"] = user.organization.name

    decl = Declaration(**safe)
    db.add(decl)
    db.flush()
    result = {
        "accepted": 1, "rejected": [], "id": decl.id,
        "mappingVersion": IMPORT_MAPPING_VERSION, "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=user.organization_id, import_kind="DECLARATION",
        source_checksum=checksum, mapping_version=IMPORT_MAPPING_VERSION,
        accepted_count=1, rejected_count=0,
        result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id, created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(decl)
    db.refresh(job)
    result["importJobId"] = job.id
    return result


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS (Appendix 1 / 2 / 3)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/reports/{kind}")
def export_report(
    kind: str,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "CV", "QLC", "BP", "ADMIN")),
):
    if kind not in ("appendix1", "appendix2", "appendix3"):
        raise HTTPException(status_code=404, detail=f"Loại báo cáo '{kind}' không tồn tại.")

    if to:
        try:
            report_end = date.fromisoformat(to)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Ngày kết thúc báo cáo không hợp lệ.") from exc
    else:
        report_end = date.today()
        to = report_end.isoformat()
    if from_:
        try:
            report_start = date.fromisoformat(from_)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Ngày bắt đầu báo cáo không hợp lệ.") from exc
    else:
        report_start = date(report_end.year, 1, 1)
        from_ = report_start.isoformat()
    if report_start > report_end:
        raise HTTPException(status_code=422, detail="Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")

    query = db.query(Declaration).filter(
        Declaration.workflow_status.in_(["APPROVED", "ISSUED"])
    )
    if user.role == "CUSTOMER":
        query = query.filter(Declaration.organization_id == user.organization_id)

    if from_:
        query = query.filter(Declaration.declaration_date >= from_)
    if to:
        query = query.filter(Declaration.declaration_date <= to)
    decls = query.order_by(Declaration.declaration_date).all()

    if kind == "appendix1":
        headers = ["Mã phiếu", "Loại", "Phương tiện", "Số đăng ký", "ETA", "ETD",
                   "Cảng cuối", "Cảng làm hàng", "Thuyền trưởng", "Trạng thái"]
        rows = [[
            d.reference_no,
            "Vào cảng" if d.movement_type == "ARRIVAL" else "Rời cảng",
            d.vessel_name, d.registration_no,
            d.actual_arrival_at or d.eta, d.actual_departure_at or d.etd,
            d.last_port, d.working_port, d.master_name, d.workflow_status,
        ] for d in decls]
        title = "Phụ lục 1 — Cảng Tân Thuận"

    elif kind == "appendix2":
        headers = ["Nhóm hàng", "Tấn kỳ báo cáo", "TEU kỳ báo cáo", "TEU rỗng", "Lượt phiếu"]
        totals: dict[str, dict[str, float]] = {}
        for d in decls:
            for cargo_item in (json.loads(d.unload_json or "{}"), json.loads(d.load_json or "{}")):
                group = cargo_item.get("cargo_type") or "Khác"
                bucket = totals.setdefault(group, {"tons": 0, "teu": 0, "empty_teu": 0, "calls": 0})
                bucket["tons"] += float(cargo_item.get("tons") or 0)
                bucket["teu"] += float(cargo_item.get("teu") or 0)
                bucket["empty_teu"] += float(cargo_item.get("empty_teu") or 0)
                bucket["calls"] += 1
        rows = [[group, value["tons"], value["teu"], value["empty_teu"], value["calls"]] for group, value in sorted(totals.items())]
        rows.append(["Tổng", sum(v["tons"] for v in totals.values()), sum(v["teu"] for v in totals.values()), sum(v["empty_teu"] for v in totals.values()), len(decls)])
        title = "Phụ lục 2 — Cảng Tân Thuận"

    else:  # appendix3
        headers = ["Mã phiếu", "Tên PTTND", "Số đăng ký", "Loại", "Cấp", "Chiều dài", "DWT", "GT",
                   "Hướng hàng", "Loại hình", "Tên hàng", "Tấn", "TEU", "TEU rỗng", "Cảng rời", "Cảng làm hàng",
                   "Cảng đích", "Ngày đến", "Ngày rời", "Đại lý", "sum_total"]
        rows = []
        for d in decls:
            cargo_rows = [("Dỡ", json.loads(d.unload_json or "{}")), ("Xếp", json.loads(d.load_json or "{}"))]
            for direction, item in cargo_rows:
                if not any((item.get("cargo_type"), item.get("cargo_name"), item.get("tons"), item.get("teu"))):
                    continue
                tons, teu = float(item.get("tons") or 0), float(item.get("teu") or 0)
                rows.append([d.reference_no, d.vessel_name, d.registration_no, d.vessel_type, d.vessel_class,
                             d.length_m or 0, d.deadweight_tons or 0, d.gross_tonnage or 0, direction,
                             item.get("movement_type") or "", item.get("cargo_name") or "", tons, teu,
                             float(item.get("empty_teu") or 0), d.last_port, d.working_port, d.destination_port,
                             d.actual_arrival_at or d.eta, d.actual_departure_at or d.etd,
                             d.company_name, f"{tons} tấn / {teu} TEU"])
        title = "Phụ lục 3 — Cảng Sài Gòn-Cảng Tân Thuận"

    xlsx_bytes = make_xlsx(title, headers, rows)
    filename = f"report_{kind}_{from_ or 'all'}_{to or 'all'}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATIONS (Maritime Authority — PREPARE ONLY, no external calls in T0)
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_connector(db: Session) -> IntegrationConnector:
    connector = db.query(IntegrationConnector).filter(
        IntegrationConnector.connector_key == "maritime-authority"
    ).first()
    if not connector:
        connector = IntegrationConnector(
            connector_key="maritime-authority",
            display_name="Cảng vụ Đường thủy nội địa",
            status="NOT_CONFIGURED",
            auth_mode="PENDING_AUTHORITY_SPEC",
            updated_at=now_iso(),
        )
        db.add(connector)
        db.commit()
        db.refresh(connector)
    return connector


@app.get("/api/integrations/maritime-authority")
def get_integration_status(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("BP", "ADMIN")),
):
    connector = _ensure_connector(db)
    jobs = (
        db.query(SyncJob)
        .filter(SyncJob.connector_key == "maritime-authority")
        .order_by(desc(SyncJob.created_at))
        .limit(20)
        .all()
    )
    connector_dict = {c.name: getattr(connector, c.name) for c in connector.__table__.columns}
    connector_dict["readyToSend"] = connector.status == "READY"
    return {
        "connector": connector_dict,
        "adapter": maritime_authority_adapter().status(),
        "jobs": [
            {c.name: getattr(j, c.name) for c in j.__table__.columns}
            for j in jobs
        ],
    }


@app.post("/api/integrations/prepare-sync")
async def prepare_sync(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN")),
):
    """
    Prepare a sync payload (PREPARED status).
    Does NOT send data to any external API — that is out of scope until T6
    and requires official API contract, credentials and sandbox from the authority.
    """
    body = await request.json()
    from_ = body.get("from")
    to = body.get("to")

    query = db.query(Declaration).filter(
        Declaration.workflow_status == "ISSUED"
    )
    if from_:
        query = query.filter(Declaration.declaration_date >= from_)
    if to:
        query = query.filter(Declaration.declaration_date <= to)
    decls = query.all()

    payload_data = [
        {"reference_no": d.reference_no, "vessel_name": d.vessel_name,
         "permit_no": d.permit_no, "issued_at": d.issued_at}
        for d in decls
    ]

    job = SyncJob(
        connector_key="maritime-authority",
        report_from=from_ or "",
        report_to=to or "",
        status="PREPARED",
        record_count=len(payload_data),
        payload_json=json.dumps(payload_data, ensure_ascii=False),
        created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "id": job.id,
        "recordCount": job.record_count,
        "status": job.status,
        "note": "Payload đã chuẩn bị nhưng chưa gửi. External sync chưa được kích hoạt (chờ T6).",
    }


# ══════════════════════════════════════════════════════════════════════════════
# STATIC FRONTEND (must be last)
# ══════════════════════════════════════════════════════════════════════════════

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
