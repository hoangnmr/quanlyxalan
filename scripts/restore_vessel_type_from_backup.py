"""Khôi phục vessel_type về đúng nguyên văn chứng từ (Công dụng), hoàn tác
migrate_vessel_type_vocabulary.py.

Việc quy vessel_type về danh mục "Tàu hàng khô"/"Tàu container"… là sai: giấy
chứng nhận đăng ký và đăng kiểm chỉ ghi "Công dụng" (vd "Chở hàng khô hoặc
container"), không có khái niệm "Loại phương tiện" tách biệt trên bất kỳ
chứng từ nào. vessel_type phải giữ nguyên văn đó; "Tàu hàng khô"/"Tàu
container"… chuyển sang trường vessel_category (tùy chọn, không liên quan
chứng từ).

Script đọc giá trị vessel_type gốc từ một bản sao lưu (mặc định là bản chụp
trước migrate đầu tiên) và ghi đè lại theo id, không đụng tới cột nào khác.

    python scripts/restore_vessel_type_from_backup.py
    python scripts/restore_vessel_type_from_backup.py --apply
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "cang_vu.db"
DEFAULT_BACKUP = ROOT / "data" / "backups" / "cang_vu-20260720-200758-pre-vessel-type-vocab.db"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Ghi thay đổi vào CSDL")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--backup-source", default=str(DEFAULT_BACKUP),
                         help="Bản sao lưu chứa giá trị vessel_type gốc cần khôi phục")
    args = parser.parse_args()

    db_path = Path(args.db)
    source_path = Path(args.backup_source)
    if not db_path.exists() or not source_path.exists():
        print(f"Thiếu tệp: {db_path if not db_path.exists() else source_path}")
        return 1

    source = sqlite3.connect(source_path)
    original = {row[0]: row[1] for row in source.execute("SELECT id, vessel_type FROM vessels")}
    source.close()

    con = sqlite3.connect(db_path)
    current = {row[0]: row[1] for row in con.execute("SELECT id, vessel_type FROM vessels")}

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

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = db_path.parent / "backups" / f"{db_path.stem}-{stamp}-pre-vessel-type-restore.db"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_path, backup)
    print(f"\nĐã sao lưu: {backup}")

    con.executemany(
        "UPDATE vessels SET vessel_type = ?, updated_at = ? WHERE id = ?",
        [(new, datetime.now().isoformat(timespec="seconds"), vid) for vid, _, new in planned],
    )
    con.commit()
    print(f"Đã khôi phục {len(planned)} hồ sơ.")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
