#!/usr/bin/env python
"""Seed the local UI with clearly marked, disposable demonstration data.

The seed refuses to run when normal operational records exist. The application
removes this sentinel-marked dataset automatically on the first real vessel
create or vessel import.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal, now_iso
from backend.models import CrewMember, Declaration, Organization, Vessel

DEMO_ORGANIZATION_TAX_CODE = "DEMO-TANTHUAN-2026"


def cargo(name: str, tons: float, teu: int = 0) -> str:
    return json.dumps({
        "cargo_type": "Container" if teu else "Hàng khô",
        "cargo_name": name,
        "tons": tons,
        "teu": teu,
        "cont20_full": teu,
        "cont20_empty": 0,
        "cont40_full": 0,
        "cont40_empty": 0,
    }, ensure_ascii=False)


def main() -> None:
    db = SessionLocal()
    try:
        demo = db.query(Organization).filter(
            Organization.tax_code == DEMO_ORGANIZATION_TAX_CODE
        ).first()
        if demo:
            print("Demo data already exists; no records changed.")
            return
        real_records = db.query(Vessel.id).first() or db.query(Declaration.id).first() or db.query(CrewMember.id).first()
        if real_records:
            print("Refusing to seed demo data because operational records already exist.", file=sys.stderr)
            raise SystemExit(1)

        now = now_iso()
        demo = Organization(
            name="DỮ LIỆU MINH HỌA — CẢNG TÂN THUẬN",
            tax_code=DEMO_ORGANIZATION_TAX_CODE,
            address="Cảng Tân Thuận, Quận 7, TP. Hồ Chí Minh",
            contact_name="Điều phối mẫu",
            contact_role="Khai thác cảng",
            phone="028-0000-0000",
            email="demo@example.invalid",
            created_at=now,
            updated_at=now,
        )
        db.add(demo)
        db.flush()

        vessels = [
            Vessel(organization_id=demo.id, name="Sà lan SG-168", registration_no="SG-DEMO-168", vessel_type="Sà lan", vessel_class="VR-SII", deadweight_tons=850, cargo_capacity_tons=780, min_crew=4, safety_certificate_no="ATKT-DEMO-168", certificate_expiry_date="2026-08-05", created_at=now, updated_at=now),
            Vessel(organization_id=demo.id, name="Tàu container Tân Thuận 01", registration_no="SG-DEMO-001", vessel_type="Tàu container", vessel_class="VR-SI", deadweight_tons=1200, container_capacity_teu=96, min_crew=6, safety_certificate_no="ATKT-DEMO-001", certificate_expiry_date="2026-12-31", created_at=now, updated_at=now),
            Vessel(organization_id=demo.id, name="Tàu hàng Nam Sài Gòn", registration_no="SG-DEMO-215", vessel_type="Tàu hàng khô", vessel_class="VR-SII", deadweight_tons=640, cargo_capacity_tons=610, min_crew=5, safety_certificate_no="ATKT-DEMO-215", certificate_expiry_date="2026-07-20", created_at=now, updated_at=now),
            Vessel(organization_id=demo.id, name="Tàu kéo Bạch Đằng", registration_no="SG-DEMO-088", vessel_type="Tàu kéo/đẩy", vessel_class="VR-SIII", deadweight_tons=210, min_crew=3, safety_certificate_no="ATKT-DEMO-088", certificate_expiry_date="2027-03-15", created_at=now, updated_at=now),
        ]
        db.add_all(vessels)
        db.flush()

        db.add_all([
            CrewMember(organization_id=demo.id, vessel_id=vessels[0].id, full_name="Nguyễn Văn Hải", crew_role="Thuyền trưởng", phone="0900 111 168", professional_certificate_type="Thuyền trưởng hạng II", professional_certificate_no="TT-DEMO-001", certificate_expiry_date="2027-02-10", created_at=now, updated_at=now),
            CrewMember(organization_id=demo.id, vessel_id=vessels[1].id, full_name="Trần Minh Quân", crew_role="Máy trưởng", phone="0900 222 001", professional_certificate_type="Máy trưởng hạng II", professional_certificate_no="MT-DEMO-002", certificate_expiry_date="2026-09-15", created_at=now, updated_at=now),
            CrewMember(organization_id=demo.id, vessel_id=vessels[2].id, full_name="Lê Quốc Bảo", crew_role="Thuyền phó", phone="0900 333 215", professional_certificate_type="Thuyền phó hạng II", professional_certificate_no="TP-DEMO-003", certificate_expiry_date="2026-07-18", created_at=now, updated_at=now),
            CrewMember(organization_id=demo.id, vessel_id=vessels[3].id, full_name="Phạm Đức Long", crew_role="Máy phó", phone="0900 444 088", professional_certificate_type="Máy phó hạng III", professional_certificate_no="MP-DEMO-004", certificate_expiry_date="2027-01-30", created_at=now, updated_at=now),
        ])

        statuses = ["DRAFT", "PENDING_REVIEW", "PENDING_QLC", "PENDING_BP", "APPROVED", "ISSUED"]
        for index, workflow_status in enumerate(statuses, 1):
            vessel = vessels[(index - 1) % len(vessels)]
            movement = "DEPARTURE" if index % 2 == 0 else "ARRIVAL"
            db.add(Declaration(
                reference_no=f"KB-DEMO-202607-{index:03d}", status=workflow_status,
                workflow_status=workflow_status, organization_id=demo.id, vessel_id=vessel.id,
                declaration_date="2026-07-11", company_name=demo.name, vessel_name=vessel.name,
                registration_no=vessel.registration_no, vessel_type=vessel.vessel_type,
                vessel_class=vessel.vessel_class, deadweight_tons=vessel.deadweight_tons,
                certificate_expiry_date=vessel.certificate_expiry_date, crew_count=vessel.min_crew or 0,
                passenger_count=0, last_port="Cảng Cát Lái", working_port="Cảng Tân Thuận",
                destination_port="Cảng Hiệp Phước" if movement == "DEPARTURE" else "",
                eta=f"2026-07-{11 + index:02d}T08:00", etd=f"2026-07-{11 + index:02d}T18:00",
                unload_json=cargo("Hàng tổng hợp", 80 * index, index if index % 2 else 0),
                load_json=cargo("Thép cuộn", 65 * index, 0), master_name="Nguyễn Văn Hải",
                master_phone="0900 111 168", movement_type=movement,
                cv_approval="APPROVED" if workflow_status in {"PENDING_QLC", "PENDING_BP", "APPROVED", "ISSUED"} else "PENDING",
                qlc_approval="APPROVED" if workflow_status in {"PENDING_BP", "APPROVED", "ISSUED"} else "PENDING",
                bp_approval="APPROVED" if workflow_status in {"APPROVED", "ISSUED"} else "PENDING",
                permit_no=f"GP-DEMO-{index:03d}" if workflow_status == "ISSUED" else "",
                issued_at=now if workflow_status == "ISSUED" else None,
                created_at=now, updated_at=now,
            ))
        db.commit()
        print("Seeded 4 vessels, 4 crew members and 6 demonstration declarations.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
