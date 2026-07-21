"""Khôi phục vessel_type về đúng nguyên văn chứng từ (Công dụng), hoàn tác
migrate_vessel_type_vocabulary.py.

Việc quy vessel_type về danh mục "Tàu hàng khô"/"Tàu container"… là sai: giấy
chứng nhận đăng ký và đăng kiểm chỉ ghi "Công dụng" (vd "Chở hàng khô hoặc
container"), không có khái niệm "Loại phương tiện" tách biệt trên bất kỳ
chứng từ nào. vessel_type phải giữ nguyên văn đó; "Tàu hàng khô"/"Tàu
container"… chuyển sang trường vessel_category (tùy chọn, không liên quan
chứng từ).

Script đọc giá trị vessel_type gốc từ một bản sao lưu SQLite lịch sử (bản chụp
trước migrate đầu tiên, có từ thời hệ thống còn chạy SQLite) và ghi đè lại theo
id vào CSDL PostgreSQL hiện hành, không đụng tới cột nào khác.

    python scripts/restore_vessel_type_from_backup.py
    python scripts/restore_vessel_type_from_backup.py --apply
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_BACKUP = ROOT / "data" / "backups" / "cang_vu-20260720-200758-pre-vessel-type-vocab.db"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Ghi thay đổi vào CSDL")
    parser.add_argument("--url", default=None,
                        help="PostgreSQL URL đích (mặc định: cấu hình ứng dụng)")
    parser.add_argument("--backup-source", default=str(DEFAULT_BACKUP),
                         help="Bản sao lưu SQLite chứa giá trị vessel_type gốc cần khôi phục")
    args = parser.parse_args()

    source_path = Path(args.backup_source)
    if not source_path.exists():
        print(f"Thiếu tệp: {source_path}")
        return 1

    if args.url:
        url = args.url
    else:
        from backend.database import SQLALCHEMY_DATABASE_URL

        url = os.environ.get("DATABASE_URL") or SQLALCHEMY_DATABASE_URL

    source = sqlite3.connect(source_path)
    original = {row[0]: row[1] for row in source.execute("SELECT id, vessel_type FROM vessels")}
    source.close()

    engine = create_engine(url)
    con = engine.connect()
    current = {row[0]: row[1] for row in con.execute(text("SELECT id, vessel_type FROM vessels"))}

    planned = [(vid, current[vid], original[vid]) for vid in current
               if vid in original and current[vid] != original[vid]]

    print(f"Tổng hồ sơ: {len(current)}")
    print(f"Sẽ khôi phục: {len(planned)}")
    summary: dict[tuple[str, str], int] = {}
    for _, old, new in planned:
        summary[(old, new)] = summary.get((old, new), 0) + 1
    for (old, new), count in sorted(summary.items(), key=lambda item: -item[1]):
        print(f"  {count:>3}  {old!r} -> {new!r}")

    missing = [vid for vid in current if vid not in original]
    if missing:
        print(f"\nKhông có trong bản sao lưu nguồn (bỏ qua, giữ nguyên): {missing}")

    if not args.apply:
        print("\n(chế độ thử — thêm --apply để ghi thật)")
        con.close()
        return 0

    if not planned:
        print("\nKhông có gì để ghi.")
        con.close()
        return 0

    from backup_local import backup as create_backup

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = ROOT / "data" / "backups" / f"cang_vu-{stamp}-pre-vessel-type-restore.dump"
    create_backup(url, backup)
    print(f"\nĐã sao lưu: {backup}")

    with con.begin():
        con.execute(
            text("UPDATE vessels SET vessel_type = :vessel_type, updated_at = :ts WHERE id = :id"),
            [{"vessel_type": new, "ts": datetime.now().isoformat(timespec="seconds"), "id": vid}
             for vid, _, new in planned],
        )
    print(f"Đã khôi phục {len(planned)} hồ sơ.")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
