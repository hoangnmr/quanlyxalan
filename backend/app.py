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
from datetime import date, datetime, timedelta, timezone
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
from .xlsx_io import (
    crew_rows, declaration_row, excel_date, import_match_key, make_xlsx,
    read_workbook, vessel_rows,
)
from scripts.backup_local import backup as create_local_backup, prune as prune_local_backups

IMPORT_MAPPING_VERSION = "KBCV-IMPORT-1.3"
DEMO_ORGANIZATION_TAX_CODE = "DEMO-TANTHUAN-2026"
CREW_ROLES = ("Thuyền trưởng", "Máy trưởng", "Thuyền viên", "Thuyền phó")
CREW_ROLE_CANONICAL = {import_match_key(role): role for role in CREW_ROLES}

ROOT = Path(__file__).resolve().parents[1]
access_logger = configure_local_logging(ROOT)
ATTACHMENT_DIR = ROOT / "data" / "attachments"
ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = ROOT / "data" / "backups"
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
    "PORT_APPROVE":      {"from": "PENDING_REVIEW",  "to": "APPROVED"},
    "REQUEST_CHANGES":   {"from": "PENDING_REVIEW",  "to": "CHANGES_REQUESTED"},
}

RETIRED_WORKFLOW_ACTIONS = frozenset({"CV_APPROVE", "QLC_APPROVE", "BP_APPROVE", "ISSUE", "REVOKE"})


def _apply_workflow_transition(
    db: Session, declaration: Declaration, action: str, actor_role: str,
    actor_name: str, actor_user_id: int, note: str = ""
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
    if action == "REQUEST_CHANGES" and not note.strip():
        raise HTTPException(status_code=400, detail="Cần nhập lý do cho thao tác này.")

    new_status = rule["to"]
    from_status = current
    declaration.workflow_status = new_status

    if action == "PORT_APPROVE":
        declaration.port_approval = "APPROVED"

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
    full_name: str
    crew_role: str
    birth_date: Optional[str] = None
    phone: str = ""
    identity_no: str = ""
    professional_certificate_type: str = ""
    professional_certificate_no: str = ""
    certificate_issue_date: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    notes: str = ""

    @field_validator("full_name", "professional_certificate_type", "professional_certificate_no")
    @classmethod
    def required_crew_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value

    @field_validator("crew_role")
    @classmethod
    def valid_crew_role(cls, value: str) -> str:
        canonical = CREW_ROLE_CANONICAL.get(import_match_key(value))
        if not canonical:
            raise ValueError(f"Chức danh phải là một trong: {', '.join(CREW_ROLES)}.")
        return canonical


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


class PrepareSyncRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: Optional[str] = None
    to: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PrepareSyncRequest":
        return cls(from_=data.get("from"), to=data.get("to"))


class NotificationPreferenceRequest(BaseModel):
    in_app_certificate_reminders: bool = True


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
        "organization_name": user.organization.name if user.organization else None,
        "notification_preferences": _notification_preferences(user),
    }


@app.post("/api/auth/logout")
def logout(user: User = Depends(get_current_user)):
    # Local client-side stateless token removal is primary, but we return 200 OK.
    return {"status": "ok", "detail": "Đăng xuất thành công."}


