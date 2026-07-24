# Quan-Ly-Xalan / Port Declaration System

Ứng dụng web quản lý khai báo phương tiện thủy, hồ sơ phương tiện, thuyền viên,
sổ theo dõi của Cảng và báo cáo PL.01–PL.03. Hệ thống hỗ trợ nhiều cảng/đơn vị
báo cáo trên cùng một nền tảng và tách biệt dữ liệu theo đơn vị đang chọn.

## Tài liệu

- [Hướng dẫn sử dụng](USER_GUIDE.md): thao tác theo từng vai trò, import dữ liệu,
  xử lý cảnh báo và xuất báo cáo.
- [Technical Catalog](CATALOG.md): sơ đồ module, API, dữ liệu, migration và vị trí
  cần sửa theo từng loại công việc.
- [API Contract](docs/API_CONTRACT.md): hợp đồng request/response chi tiết.
- [Architecture](docs/ARCHITECTURE.md): kiến trúc và ranh giới triển khai.

## Chức năng chính

- Khách hàng tạo, lưu nháp và gửi phiếu khai báo; nhân viên Cảng cũng tạo/lưu
  nháp được (kể cả qua import Excel) nhưng không tự gửi thay khách hàng; Cảng
  yêu cầu bổ sung hoặc duyệt.
- Quản lý hồ sơ phương tiện, sổ theo dõi Salan và danh sách thuyền viên.
- Import dữ liệu vận hành có preview và bước xác nhận.
- Import lịch sử từ workbook TOS Berth, chi tiết container và PL.03 cũ theo cấu
  trúc dữ liệu, không phụ thuộc tên file.
- Đối soát theo lượt tàu, lưu provenance/revision và xuất PL.03 tổng hợp với
  ATB/ATD, TEU, tấn ưu tiên từ dữ liệu TOS.
- Dashboard báo cáo theo nguồn LIVE, LỊCH SỬ hoặc KẾT HỢP; xuất Excel PL.01–PL.03.
- Phân quyền `CUSTOMER`, `PORT_STAFF`, `PLATFORM_ADMIN` với phạm vi đơn vị báo
  cáo được kiểm soát ở backend.

## Yêu cầu

- Python 3.12+
- PostgreSQL 14+ (đang kiểm chứng trên PostgreSQL 17)
- `pip`

## Cài đặt

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pip install -r backend/requirements-dev.txt
```

Tạo cơ sở dữ liệu:

```bash
createdb cangvu
```

## Cấu hình

Sao chép `.env.example` thành `.env`, rồi đặt `SECRET_KEY` và `DATABASE_URL`:

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"   # dán vào SECRET_KEY
```

`DATABASE_URL` mặc định là `postgresql+psycopg://localhost/cangvu`. Ứng dụng chỉ
chấp nhận URL PostgreSQL và sẽ báo lỗi khi khởi động nếu nhận URL khác.

## Chạy kiểm thử

```bash
SECRET_KEY=<khoa-bat-ky-cho-test> .venv/bin/python -m pytest -q
```

Bộ kiểm thử tự tạo và xoá một PostgreSQL database riêng cho từng module, dùng
`TEST_ADMIN_DATABASE_URL` (mặc định `postgresql+psycopg://localhost/postgres`)
làm kết nối quản trị.

Mọi kiểm thử phải pass trước khi merge hoặc triển khai.

## Chạy local

```bash
./scripts/run-dev.sh
```

Script sẽ áp Alembic migrations trước khi khởi động. Mở
`http://127.0.0.1:8080`.

Có thể chạy trực tiếp:

```bash
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8080 --reload
```

Sao lưu định kỳ hằng ngày (launchd trên macOS):

```bash
./scripts/register-local-backup-task.sh 02:00
```

Backup dùng `pg_dump` định dạng custom kèm manifest SHA-256, ghi vào
`data/backups/`. Thư mục `data/`, workbook nguồn và file backup không được đưa
vào Git.

## Ranh giới production

Production cần persistent storage, HTTPS/reverse proxy, secret từ biến môi
trường và quy trình backup/restore đã kiểm chứng. Xem
[Deployment](docs/DEPLOYMENT.md) và
[EA Evaluation Roadmap](docs/EA_EVALUATION_ROADMAP.md).
