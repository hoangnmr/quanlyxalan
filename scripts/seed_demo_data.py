#!/usr/bin/env python
"""Seed the local UI with clearly marked, disposable demonstration data.

The seed refuses to run when normal operational records exist. The application
removes this sentinel-marked dataset automatically on the first real vessel
create or vessel import.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal, now_iso
from backend.auth import get_password_hash
from backend.models import CrewMember, Declaration, DeclarationEvent, Organization, User, Vessel

DEMO_ORGANIZATION_TAX_CODE = "DEMO-TANTHUAN-2026"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")


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

        db.add_all([
            User(
                username="khachhang",
                password_hash=get_password_hash(DEMO_PASSWORD),
                full_name="Khách hàng minh họa",
                role="CUSTOMER",
                organization_id=demo.id,
                is_active=1,
                created_at=now,
            ),
            User(
                username="nhanviencang",
                password_hash=get_password_hash(DEMO_PASSWORD),
                full_name="Nhân viên Cảng minh họa",
                role="PORT_STAFF",
                organization_id=None,
                is_active=1,
                created_at=now,
            ),
        ])

        vessels = [
            Vessel(organization_id=demo.id, name="Sà lan SG-168", registration_no="SG-DEMO-168", vessel_type="Sà lan", vessel_class="VR-SII", deadweight_tons=850, cargo_capacity_tons=780, min_crew=4, safety_certificate_no="ATKT-DEMO-168", certificate_expiry_date="2026-08-05", created_at=now, updated_at=now),
            Vessel(organization_id=demo.id, name="Tàu container Tân Thuận 01", registration_no="SG-DEMO-001", vessel_type="Tàu container", vessel_class="VR-SI", deadweight_tons=1200, container_capacity_teu=96, min_crew=6, safety_certificate_no="ATKT-DEMO-001", certificate_expiry_date="2026-12-31", created_at=now, updated_at=now),
            Vessel(organization_id=demo.id, name="Tàu hàng Nam Sài Gòn", registration_no="SG-DEMO-215", vessel_type="Tàu hàng khô", vessel_class="VR-SII", deadweight_tons=640, cargo_capacity_tons=610, min_crew=5, safety_certificate_no="ATKT-DEMO-215", certificate_expiry_date="2026-07-20", created_at=now, updated_at=now),
            Vessel(organization_id=demo.id, name="Tàu kéo Bạch Đằng", registration_no="SG-DEMO-088", vessel_type="Tàu kéo/đẩy", vessel_class="VR-SIII", deadweight_tons=210, min_crew=3, safety_certificate_no="ATKT-DEMO-088", certificate_expiry_date="2027-03-15", created_at=now, updated_at=now),
        ]
        db.add_all(vessels)
        db.flush()

        captain_names = ["Nguyễn Văn Hải", "Trần Minh Quân", "Lê Quốc Bảo", "Phạm Đức Long"]
        captain_phones = ["0900 111 168", "0900 222 001", "0900 333 215", "0900 444 088"]
        crew_members = []
        for index, vessel in enumerate(vessels):
            crew_members.extend([
                CrewMember(organization_id=demo.id, vessel_id=vessel.id, full_name=captain_names[index], crew_role="Thuyền trưởng", phone=captain_phones[index], professional_certificate_type="Thuyền trưởng hạng II", professional_certificate_no=f"TT-DEMO-{index + 1:03d}", certificate_expiry_date="2027-02-10", created_at=now, updated_at=now),
                CrewMember(organization_id=demo.id, vessel_id=vessel.id, full_name=f"Thuyền viên mẫu {index + 1}", crew_role="Thủy thủ", phone=f"0900 555 00{index + 1}", professional_certificate_type="Chứng chỉ nghiệp vụ", professional_certificate_no=f"TV-DEMO-{index + 1:03d}", certificate_expiry_date="2027-06-30", created_at=now, updated_at=now),
            ])
        db.add_all(crew_members)

        statuses = ["DRAFT", "PENDING_REVIEW", "CHANGES_REQUESTED", "APPROVED", "PENDING_REVIEW", "APPROVED"]
        for index, workflow_status in enumerate(statuses, 1):
            vessel = vessels[(index - 1) % len(vessels)]
            vessel_index = (index - 1) % len(vessels)
            movement = "DEPARTURE" if index % 2 == 0 else "ARRIVAL"
            declaration = Declaration(
                reference_no=f"KB-DEMO-202607-{index:03d}",
                status="DRAFT" if workflow_status == "DRAFT" else "SUBMITTED",
                workflow_status=workflow_status, organization_id=demo.id, vessel_id=vessel.id,
                declaration_date="2026-07-11", company_name=demo.name, vessel_name=vessel.name,
                registration_no=vessel.registration_no, vessel_type=vessel.vessel_type,
                vessel_class=vessel.vessel_class, deadweight_tons=vessel.deadweight_tons,
                certificate_expiry_date=vessel.certificate_expiry_date, crew_count=vessel.min_crew or 0,
                passenger_count=0, last_port="Cảng Cát Lái", working_port="Cảng Tân Thuận",
                destination_port="Cảng Hiệp Phước" if movement == "DEPARTURE" else "",
                eta=f"2026-07-{11 + index:02d}T08:00", etd=f"2026-07-{11 + index:02d}T18:00",
                unload_json=cargo("Hàng tổng hợp", 80 * index, index if index % 2 else 0),
                load_json=cargo("Thép cuộn", 65 * index, 0), master_name=captain_names[vessel_index],
                master_phone=captain_phones[vessel_index], movement_type=movement,
                port_approval="APPROVED" if workflow_status == "APPROVED" else "PENDING",
                submitted_at=now if workflow_status != "DRAFT" else None,
                created_at=now, updated_at=now,
            )
            db.add(declaration)
            db.flush()
            if workflow_status != "DRAFT":
                db.add(DeclarationEvent(
                    declaration_id=declaration.id,
                    action="SUBMIT",
                    from_status="DRAFT",
                    to_status="PENDING_REVIEW",
                    actor_name="Khách hàng minh họa",
                    actor_role="CUSTOMER",
                    note="Khách hàng xác nhận gửi phiếu minh họa.",
                    created_at=now,
                ))
            if workflow_status == "CHANGES_REQUESTED":
                db.add(DeclarationEvent(
                    declaration_id=declaration.id,
                    action="REQUEST_CHANGES",
                    from_status="PENDING_REVIEW",
                    to_status="CHANGES_REQUESTED",
                    actor_name="Nhân viên Cảng minh họa",
                    actor_role="PORT_STAFF",
                    note="Vui lòng bổ sung bản chụp chứng chỉ an toàn.",
                    created_at=now,
                ))
            elif workflow_status == "APPROVED":
                db.add(DeclarationEvent(
                    declaration_id=declaration.id,
                    action="PORT_APPROVE",
                    from_status="PENDING_REVIEW",
                    to_status="APPROVED",
                    actor_name="Nhân viên Cảng minh họa",
                    actor_role="PORT_STAFF",
                    note="Thông tin và chứng từ phù hợp.",
                    created_at=now,
                ))
        db.commit()
        print("Seeded demo accounts, 4 vessels, 8 crew members and 6 declarations.")
        print(f"Customer: khachhang / {DEMO_PASSWORD}")
        print(f"Port employee: nhanviencang / {DEMO_PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
