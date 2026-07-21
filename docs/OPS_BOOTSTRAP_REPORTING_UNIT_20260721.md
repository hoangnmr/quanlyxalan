# Ops Record — Bootstrap đơn vị báo cáo đầu tiên (2026-07-21)

## Triệu chứng

Sau khi đăng nhập bằng `admin` (PLATFORM_ADMIN), mọi màn hình nghiệp vụ đều trống
và console trả về một loạt lỗi `400 Bad Request`:

```
GET /api/dashboard                          400
GET /api/declarations?...&direction=desc    400
GET /api/crew                               400
GET /api/integrations/...maritime-authority 400
GET /api/reports/an...month&source=live     400
```

Toast hiển thị: `Thiếu ngữ cảnh đơn vị báo cáo (X-Reporting-Unit-ID).`
Sidebar hiển thị `Chưa chọn` và màn hình chính báo
"Tài khoản chưa có đơn vị báo cáo hoạt động."

## Nguyên nhân gốc

Không phải lỗi code. Bảng `reporting_units` **trống** — cơ sở dữ liệu `cangvu`
chưa từng được seed sau khi chạy migration.

Chuỗi nhân quả:

1. Không có đơn vị báo cáo nào → dropdown chọn cảng rỗng.
2. Frontend không có gì để chọn → không gắn header `X-Reporting-Unit-ID`.
3. `resolve_scope()` (`backend/tenant.py`) fail-closed với `400` cho mọi route
   dùng guard tenant, vì `admin` mang role PORT (`PLATFORM_ADMIN`) và role này
   **bắt buộc** phải cung cấp ngữ cảnh đơn vị tường minh.

Đây là hành vi đúng theo thiết kế R4 — xem
[CLAUDE_H2_CORRECTION_ORDER_R4_TENANT_CONTEXT_20260718.md](CLAUDE_H2_CORRECTION_ORDER_R4_TENANT_CONTEXT_20260718.md).
Hệ thống không có đơn vị mặc định ngầm định; đó là chủ ý để tránh rò rỉ dữ liệu
giữa các tenant.

## Xử lý

Tạo đơn vị báo cáo đầu tiên trực tiếp trong PostgreSQL:

```sql
INSERT INTO reporting_units
  (name, code, official_header_json, is_active, created_at, updated_at)
VALUES
  ('Cảng Tân Thuận', 'TANTHUAN', '{}', 1, now()::text, now()::text);
```

Kết quả: `id=1 — Cảng Tân Thuận (TANTHUAN)`, `is_active=1`.

### Sai sót trong quy trình xử lý — đã khắc phục

Câu `INSERT` thủ công trên **đáng lẽ không nên dùng**. Dự án đã có
`scripts/bootstrap_reporting_unit.py` làm đúng việc này an toàn hơn: chạy trong
transaction, mặc định dry-run (`--apply` mới ghi), kiểm tra Alembic revision, và
ghi `audit_events` action `LEGACY_BOOTSTRAP`.

Hệ quả: đơn vị `id=1` ban đầu tồn tại **không có bản ghi kiểm toán**. Đã bù lại
thủ công một dòng `audit_events` (`id=7`) theo đúng định dạng script sinh ra.

### Vì sao script không được dùng: script đã lạc hậu

`scripts/bootstrap_reporting_unit.py:20` chốt cứng:

```python
EXPECTED_REVISION = "n13f0f000013"
```

DB hiện ở revision **`q16f0f000016`**. Script sẽ dừng ngay với
`RuntimeError: Expected Alembic n13f0f000013, found 'q16f0f000016'`.

Ngoài ra script được thiết kế cho **migration hệ thống single-port cũ**, không
phải DB rỗng: nó bắt buộc `--staff-username` (phải là `PORT_STAFF` đang hoạt
động) và ít nhất một Organization. Trên DB rỗng không có cả hai, nên script
không thể chạy kể cả khi revision khớp.

**Việc cần làm (chưa thực hiện):** quyết định giữa (a) cập nhật
`EXPECTED_REVISION` và nới yêu cầu staff/organization để script dùng được cho
DB mới, hay (b) tuyên bố script chỉ dành cho legacy và viết đường seed riêng cho
cài đặt mới. Không tự ý sửa vì đây là mã có ràng buộc governance.

Sau đó người dùng tải lại trang và chọn đơn vị trong dropdown sidebar; frontend
bắt đầu gửi `X-Reporting-Unit-ID: 1` và các lỗi 400 chấm dứt.

## Trạng thái còn lại sau xử lý

| Bảng | Số dòng | Ảnh hưởng |
|---|---|---|
| `reporting_units` | 1 | đã xử lý |
| `users` | 1 (`admin`, PLATFORM_ADMIN) | đủ để vận hành |
| `reporting_unit_users` | 0 | chưa cần — PLATFORM_ADMIN không yêu cầu membership |
| `reporting_unit_organizations` | 0 | **danh sách khách hàng/khai báo vẫn rỗng** |

`reporting_unit_organizations` trống nghĩa là `Scope.member_org_ids` rỗng, nên
mọi truy vấn dữ liệu khách hàng trả về tập rỗng một cách hợp lệ (không phải lỗi).
Cần gán tổ chức vào đơn vị trước khi có dữ liệu hiển thị.

## Ghi chú vận hành cho lần triển khai sau

- Một DB vừa migrate là **chưa dùng được**; phải seed ít nhất một
  `reporting_unit` trước khi bất kỳ tài khoản PORT nào đăng nhập.
- Tài khoản `PORT_STAFF` (khác PLATFORM_ADMIN) còn phải có dòng trong
  `reporting_unit_users`, nếu không sẽ nhận `403 Bạn không có quyền tại đơn vị
  báo cáo này.`
- Lỗi `401` trên `/api/auth/me` lúc mới tải trang là bình thường (gọi trước khi
  token được gắn). Lỗi `404 /favicon.ico` vô hại.

## Liên quan

- `backend/tenant.py` — guard `resolve_scope()` / `require_port_scope()`
- [USER_BOOTSTRAP.md](USER_BOOTSTRAP.md) — quy trình tạo tài khoản
- [CLAUDE_H2_FINALIZATION_PLATFORM_ADMIN_AND_DB_RECONCILIATION_20260718.md](CLAUDE_H2_FINALIZATION_PLATFORM_ADMIN_AND_DB_RECONCILIATION_20260718.md)
