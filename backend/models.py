from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, backref

Base = declarative_base()

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, default="")
    role = Column(String, default="CUSTOMER")  # ADMIN, CV, QLC, BP, CUSTOMER
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    is_active = Column(Integer, nullable=False, default=1)  # Using Integer (0 or 1) as SQLite boolean
    created_at = Column(String, default=now_iso)

    organization = relationship("Organization", back_populates="users", lazy="select")

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    tax_code = Column(String, nullable=False, default="")
    address = Column(String, nullable=False, default="")
    contact_name = Column(String, nullable=False, default="")
    contact_role = Column(String, nullable=False, default="")
    phone = Column(String, nullable=False, default="")
    email = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    vessels = relationship("Vessel", back_populates="organization", lazy="dynamic")
    users = relationship("User", back_populates="organization", lazy="dynamic")
    crew_members = relationship("CrewMember", back_populates="organization", lazy="dynamic")
    declarations = relationship("Declaration", back_populates="organization", lazy="dynamic")

class Vessel(Base):
    __tablename__ = "vessels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    name = Column(String, nullable=False)
    registration_no = Column(String, nullable=False, unique=True)
    registry_or_imo = Column(String, nullable=False, default="")
    vessel_type = Column(String, nullable=False)
    vessel_class = Column(String, nullable=False)
    shell_material = Column(String, nullable=False, default="")
    build_year = Column(Integer)
    length_m = Column(Float)
    width_m = Column(Float)
    side_height_m = Column(Float)
    draft_m = Column(Float)
    deadweight_tons = Column(Float)
    gross_tonnage = Column(Float)
    engine_power_cv = Column(Float)
    cargo_capacity_tons = Column(Float)
    container_capacity_teu = Column(Float)
    passenger_capacity = Column(Integer)
    min_crew = Column(Integer)
    safety_certificate_no = Column(String, nullable=False, default="")
    certificate_issue_date = Column(String)
    certificate_expiry_date = Column(String)
    registry_verification_status = Column(String, nullable=False, default="NOT_VERIFIED")
    registry_verified_at = Column(String)
    registry_verification_source = Column(String, nullable=False, default="")
    notes = Column(Text, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    version = Column(Integer, nullable=False, default=1)
    organization = relationship("Organization", back_populates="vessels", lazy="select")
    crew_members = relationship("CrewMember", back_populates="vessel", lazy="dynamic")
    declarations = relationship("Declaration", back_populates="vessel", lazy="dynamic")

class Declaration(Base):
    __tablename__ = "declarations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_no = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="DRAFT")
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    vessel_id = Column(Integer, ForeignKey("vessels.id"))
    declaration_date = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    vessel_name = Column(String, nullable=False)
    registration_no = Column(String, nullable=False)
    vessel_type = Column(String, nullable=False)
    vessel_class = Column(String, nullable=False)
    length_m = Column(Float)
    deadweight_tons = Column(Float)
    gross_tonnage = Column(Float)
    certificate_expiry_date = Column(String)
    crew_count = Column(Integer, nullable=False, default=0)
    passenger_count = Column(Integer, nullable=False, default=0)
    last_port = Column(String, nullable=False)
    working_port = Column(String, nullable=False)
    destination_port = Column(String, nullable=False, default="")
    eta = Column(String, nullable=False)
    etd = Column(String, nullable=False)
    unload_json = Column(Text, nullable=False)
    load_json = Column(Text, nullable=False)
    master_name = Column(String, nullable=False)
    master_phone = Column(String, nullable=False)
    movement_type = Column(String, nullable=False, default="ARRIVAL")
    purpose = Column(String, nullable=False, default="")
    cargo_description = Column(String, nullable=False, default="")
    actual_arrival_at = Column(String)
    actual_departure_at = Column(String)
    workflow_status = Column(String, nullable=False, default="DRAFT")
    cv_approval = Column(String, nullable=False, default="PENDING")
    qlc_approval = Column(String, nullable=False, default="PENDING")
    bp_approval = Column(String, nullable=False, default="PENDING")
    permit_no = Column(String, nullable=False, default="")
    issued_at = Column(String)
    revoked_at = Column(String)
    submitted_at = Column(String)
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    version = Column(Integer, nullable=False, default=1)
    organization = relationship("Organization", back_populates="declarations", lazy="select")
    vessel = relationship("Vessel", back_populates="declarations", lazy="select")
    crew_links = relationship("DeclarationCrew", back_populates="declaration", cascade="all, delete-orphan")
    events = relationship("DeclarationEvent", back_populates="declaration", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="declaration", cascade="all, delete-orphan")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    correlation_id = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)

class DeclarationEvent(Base):
    __tablename__ = "declaration_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    declaration_id = Column(Integer, ForeignKey("declarations.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)
    from_status = Column(String, nullable=False, default="")
    to_status = Column(String, nullable=False)
    actor_name = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    correlation_id = Column(String, nullable=False, default="")
    note = Column(Text, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)
    declaration = relationship("Declaration", back_populates="events")

class CrewMember(Base):
    __tablename__ = "crew_members"
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    vessel_id = Column(Integer, ForeignKey("vessels.id"))
    full_name = Column(String, nullable=False)
    crew_role = Column(String, nullable=False)
    phone = Column(String, nullable=False, default="")
    identity_no = Column(String, nullable=False, default="")
    professional_certificate_type = Column(String, nullable=False)
    professional_certificate_no = Column(String, nullable=False)
    certificate_issue_date = Column(String)
    certificate_expiry_date = Column(String)
    notes = Column(Text, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    version = Column(Integer, nullable=False, default=1)
    organization = relationship("Organization", back_populates="crew_members", lazy="select")
    vessel = relationship("Vessel", back_populates="crew_members", lazy="select")
    declaration_links = relationship("DeclarationCrew", back_populates="crew_member")

class DeclarationCrew(Base):
    __tablename__ = "declaration_crew"
    declaration_id = Column(Integer, ForeignKey("declarations.id", ondelete="CASCADE"), primary_key=True)
    crew_member_id = Column(Integer, ForeignKey("crew_members.id"), primary_key=True)
    crew_role_snapshot = Column(String, nullable=False)
    certificate_no_snapshot = Column(String, nullable=False)
    certificate_expiry_snapshot = Column(String)
    declaration = relationship("Declaration", back_populates="crew_links")
    crew_member = relationship("CrewMember", back_populates="declaration_links")

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    declaration_id = Column(Integer, ForeignKey("declarations.id", ondelete="CASCADE"), nullable=False)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False, unique=True)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False, default=now_iso)
    declaration = relationship("Declaration", back_populates="attachments")

class IntegrationConnector(Base):
    __tablename__ = "integration_connectors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    connector_key = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="NOT_CONFIGURED")
    base_url = Column(String, nullable=False, default="")
    auth_mode = Column(String, nullable=False, default="PENDING_AUTHORITY_SPEC")
    last_sync_at = Column(String)
    updated_at = Column(String, nullable=False, default=now_iso)

class SyncJob(Base):
    __tablename__ = "sync_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    connector_key = Column(String, nullable=False)
    report_from = Column(String, nullable=False)
    report_to = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PREPARED")
    record_count = Column(Integer, nullable=False, default=0)
    payload_json = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=now_iso)
    sent_at = Column(String)


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("organization_id", "import_kind", "source_checksum", "mapping_version", name="uq_import_idempotency"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    import_kind = Column(String, nullable=False)
    source_checksum = Column(String, nullable=False)
    mapping_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="COMPLETED")
    accepted_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    result_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(String, nullable=False, default=now_iso)