def _notification_preferences(user: User) -> dict[str, bool]:
    try:
        stored = json.loads(user.notification_preferences_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        stored = {}
    return {"in_app_certificate_reminders": bool(stored.get("in_app_certificate_reminders", True))}


@app.get("/api/notification-preferences")
def get_notification_preferences(user: User = Depends(get_current_user)):
    return _notification_preferences(user)


@app.put("/api/notification-preferences")
def update_notification_preferences(
    payload: NotificationPreferenceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    preferences = {"in_app_certificate_reminders": payload.in_app_certificate_reminders}
    # `user` is supplied by the authentication dependency and can be bound to
    # a separate request session. Persist through this endpoint's transaction.
    current_user = db.query(User).filter(User.id == user.id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="Không thể xác thực thông tin đăng nhập")
    current_user.notification_preferences_json = json.dumps(preferences, separators=(",", ":"))
    audit(
        db, "USER", current_user.id, "NOTIFICATION_PREFERENCES_UPDATE",
        f"in_app_certificate_reminders={payload.in_app_certificate_reminders}", actor_user_id=user.id,
        organization_id=current_user.organization_id,
    )
    db.commit()
    return preferences


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
    approved = [item for item in declarations if item.workflow_status == "APPROVED"]
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
    backups = list(BACKUP_DIR.glob("*.db")) if BACKUP_DIR.exists() else []
    latest_backup = max(backups, key=lambda item: item.stat().st_mtime).name if backups else None
    return {
        "period": {"from": year_start, "to": today.isoformat()},
        "operations": {"declarations": len(declarations), "approved": len(approved), "pending": len(pending), "tons": tons, "teu": teu},
        "fleet": {"vessels": db.query(Vessel).count(), "certificateWarnings": expiring},
        "imports": {"jobs": db.query(ImportJob).count(), "rejectedRows": db.query(func.coalesce(func.sum(ImportJob.rejected_count), 0)).scalar()},
        "storage": {"attachments": db.query(Attachment).count(), "backups": len(backups), "latestBackup": latest_backup},
        "security": {"failedLogins": db.query(AuditEvent).filter(AuditEvent.action.like("LOGIN_FAILURE%")).count(), "disabledUsers": db.query(User).filter(User.is_active == 0).count()},
    }


def _backup_record(path: Path) -> dict[str, Any]:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
    created_at = manifest.get("created_at") or datetime.fromtimestamp(
        path.stat().st_mtime, timezone.utc
    ).isoformat()
    return {
        "filename": path.name,
        "createdAt": created_at,
        "sizeBytes": path.stat().st_size,
        "integrityCheck": manifest.get("integrity_check", "unknown"),
        "sha256": manifest.get("sha256", ""),
    }


@app.get("/api/admin/backups")
def list_admin_backups(user: User = Depends(require_roles("ADMIN"))):
    del user
    if not BACKUP_DIR.exists():
        return []
    return [
        _backup_record(path)
        for path in sorted(
            BACKUP_DIR.glob("cang_vu-*.db"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    ]


@app.post("/api/admin/backups")
def create_admin_backup(
    db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN")),
):
    database = engine.url.database
    if engine.url.get_backend_name() != "sqlite" or not database or database == ":memory:":
        raise HTTPException(
            status_code=503,
            detail="Sao lưu trực tiếp chỉ khả dụng với cấu hình SQLite cục bộ.",
        )
    source = Path(database)
    if not source.exists():
        raise HTTPException(status_code=503, detail="Không tìm thấy cơ sở dữ liệu để sao lưu.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = BACKUP_DIR / f"cang_vu-{stamp}.db"
    try:
        create_local_backup(source, destination)
        removed = prune_local_backups(BACKUP_DIR)
    except Exception as exc:
        access_logger.exception("Local backup failed")
        raise HTTPException(status_code=500, detail="Không thể tạo bản sao lưu cục bộ.") from exc
    audit(
        db, "BACKUP", 0, "CREATE", destination.name,
        actor_user_id=user.id, organization_id=user.organization_id,
    )
    db.commit()
    return {**_backup_record(destination), "pruned": len(removed)}


def _get_or_create_org(db: Session, name: Optional[str]) -> Optional[Organization]:
    if not name:
        return None
    org = db.query(Organization).filter(Organization.name == name).first()
    if not org:
        org = Organization(name=name, updated_at=now_iso(), created_at=now_iso())
        db.add(org)
        db.flush()
    return org


def is_demo_data_active(db: Session) -> bool:
    return db.query(Organization.id).filter(
        Organization.tax_code == DEMO_ORGANIZATION_TAX_CODE
    ).first() is not None


def remove_demo_data_for_real_input(
    db: Session,
    *,
    retain_organization_id: int | None = None,
    organization_data: dict[str, Any] | None = None,
) -> bool:
    """Remove sentinel-marked records before the first real input.

    A demo CUSTOMER keeps its organization binding, but the sentinel is cleared
    and optional workbook metadata becomes the real profile. ADMIN imports may
    remove the demo organization entirely.
    """
    demo_org = db.query(Organization).filter(
        Organization.tax_code == DEMO_ORGANIZATION_TAX_CODE
    ).first()
    if not demo_org:
        return False

    declaration_ids = [row[0] for row in db.query(Declaration.id).filter(
        Declaration.organization_id == demo_org.id
    ).all()]
    if declaration_ids:
        db.query(Attachment).filter(Attachment.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(DeclarationCrew).filter(DeclarationCrew.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(DeclarationEvent).filter(DeclarationEvent.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(Declaration).filter(Declaration.id.in_(declaration_ids)).delete(synchronize_session=False)
    db.query(CrewMember).filter(CrewMember.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(Vessel).filter(Vessel.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(AuditEvent).filter(AuditEvent.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(ImportJob).filter(ImportJob.organization_id == demo_org.id).delete(synchronize_session=False)
    if retain_organization_id == demo_org.id:
        profile = organization_data or {}
        proposed_name = str(profile.get("name") or "").strip()
        name_in_use = proposed_name and db.query(Organization.id).filter(
            Organization.name == proposed_name, Organization.id != demo_org.id
        ).first()
        if proposed_name and not name_in_use:
            demo_org.name = proposed_name
        demo_org.tax_code = str(profile.get("tax_code") or "").strip()
        for field in ("address", "contact_name", "phone"):
            value = str(profile.get(field) or "").strip()
            if value:
                setattr(demo_org, field, value)
        demo_org.updated_at = now_iso()
    else:
        db.query(User).filter(User.organization_id == demo_org.id).update(
            {User.organization_id: None}, synchronize_session=False
        )
        db.delete(demo_org)
    db.flush()
    return True


def _attention_queue(db: Session, user: User) -> dict[str, Any]:
    """Return only the actionable/observable queue for the authenticated role."""
    role_rules = {
        "CUSTOMER": (["DRAFT", "CHANGES_REQUESTED"], "Phiếu cần khách hàng hoàn tất hoặc bổ sung"),
        "PORT_STAFF": (["PENDING_REVIEW"], "Phiếu chờ nhân viên Cảng xem xét"),
        "ADMIN": (["PENDING_REVIEW"], "Theo dõi các phiếu đang chờ Cảng xử lý"),
    }
    statuses, label = role_rules.get(user.role, ([], ""))
    if not statuses:
        return {"label": label, "count": 0, "items": []}
    query = db.query(Declaration).filter(Declaration.workflow_status.in_(statuses))
    if user.role == "CUSTOMER":
        query = query.filter(Declaration.organization_id == user.organization_id)
    declarations = query.order_by(Declaration.updated_at.asc(), Declaration.id.asc()).limit(5).all()
    now = datetime.now().astimezone()
    items = []
    for declaration in declarations:
        try:
            updated = datetime.fromisoformat(declaration.updated_at)
            age_hours = max(0, int((now - updated).total_seconds() // 3600))
        except (TypeError, ValueError):
            age_hours = None
        items.append({
            "id": declaration.id,
            "reference_no": declaration.reference_no,
            "vessel_name": declaration.vessel_name,
            "workflow_status": declaration.workflow_status,
            "updated_at": declaration.updated_at,
            "age_hours": age_hours,
        })
    return {"label": label, "count": query.count(), "items": items}


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
    elif user.role == "PORT_STAFF":
        # Port employees see all non-draft declarations.
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
        "attention": _attention_queue(db, user),
        "demo_mode": is_demo_data_active(db),
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
def get_vessels(db: Session = Depends(get_db), user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN"))):
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

    if not payload.id:
        remove_demo_data_for_real_input(
            db,
            retain_organization_id=org_id if user.role == "CUSTOMER" else None,
            organization_data=payload.organization if isinstance(payload.organization, dict) else None,
        )

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
def get_crew(db: Session = Depends(get_db), user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN"))):
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
    data = payload.model_dump(exclude={"id", "version"})
    data["vessel_id"] = None
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
    user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN")),
):
    query = db.query(Declaration)

    if user.role == "CUSTOMER":
        query = query.filter(Declaration.organization_id == user.organization_id)
    elif user.role == "PORT_STAFF":
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
            detail="Chỉ khách hàng/chủ phương tiện (CUSTOMER) mới có quyền xác nhận gửi phiếu khai báo."
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
                detail="Không thể chỉnh sửa phiếu đã xác nhận gửi. Dùng luồng REQUEST_CHANGES để điều chỉnh.",
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
            decl.port_approval = "PENDING"
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
            note="Khách hàng xác nhận gửi phiếu khai báo.",
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
    user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN")),
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
    user: User = Depends(require_roles("PORT_STAFF")),
):
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")

    if payload.action in RETIRED_WORKFLOW_ACTIONS:
        raise HTTPException(
            status_code=410,
            detail="Hành động thuộc quy trình cũ đã ngừng hỗ trợ. Dùng PORT_APPROVE hoặc REQUEST_CHANGES.",
        )

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
    user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN")),
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

VESSEL_IMPORT_COMPARE_FIELDS = {
    "name": "Tên phương tiện",
    "vessel_type": "Loại phương tiện",
    "vessel_class": "Cấp phương tiện",
    "registry_or_imo": "Số đăng kiểm / IMO",
    "shell_material": "Vật liệu vỏ",
    "build_year": "Năm đóng",
    "length_m": "Chiều dài",
    "width_m": "Chiều rộng",
    "side_height_m": "Chiều cao mạn",
    "draft_m": "Mớn nước",
    "deadweight_tons": "Trọng tải",
    "gross_tonnage": "Dung tích",
    "engine_power_cv": "Công suất",
    "cargo_capacity_tons": "Sức chở hàng",
    "container_capacity_teu": "Sức chở container",
    "passenger_capacity": "Sức chở khách",
    "min_crew": "Số thuyền viên",
    "safety_certificate_no": "Số chứng nhận an toàn",
    "certificate_issue_date": "Ngày cấp chứng nhận",
    "certificate_expiry_date": "Ngày hết hạn chứng nhận",
    "notes": "Ghi chú",
}


def _vessel_import_changes(existing: Vessel, row: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field, label in VESSEL_IMPORT_COMPARE_FIELDS.items():
        if field not in row:
            continue
        incoming = excel_date(row[field]) if "date" in field else row[field]
        current = getattr(existing, field, None)
        if current != incoming:
            changes.append({
                "field": field,
                "label": label,
                "current": current,
                "incoming": incoming,
            })
    return changes

@app.post("/api/import/vessels")
async def import_vessels(
    request: Request,
    preview: bool = False,
    overwrite_existing: bool = False,
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
    required_vessel_fields = {
        "name": "Tên phương tiện",
        "registration_no": "Số đăng ký",
        "vessel_type": "Loại phương tiện",
        "vessel_class": "Cấp phương tiện",
    }
    preview_rows = []
    conflict_count = 0
    for row in rows:
        clean_row = {key: value for key, value in row.items() if not key.startswith("_")}
        clean_row["sourceRow"] = row.get("_source_row")
        clean_row["sourceSheet"] = row.get("_source_sheet")
        clean_row["mappingWarnings"] = row.get("_mapping_warnings", [])
        clean_row["missingFields"] = [
            label for field, label in required_vessel_fields.items() if not row.get(field)
        ]
        existing = db.query(Vessel).filter(
            Vessel.registration_no == row.get("registration_no")
        ).first() if row.get("registration_no") else None
        if existing:
            conflict_count += 1
            same_scope = user.role == "ADMIN" or existing.organization_id == user.organization_id
            clean_row["existing"] = True
            clean_row["ownershipConflict"] = not same_scope
            if same_scope:
                clean_row["existingRecord"] = {
                    "id": existing.id,
                    "name": existing.name,
                    "registration_no": existing.registration_no,
                }
                clean_row["changes"] = _vessel_import_changes(existing, row)
        else:
            clean_row["existing"] = False
            clean_row["ownershipConflict"] = False
            clean_row["changes"] = []
        preview_rows.append(clean_row)
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == org_id,
        ImportJob.import_kind == "VESSELS",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if preview:
        db.rollback()
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "organization": org_data,
            "mapping": {
                "strategy": "HEADER_LABEL_DETECTION",
                "sheet": rows[0].get("_source_sheet") if rows else None,
            },
            "rows": preview_rows,
            "conflictCount": conflict_count,
            "previousImportId": prior.id if prior else None,
            "accepted": 0,
            "rejected": [],
        }
    if prior and not overwrite_existing:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    remove_demo_data_for_real_input(
        db,
        retain_organization_id=org_id if user.role == "CUSTOMER" else None,
        organization_data=org_data,
    )

    accepted = 0
    created = 0
    updated = 0
    skipped = 0
    rejected: list[dict] = []
    for row in rows:
        source_row = row.get("_source_row")
        missing_fields = [
            label for field, label in required_vessel_fields.items() if not row.get(field)
        ]
        if missing_fields:
            rejected.append({
                "sourceRow": source_row,
                "row": row.get("name"),
                "error": f"Thiếu {', '.join(missing_fields)}",
            })
            continue
        try:
            with db.begin_nested():
                existing = db.query(Vessel).filter(
                    Vessel.registration_no == row.get("registration_no")
                ).first()
                if existing:
                    if not overwrite_existing:
                        skipped += 1
                        continue
                    verify_organization_ownership(user, existing.organization_id)
                    for k, v in row.items():
                        if hasattr(existing, k) and k not in ("id", "created_at", "organization_id"):
                            setattr(existing, k, excel_date(v) if "date" in k else v)
                    existing.organization_id = org_id
                    existing.updated_at = now_iso()
                    existing.version += 1
                    updated += 1
                else:
                    safe = {
                        k: (excel_date(v) if "date" in k else v)
                        for k, v in row.items()
                        if not k.startswith("_") and hasattr(Vessel, k) and k not in ("id", "organization_id")
                    }
                    safe["organization_id"] = org_id
                    safe["created_at"] = now_iso()
                    safe["updated_at"] = now_iso()
                    db.add(Vessel(**safe))
                    created += 1
                db.flush()
            accepted += 1
        except Exception:
            access_logger.exception(
                "Vessel import row rejected source_row=%s registration_no=%s",
                source_row, row.get("registration_no"),
            )
            rejected.append({
                "sourceRow": source_row,
                "row": row.get("name"),
                "error": "Không thể nhập dòng này. Hãy kiểm tra định dạng số, ngày hoặc mã đăng ký trùng.",
            })
    result = {
        "accepted": accepted,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "rejected": rejected,
        "mappingVersion": IMPORT_MAPPING_VERSION,
        "checksum": checksum,
        "idempotent": False,
    }
    if prior:
        result["reapplied"] = True
        result["importJobId"] = prior.id
        prior.accepted_count = accepted
        prior.rejected_count = len(rejected)
        prior.result_json = json.dumps(result, ensure_ascii=False)
        db.commit()
        return result
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


CREW_IMPORT_COMPARE_FIELDS = {
    "full_name": "Họ và tên",
    "crew_role": "Chức danh",
    "birth_date": "Ngày sinh",
    "phone": "Số điện thoại",
    "identity_no": "CCCD / Hộ chiếu",
    "professional_certificate_type": "Loại chứng chỉ",
    "professional_certificate_no": "Số chứng chỉ",
    "certificate_issue_date": "Ngày cấp",
    "certificate_expiry_date": "Ngày hết hạn",
    "notes": "Ghi chú",
}


def _import_organization(db: Session, name: str) -> Organization | None:
    key = import_match_key(name)
    return next(
        (organization for organization in db.query(Organization).all()
         if import_match_key(organization.name) == key),
        None,
    )


def _existing_import_crew(
    db: Session, organization_id: int, row: dict[str, Any],
) -> CrewMember | None:
    query = db.query(CrewMember).filter(CrewMember.organization_id == organization_id)
    identity_no = str(row.get("identity_no") or "").strip()
    certificate_no = str(row.get("professional_certificate_no") or "").strip()
    if identity_no:
        existing = query.filter(CrewMember.identity_no == identity_no).first()
        if existing:
            return existing
    if certificate_no:
        return query.filter(CrewMember.professional_certificate_no == certificate_no).first()
    birth_date = row.get("birth_date")
    if birth_date:
        return query.filter(
            CrewMember.full_name == row.get("full_name"),
            CrewMember.birth_date == birth_date,
        ).first()
    return None


def _crew_import_changes(existing: CrewMember, row: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field, label in CREW_IMPORT_COMPARE_FIELDS.items():
        if field not in row:
            continue
        current = getattr(existing, field, None)
        incoming = row[field]
        if current != incoming:
            changes.append({
                "field": field,
                "label": label,
                "current": current,
                "incoming": incoming,
            })
    return changes


@app.post("/api/import/crew")
async def import_crew(
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PORT_STAFF", "ADMIN")),
):
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        rows = crew_rows(read_workbook(content))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    checksum = hashlib.sha256(content).hexdigest()
    required_fields = {
        "organization_name": "Tên doanh nghiệp",
        "full_name": "Họ và tên",
        "crew_role": "Chức danh",
    }
    prepared: list[tuple[dict[str, Any], Organization | None, CrewMember | None]] = []
    preview_rows: list[dict[str, Any]] = []
    for row in rows:
        raw_role = str(row.get("crew_role") or "")
        canonical_role = CREW_ROLE_CANONICAL.get(import_match_key(raw_role))
        if canonical_role:
            row["crew_role"] = canonical_role
        elif raw_role:
            row["_invalid_crew_role"] = raw_role
        organization = _import_organization(db, str(row.get("organization_name") or ""))
        existing = _existing_import_crew(db, organization.id, row) if organization else None
        missing = [label for field, label in required_fields.items() if not row.get(field)]
        if row.get("_invalid_crew_role"):
            missing.append("Chức danh hợp lệ")
        if row.get("organization_name") and not organization:
            missing.append("Doanh nghiệp đã có trong hệ thống")
        clean = {key: value for key, value in row.items() if not key.startswith("_")}
        clean.update({
            "sourceRow": row.get("_source_row"),
            "sourceSheet": row.get("_source_sheet"),
            "mappingWarnings": row.get("_mapping_warnings", []),
            "missingFields": missing,
            "existing": bool(existing),
            "changes": _crew_import_changes(existing, row) if existing else [],
        })
        preview_rows.append(clean)
        prepared.append((row, organization, existing))

    recognized_organization_ids = {
        organization.id for _, organization, _ in prepared if organization
    }
    if len(recognized_organization_ids) > 1:
        raise HTTPException(
            status_code=422,
            detail="Mỗi file thuyền viên chỉ được chứa dữ liệu của một doanh nghiệp.",
        )
    job_organization_id = next(iter(recognized_organization_ids), None)
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == job_organization_id,
        ImportJob.import_kind == "CREW",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if preview:
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "mapping": {
                "strategy": "HEADER_LABEL_DETECTION",
                "sheet": rows[0].get("_source_sheet") if rows else None,
            },
            "rows": preview_rows,
            "previousImportId": prior.id if prior else None,
            "accepted": 0,
            "rejected": [],
        }
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result
    if job_organization_id is None:
        raise HTTPException(
            status_code=422,
            detail="File không có doanh nghiệp nào khớp với dữ liệu hệ thống.",
        )

    created = 0
    updated = 0
    rejected: list[dict[str, Any]] = []
    for row, organization, existing in prepared:
        missing = [label for field, label in required_fields.items() if not row.get(field)]
        if row.get("_invalid_crew_role"):
            missing.append("Chức danh hợp lệ")
        if row.get("organization_name") and not organization:
            missing.append("Doanh nghiệp đã có trong hệ thống")
        if missing:
            rejected.append({
                "sourceRow": row.get("_source_row"),
                "row": row.get("full_name"),
                "error": f"Thiếu hoặc không hợp lệ: {', '.join(missing)}",
            })
            continue
        data = {
            key: value for key, value in row.items()
            if not key.startswith("_") and key != "organization_name" and hasattr(CrewMember, key)
        }
        data["organization_id"] = organization.id
        data["vessel_id"] = None
        data["updated_at"] = now_iso()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.version += 1
            member = existing
            updated += 1
            action = "IMPORT_UPDATE"
        else:
            data["created_at"] = now_iso()
            member = CrewMember(**data)
            db.add(member)
            created += 1
            action = "IMPORT_CREATE"
        db.flush()
        audit(
            db, "CREW", member.id, action, f"{member.full_name} / {member.crew_role}",
            actor_user_id=user.id, organization_id=organization.id,
        )

    result = {
        "accepted": created + updated,
        "created": created,
        "updated": updated,
        "rejected": rejected,
        "mappingVersion": IMPORT_MAPPING_VERSION,
        "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=job_organization_id,
        import_kind="CREW",
        source_checksum=checksum,
        mapping_version=IMPORT_MAPPING_VERSION,
        accepted_count=result["accepted"],
        rejected_count=len(rejected),
        result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id,
        created_at=now_iso(),
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
    user: User = Depends(require_roles("CUSTOMER", "ADMIN")),
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
    row["created_at"] = now_iso()
    row["updated_at"] = now_iso()
    row["reference_no"] = f"TT-IMP-{datetime.now():%Y%m%d-%H%M%S}-{datetime.now().microsecond:06d}"
    row["workflow_status"] = "DRAFT"
    row["status"] = "DRAFT"
    row["unload_json"] = json.dumps(cargo(row.pop("unload", {})), ensure_ascii=False)
    row["load_json"] = json.dumps(cargo(row.pop("load", {})), ensure_ascii=False)

    safe = {k: v for k, v in row.items() if not k.startswith("_") and hasattr(Declaration, k)}
    imported_company_name = str(safe.get("company_name") or "").strip()
    if not safe.get("declaration_date"):
        safe["declaration_date"] = date.today().isoformat()
    for required in ("company_name", "vessel_name", "registration_no", "vessel_type",
                     "vessel_class", "last_port", "working_port", "eta", "etd",
                     "master_name", "master_phone"):
        if not safe.get(required):
            safe[required] = "N/A"

    # CUSTOMER imports stay tenant-bound. ADMIN may import a declaration sent by
    # any customer and the workbook company name selects (or creates) its tenant.
    if user.role == "CUSTOMER":
        target_organization = user.organization
    else:
        if not imported_company_name:
            raise HTTPException(status_code=422, detail="File phải có tên doanh nghiệp để Admin nhập phiếu khai báo.")
        target_organization = _import_organization(db, imported_company_name)
        if target_organization is None:
            target_organization = _get_or_create_org(db, imported_company_name)
    if target_organization is None:
        raise HTTPException(status_code=422, detail="File phải có tên doanh nghiệp để Admin nhập phiếu khai báo.")

    target_organization_id = target_organization.id
    safe["organization_id"] = target_organization_id

    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == target_organization_id,
        ImportJob.import_kind == "DECLARATION",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    remove_demo_data_for_real_input(
        db,
        retain_organization_id=target_organization_id,
        organization_data={"name": imported_company_name},
    )
    safe["company_name"] = target_organization.name

    decl = Declaration(**safe)
    db.add(decl)
    db.flush()
    result = {
        "accepted": 1, "rejected": [], "id": decl.id,
        "mappingVersion": IMPORT_MAPPING_VERSION, "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=target_organization_id, import_kind="DECLARATION",
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

ANALYTICS_PERIODS = {"week", "month", "quarter", "year"}


def _month_shift(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _analytics_period(period: str, anchor: date) -> dict[str, Any]:
    if period == "week":
        current_start = anchor - timedelta(days=anchor.weekday())
        current_end = current_start + timedelta(days=6)
        previous_start = current_start - timedelta(days=364)
        labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        bucket = lambda value, start: (value - start).days
        title = "Tổng hợp theo tuần"
        trend_title = "Lượt tàu theo ngày"
        compare = "Tuần này so với cùng kỳ năm trước"
    elif period == "month":
        current_start = anchor.replace(day=1)
        current_end = _month_shift(current_start, 1) - timedelta(days=1)
        previous_start = date(current_start.year - 1, current_start.month, 1)
        labels = [f"Tuần {index}" for index in range(1, 6)]
        bucket = lambda value, start: min(4, (value.day - 1) // 7)
        title = "Tổng hợp theo tháng"
        trend_title = "Lượt tàu theo tuần"
        compare = f"Tháng {current_start.month}/{current_start.year} so với cùng kỳ {previous_start.year}"
    elif period == "quarter":
        quarter_month = ((anchor.month - 1) // 3) * 3 + 1
        current_start = date(anchor.year, quarter_month, 1)
        current_end = _month_shift(current_start, 3) - timedelta(days=1)
        previous_start = date(current_start.year - 1, current_start.month, 1)
        labels = [f"T{_month_shift(current_start, index).month}" for index in range(3)]
        bucket = lambda value, start: (value.year - start.year) * 12 + value.month - start.month
        title = "Tổng hợp theo quý"
        trend_title = "Lượt tàu theo tháng"
        compare = f"Quý {(quarter_month - 1) // 3 + 1}/{current_start.year} so với cùng kỳ {previous_start.year}"
    else:
        current_start = date(anchor.year, 1, 1)
        current_end = date(anchor.year, 12, 31)
        previous_start = date(anchor.year - 1, 1, 1)
        labels = [f"T{index}" for index in range(1, 13)]
        bucket = lambda value, start: value.month - 1
        title = "Tổng hợp theo năm"
        trend_title = "Lượt tàu theo tháng"
        compare = f"Năm {anchor.year} so với {anchor.year - 1}"
    if period == "week":
        previous_end = previous_start + timedelta(days=6)
    elif period == "month":
        previous_end = _month_shift(previous_start, 1) - timedelta(days=1)
    elif period == "quarter":
        previous_end = _month_shift(previous_start, 3) - timedelta(days=1)
    else:
        previous_end = date(previous_start.year, 12, 31)
    return {
        "current_start": current_start,
        "current_end": current_end,
        "previous_start": previous_start,
        "previous_end": previous_end,
        "labels": labels,
        "bucket": bucket,
        "title": title,
        "trend_title": trend_title,
        "compare": compare,
    }


def _declaration_operating_date(declaration: Declaration) -> date | None:
    for raw in (declaration.actual_arrival_at, declaration.eta, declaration.declaration_date):
        if not raw:
            continue
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            continue
    return None


def _declaration_metrics(declaration: Declaration) -> dict[str, float]:
    def numeric(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    tons = 0.0
    teu = 0.0
    for raw in (declaration.unload_json, declaration.load_json):
        try:
            item = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            item = {}
        tons += numeric(item.get("tons"))
        teu += numeric(item.get("teu"))
    return {
        "trips": 1.0,
        "tons": tons,
        "teu": teu,
        "pax": numeric(declaration.passenger_count),
    }


def _analytics_payload(db: Session, user: User, period: str, anchor: date) -> dict[str, Any]:
    config = _analytics_period(period, anchor)
    query = db.query(Declaration).filter(Declaration.workflow_status == "APPROVED")
    if user.role == "CUSTOMER":
        query = query.filter(Declaration.organization_id == user.organization_id)
    declarations = query.all()
    totals = {
        "cur": {key: 0.0 for key in ("trips", "tons", "teu", "pax")},
        "prev": {key: 0.0 for key in ("trips", "tons", "teu", "pax")},
    }
    trend_current = [0] * len(config["labels"])
    trend_previous = [0] * len(config["labels"])
    for declaration in declarations:
        operating_date = _declaration_operating_date(declaration)
        if not operating_date:
            continue
        if config["current_start"] <= operating_date <= config["current_end"]:
            group = "cur"
            trend = trend_current
            start = config["current_start"]
        elif config["previous_start"] <= operating_date <= config["previous_end"]:
            group = "prev"
            trend = trend_previous
            start = config["previous_start"]
        else:
            continue
        for key, value in _declaration_metrics(declaration).items():
            totals[group][key] += value
        index = config["bucket"](operating_date, start)
        if 0 <= index < len(trend):
            trend[index] += 1
    return {
        "period": period,
        "asOf": anchor.isoformat(),
        "dataSource": "DEMO" if is_demo_data_active(db) else "OPERATIONAL",
        "kpis": {
            key: {"cur": totals["cur"][key], "prev": totals["prev"][key]}
            for key in totals["cur"]
        },
        "trend": {"labels": config["labels"], "cur": trend_current, "prev": trend_previous},
        "meta": {
            "analyticsTitle": config["title"],
            "trendTitle": config["trend_title"],
            "trendSub": f"{config['current_start'].isoformat()} → {config['current_end'].isoformat()}",
            "compareSub": config["compare"],
        },
    }


@app.get("/api/reports/analytics")
def report_analytics(
    period: str = "month",
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN")),
):
    if period not in ANALYTICS_PERIODS:
        raise HTTPException(status_code=422, detail="Kỳ thống kê phải là week, month, quarter hoặc year.")
    return _analytics_payload(db, user, period, as_of or date.today())


@app.get("/api/reports/analytics/export")
def export_analytics(
    period: str = "month",
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN")),
):
    if period not in ANALYTICS_PERIODS:
        raise HTTPException(status_code=422, detail="Kỳ thống kê không hợp lệ.")
    payload = _analytics_payload(db, user, period, as_of or date.today())
    labels = {"trips": "Lượt tàu", "tons": "Khối lượng (tấn)", "teu": "TEU", "pax": "Hành khách"}
    rows = [[labels[key], values["cur"], values["prev"], values["cur"] - values["prev"]] for key, values in payload["kpis"].items()]
    content = make_xlsx(payload["meta"]["analyticsTitle"], ["Chỉ tiêu", "Kỳ này", "Kỳ trước", "Chênh lệch"], rows)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="analytics_{period}_{payload["asOf"]}.xlsx"'},
    )

@app.get("/api/reports/{kind}")
def export_report(
    kind: str,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("CUSTOMER", "PORT_STAFF", "ADMIN")),
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
        Declaration.workflow_status == "APPROVED"
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
    user: User = Depends(require_roles("ADMIN")),
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
        Declaration.workflow_status == "APPROVED"
    )
    if from_:
        query = query.filter(Declaration.declaration_date >= from_)
    if to:
        query = query.filter(Declaration.declaration_date <= to)
    decls = query.all()

    payload_data = [
        {"reference_no": d.reference_no, "vessel_name": d.vessel_name,
         "workflow_status": d.workflow_status}
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
