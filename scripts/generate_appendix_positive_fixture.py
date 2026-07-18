"""Generate isolated positive appendix workbooks through the application exporter.

The script uses an in-memory database and never reads or changes data/cang_vu.db.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import _appendix1_rows, _appendix2_rows, _appendix3_rows
from backend.database import cargo
from backend.models import Base, Declaration, Organization, Vessel, VesselOperatingProfile
from backend.xlsx_io import make_report_xlsx


OUTPUT_DIR = ROOT / "outputs" / "appendix-positive-fixture-20260717"


def declaration(**values) -> Declaration:
    defaults = {
        "reference_no": "QA-PLACEHOLDER",
        "status": "SUBMITTED",
        "workflow_status": "APPROVED",
        "declaration_date": "2046-07-01",
        "company_name": "DOANH NGHIỆP QA",
        "vessel_name": "SÀ LAN QA CANONICAL",
        "registration_no": "QA-CANONICAL-01",
        "vessel_type": "CHỞ HÀNG KHÔ HOẶC CONTAINER",
        "vessel_class": "VR-SI",
        "crew_count": 6,
        "passenger_count": 0,
        "last_port": "CẢNG A",
        "working_port": "CẦU 1 - CẢNG TÂN THUẬN",
        "departure_berth": "CẦU 2 - CẢNG TÂN THUẬN",
        "destination_port": "CẢNG C",
        "eta": "2046-07-15T08:00",
        "etd": "2046-07-15T18:00",
        "master_name": "THUYỀN TRƯỞNG QA",
        "master_phone": "0900000000",
        "movement_type": "ARRIVAL",
        "purpose": "Làm hàng",
        "cargo_description": "",
        "agent_ptnd_name": "ĐẠI LÝ PTND QA",
        "is_passenger_call": 1,
        "unload_json": json.dumps(cargo({}), ensure_ascii=False),
        "load_json": json.dumps(cargo({}), ensure_ascii=False),
    }
    defaults.update(values)
    return Declaration(**defaults)


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    organization = Organization(name="DOANH NGHIỆP QA")
    db.add(organization)
    db.flush()
    vessel = Vessel(
        organization_id=organization.id,
        name="SÀ LAN QA CANONICAL",
        registration_no="QA-CANONICAL-01",
        vessel_type="CHỞ HÀNG KHÔ HOẶC CONTAINER",
        vessel_class="VR-SI",
        length_m=58.5,
        deadweight_tons=920,
        gross_tonnage=410,
        cargo_capacity_tons=900,
        container_capacity_teu=48,
        passenger_capacity=80,
        certificate_expiry_date="2048-12-31",
        tracking_master_name="THUYỀN TRƯỞNG QA",
        tracking_master_phone="0900000000",
    )
    db.add(vessel)
    db.flush()
    db.add(VesselOperatingProfile(vessel_id=vessel.id, sequence=1, activity_area="VR-SI", deadweight_tons=920, cargo_capacity_tons=900))
    january = declaration(
        reference_no="QA-2046-01",
        organization_id=organization.id,
        vessel_id=vessel.id,
        declaration_date="2046-07-20",
        eta="2046-01-10T08:00",
        etd="2046-01-10T17:00",
        actual_arrival_at="2046-01-10T08:15",
        actual_departure_at="2046-01-10T16:50",
        agent_ptnd_name="ĐẠI LÝ PTND A",
        unload_json=json.dumps(cargo({"cargo_type": "Container", "movement_type": "Nhập khẩu", "cargo_name": "HÀNG NHẬP", "cont20_full": 1, "cont20_empty": 1, "tons": 12}), ensure_ascii=False),
    )
    july = declaration(
        reference_no="QA-2046-07",
        organization_id=organization.id,
        vessel_id=vessel.id,
        declaration_date="2046-01-02",
        actual_arrival_at="2046-07-15T08:20",
        actual_departure_at="2046-07-15T17:45",
        passenger_count=7,
        agent_ptnd_name="ĐẠI LÝ PTND B",
        load_json=json.dumps(cargo({"cargo_type": "Container", "movement_type": "Xuất khẩu", "cargo_name": "HÀNG XUẤT", "cont40_full": 1, "tons": 20}), ensure_ascii=False),
    )
    db.add_all([january, july])
    db.commit()

    current = [july]
    cumulative = [january, july]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "report_from": date(2046, 7, 1),
        "report_to": date(2046, 7, 31),
        "reporting_unit": "CÔNG TY CỔ PHẦN CẢNG TÂN THUẬN",
    }
    (OUTPUT_DIR / "PL.01_positive_fixture.xlsx").write_bytes(make_report_xlsx("appendix1", _appendix1_rows(db, current), **metadata))
    (OUTPUT_DIR / "PL.02_positive_fixture.xlsx").write_bytes(make_report_xlsx("appendix2", _appendix2_rows(current, cumulative), **metadata))
    (OUTPUT_DIR / "PL.03_positive_fixture.xlsx").write_bytes(make_report_xlsx(
        "appendix3", _appendix3_rows(db, cumulative), appendix3_template=ROOT / "templates" / "Phụ lục 3.xlsx", **metadata,
    ))
    (OUTPUT_DIR / "README.txt").write_text(
        "Synthetic positive QA fixture generated through the application exporter.\n"
        "It uses an in-memory database and does not contain operational/customer data.\n",
        encoding="utf-8",
    )
    db.close()
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
