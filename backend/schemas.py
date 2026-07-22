from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: str

class OrganizationBase(BaseModel):
    name: str
    tax_code: str = ""
    address: str = ""
    contact_name: str = ""
    contact_role: str = ""
    phone: str = ""
    email: str = ""

class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class VesselBase(BaseModel):
    organization_id: Optional[int] = None
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

class VesselResponse(VesselBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    certificate_status: Optional[str] = None
    organization_name: Optional[str] = None

class DeclarationBase(BaseModel):
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
    departure_berth: str = ""
    destination_port: str = ""
    agent_ptnd_name: str = ""
    is_passenger_call: bool = False
    eta: str
    etd: str
    master_name: str
    master_phone: str
    movement_type: str = "ARRIVAL"
    purpose: str = ""
    cargo_description: str = ""
    actual_arrival_at: Optional[str] = None
    actual_departure_at: Optional[str] = None

class CrewMember(BaseModel):
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

class CrewMemberResponse(CrewMember):
    model_config = ConfigDict(from_attributes=True)
    id: int
    certificate_status: Optional[str] = None
    vessel_name: Optional[str] = None
    registration_no: Optional[str] = None

class Cargo(BaseModel):
    cargo_type: str = ""
    movement_type: str = ""
    cargo_name: str = ""
    cont20_full: int = 0
    cont20_empty: int = 0
    cont40_full: int = 0
    cont40_empty: int = 0
    tons20_full: float = 0.0
    tons20_empty: float = 0.0
    tons40_full: float = 0.0
    tons40_empty: float = 0.0
    tons: float = 0.0

class DeclarationCreate(DeclarationBase):
    unload: Cargo
    load: Cargo
    crew_ids: List[int] = []

class DeclarationResponse(DeclarationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_no: str
    status: str
    workflow_status: str
    unload: Cargo
    load: Cargo
