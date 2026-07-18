"""Export a read-only operational appendix review set from the local database."""
from __future__ import annotations

import json
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import (
    _appendix1_rows,
    _appendix2_rows,
    _appendix3_rows,
    _approved_report_query,
    _arrival_operating_date,
    _declaration_operating_date,
    _report_adjustment_totals,
    _report_base_vessels,
)
from backend.database import SessionLocal
from backend.models import User
from backend.xlsx_io import make_report_xlsx


OUTPUT_DIR = ROOT / "outputs" / "appendix-operational-review-20260717"


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role.in_(["PORT_STAFF", "PLATFORM_ADMIN"])).order_by(User.id).first()
        if not user:
            raise RuntimeError("Không có PORT_STAFF/PLATFORM_ADMIN để áp dụng đúng phạm vi báo cáo Cảng.")
        anchor = date.today()
        period_start = date(anchor.year, 1, 1)
        month_start = date(anchor.year, anchor.month, 1)
        month_end = date(anchor.year, anchor.month, monthrange(anchor.year, anchor.month)[1])
        approved = _approved_report_query(db, user).all()
        period_declarations = [
            item for item in approved
            if (operating_date := _declaration_operating_date(item)) and period_start <= operating_date <= anchor
        ]
        current_month = [
            item for item in approved
            if (operating_date := _arrival_operating_date(item)) and month_start <= operating_date <= month_end
        ]
        cumulative = [
            item for item in approved
            if (operating_date := _arrival_operating_date(item)) and period_start <= operating_date <= month_end
        ]
        vessels = _report_base_vessels(db, user)
        month_key = anchor.strftime("%Y-%m")
        metadata = {
            "report_from": period_start,
            "report_to": anchor,
            "reporting_unit": "CÔNG TY CỔ PHẦN CẢNG TÂN THUẬN",
        }
        appendix1_rows = _appendix1_rows(db, period_declarations, vessels)
        appendix2_rows = _appendix2_rows(
            current_month,
            cumulative,
            _report_adjustment_totals(db, month_key, month_key, None),
            _report_adjustment_totals(db, f"{anchor.year}-01", month_key, None),
        )
        appendix3_rows = _appendix3_rows(db, period_declarations, vessels)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "PL.01_operational_review.xlsx").write_bytes(
            make_report_xlsx("appendix1", appendix1_rows, **metadata)
        )
        (OUTPUT_DIR / "PL.02_operational_review.xlsx").write_bytes(make_report_xlsx(
            "appendix2",
            appendix2_rows,
            report_from=month_start,
            report_to=month_end,
            reporting_unit=metadata["reporting_unit"],
        ))
        (OUTPUT_DIR / "PL.03_operational_review.xlsx").write_bytes(make_report_xlsx(
            "appendix3",
            appendix3_rows,
            appendix3_template=ROOT / "templates" / "Phụ lục 3.xlsx",
            **metadata,
        ))
        (OUTPUT_DIR / "manifest.json").write_text(json.dumps({
            "generated_on": anchor.isoformat(),
            "canonical_salan_rows": len(vessels),
            "approved_declarations_in_period": len(period_declarations),
            "approved_arrivals_in_month": len(current_month),
            "expected": {
                "appendix1_rows": len(appendix1_rows),
                "appendix2_activity": "blank when no approved activity",
                "appendix3_rows": len(appendix3_rows),
            },
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(OUTPUT_DIR)
    finally:
        db.close()


if __name__ == "__main__":
    main()
