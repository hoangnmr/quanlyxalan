import tempfile
import unittest
from pathlib import Path
import sys
import zipfile
from io import BytesIO


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import database
from app import ApiError, certificate_status, save_crew_member, save_declaration, save_vessel, transition_declaration, validate_attachment_content
from xlsx_io import make_xlsx


class BackendTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.tempdir.name) / "test.db"
        database.init_db()

    def tearDown(self):
        self.tempdir.cleanup()

    def test_vessel_and_submitted_declaration(self):
        with database.connection() as db:
            vessel = save_vessel(db, {
                "organization": {"name": "Test Company"},
                "name": "TT TEST",
                "registration_no": "SG-TEST",
                "vessel_type": "Tàu container",
                "vessel_class": "VR-SI",
            })
            declaration = save_declaration(db, {
                "company_name": "Test Company",
                "declaration_date": "2026-07-11",
                "vessel_id": vessel["id"],
                "vessel_name": vessel["name"],
                "registration_no": vessel["registration_no"],
                "vessel_type": vessel["vessel_type"],
                "vessel_class": vessel["vessel_class"],
                "last_port": "Bến A",
                "working_port": "Cảng Tân Thuận",
                "eta": "2026-07-11T08:00",
                "etd": "2026-07-11T18:00",
                "master_name": "Nguyễn Văn A",
                "master_phone": "0900000000",
                "unload": {"cont20_full": 2, "cont20_empty": 1, "cont40_full": 3, "cont40_empty": 1},
                "load": {},
            }, submit=True)
        self.assertEqual(declaration["status"], "SUBMITTED")
        self.assertEqual(declaration["unload"]["total_containers"], 7)
        self.assertEqual(declaration["unload"]["teu"], 11)
        self.assertEqual(declaration["unload"]["empty_teu"], 3)

    def test_generated_report_is_an_xlsx_package(self):
        content = make_xlsx("TEST", ["A", "B"], [[1, "Hai"]])
        with zipfile.ZipFile(BytesIO(content)) as archive:
            self.assertIn("xl/workbook.xml", archive.namelist())
            self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())

    def test_crew_certificate_and_snapshot(self):
        with database.connection() as db:
            member = save_crew_member(db, {
                "full_name": "Nguyễn Văn Thuyền",
                "crew_role": "Thuyền trưởng",
                "professional_certificate_type": "Bằng thuyền trưởng",
                "professional_certificate_no": "CERT-001",
                "certificate_expiry_date": "2020-01-01",
            })
            declaration = save_declaration(db, {
                "company_name": "Test Company",
                "declaration_date": "2026-07-11",
                "vessel_name": "TT TEST",
                "registration_no": "SG-TEST-CREW",
                "vessel_type": "Tàu hàng khô",
                "vessel_class": "VR-SI",
                "last_port": "Bến A",
                "working_port": "Cảng Tân Thuận",
                "eta": "2026-07-11T08:00",
                "etd": "2026-07-11T18:00",
                "master_name": member["full_name"],
                "master_phone": "0900000000",
                "crew_ids": [member["id"]],
                "unload": {},
                "load": {},
            })
        self.assertEqual(member["certificate_status"], "EXPIRED")
        self.assertEqual(certificate_status("2099-01-01"), "VALID")
        self.assertEqual(declaration["crew"][0]["certificate_no_snapshot"], "CERT-001")

    def test_attachment_signature_check(self):
        validate_attachment_content(".pdf", b"%PDF-1.4 valid")
        with self.assertRaises(ApiError):
            validate_attachment_content(".pdf", b"not a pdf")

    def test_ordered_approval_and_permit_timeline(self):
        payload = {
            "company_name": "Test Company", "declaration_date": "2026-07-11",
            "vessel_name": "TT DEPARTURE", "registration_no": "SG-WORKFLOW",
            "vessel_type": "Tàu hàng khô", "vessel_class": "VR-SI",
            "movement_type": "DEPARTURE", "last_port": "Cảng Tân Thuận",
            "working_port": "Cảng Tân Thuận", "destination_port": "Bến B",
            "eta": "2026-07-11T08:00", "etd": "2026-07-11T18:00",
            "master_name": "Nguyễn Văn A", "master_phone": "0900000000",
            "unload": {}, "load": {},
        }
        with database.connection() as db:
            declaration = save_declaration(db, payload, submit=True)
            with self.assertRaises(ApiError):
                transition_declaration(db, declaration["id"], {"action": "BP_APPROVE", "actor_role": "BP", "actor_name": "Sai thứ tự"})
            transition_declaration(db, declaration["id"], {"action": "CV_APPROVE", "actor_role": "CV", "actor_name": "Cán bộ CV"})
            transition_declaration(db, declaration["id"], {"action": "QLC_APPROVE", "actor_role": "QLC", "actor_name": "Quản lý"})
            transition_declaration(db, declaration["id"], {"action": "BP_APPROVE", "actor_role": "BP", "actor_name": "Ban phép"})
            issued = transition_declaration(db, declaration["id"], {"action": "ISSUE", "actor_role": "BP", "actor_name": "Ban phép", "permit_no": "53/GP-TT"})
            events = db.execute("SELECT COUNT(*) FROM declaration_events WHERE declaration_id=?", (declaration["id"],)).fetchone()[0]
        self.assertEqual(issued["workflow_status"], "ISSUED")
        self.assertEqual(issued["permit_no"], "53/GP-TT")
        self.assertEqual(events, 5)


if __name__ == "__main__":
    unittest.main()
