import tempfile
import unittest
from pathlib import Path
import sys
import zipfile
from io import BytesIO


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import database
from app import save_declaration, save_vessel
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


if __name__ == "__main__":
    unittest.main()

