# Session Handoff — Recovery UX — 2026-07-13

## Mục đích

Tài liệu này là điểm vào cho agent tiếp theo. Đọc tài liệu này trước, sau đó
đọc `RECOVERY_UX_CHECKPOINT_20260713.md` và
`UX_REEVALUATION_RECOVERY_BRANCH_20260713.md`. Không suy luận trạng thái từ
worktree `main` hoặc bản restore.

## Bối cảnh vận hành bắt buộc

- Project root:
  `D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux`
- Branch: `recovery/frontend-baseline-20260712`
- Baseline khôi phục: `929a8c487c572b7bcad859e237b17da1d494a1db`
- Commit workflow/UX nền: `0b2ba72`
- Commit sửa lỗi runtime mới nhất: `5e74643`
- Phase: BUILD/REVIEW
- Risk: R2 vì có workflow, RBAC và migration dữ liệu.
- Live governance evidence required: YES đối với mọi tuyên bố về CVF governance.
  Mock chỉ dùng cho kiểm tra UI thuần túy theo `AGENTS.md`.
- Worktree `main` và `Khai-bao-Cang-vu-restore-20260712-1917` là nguồn đối
  chiếu, không được sửa từ tranche này.

## Quy trình nghiệp vụ đã chốt

```text
Khách hàng/chủ phương tiện khai báo
  -> Xác nhận & gửi
  -> Nhân viên doanh nghiệp Cảng xem xét
  -> PORT_APPROVE hoặc REQUEST_CHANGES
  -> Phản hồi về khách hàng
```

Cảng Tân Thuận là doanh nghiệp Cảng, không phải Cảng vụ/cơ quan chính quyền.
Không khôi phục quy trình CV → QLC → BP hoặc nghiệp vụ cấp phép/phát hành.

## Những gì đã hoàn thành

Commit `0b2ba72` bao gồm:

- Role runtime còn `CUSTOMER`, `PORT_STAFF`, `ADMIN`.
- Workflow runtime chỉ còn `PORT_APPROVE` và `REQUEST_CHANGES`.
- Action `CV_APPROVE`, `QLC_APPROVE`, `BP_APPROVE`, `ISSUE`, `REVOKE` trả
  HTTP 410 và không thay đổi hồ sơ.
- Migration `g06f0f000006` chuyển role/status cũ, đổi `cv_approval` thành
  `port_approval`, bỏ các cột legacy.
- Phiếu demo id 8 từng kẹt đã được chuyển sang `APPROVED` sau khi xác minh
  action cũ trả 410.
- Wizard sáu bước theo thứ tự phương tiện, hành trình, hàng hóa, thuyền viên,
  đính kèm, xem lại/gửi.
- Hồ sơ phương tiện có sẵn được điền tự động và khóa; Admin cập nhật hồ sơ gốc.
- Checkbox checklist thay native multi-select thuyền viên.
- Error summary, `aria-invalid`, thông báo theo field và focus-to-error.
- Thuật ngữ khách hàng dùng “Xác nhận & gửi”; “Crew List” đã Việt hóa.
- Báo cáo Claude được giữ nguyên ở phần dưới để truy vết, có bảng đính chính
  và trạng thái hiện hành ở đầu file.

Commit `5e74643` bổ sung:

- Không gọi endpoint Analytics chưa tồn tại khi mở trang Báo cáo; hiển thị
  trạng thái chưa khả dụng thay vì toast 404 hoặc số liệu giả.
- Chỉ Admin nhìn thấy và tải khu vực kết nối dữ liệu bên ngoài, loại bỏ toast
  403 đối với CUSTOMER/PORT_STAFF.
- Chỉ CUSTOMER nhìn thấy điểm vào tạo phiếu; Admin không còn đi vào luồng xác
  nhận gửi vốn bị backend từ chối.
- Đổi nhãn “Báo cáo Cảng vụ” thành “Báo cáo hoạt động Cảng” và bỏ mô tả phê
  duyệt nhiều cấp còn sót.

## Bằng chứng kỹ thuật hiện có

- `python -m pytest -q`: `67 passed`.
- `node --check frontend/app.js`: PASS.
- `git diff --check`: PASS.
- Alembic upgrade/downgrade trên database demo hiện hữu: PASS.
- Alembic upgrade từ database trắng + seed demo: PASS.
- Schema hiện hành có `port_approval`, không có `cv_approval`,
  `qlc_approval`, `bp_approval`, `permit_no`, `issued_at`, `revoked_at`.
- API thực trên port 8086 đã xác nhận:
  - `/api/auth/me` trả role `PORT_STAFF` cho `nhanviencang`.
  - Action cũ trả HTTP 410.
  - `PORT_APPROVE` đưa phiếu hợp lệ sang `APPROVED`.
  - `page=1&page_size=1` trả một item và metadata tổng.
- CVF Workspace Doctor ở đầu tranche: PASS 17/17.

Không có bằng chứng browser trực quan trong session này. Không được chuyển các
mục “chờ browser/UAT” thành PASS chỉ dựa trên mã nguồn hoặc test tĩnh.

Ngày 2026-07-14 đã thử kết nối in-app browser theo browser skill nhưng danh
sách browser khả dụng rỗng. Không dùng công cụ browser khác để thay thế và
không tạo tuyên bố screenshot/viewport.

## Cách chạy đúng worktree

Worktree recovery chưa có `.venv` riêng. Interpreter đã dùng để xác minh là:

```powershell
$python = 'D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu\.venv\Scripts\python.exe'
$env:SECRET_KEY = '<secret ngẫu nhiên cục bộ, không commit>'
& $python -m alembic upgrade head
& $python -m uvicorn backend.app:app --host 127.0.0.1 --port 8086 --reload
```

Terminal phải đứng tại project root recovery nêu trên. Có thể tạo `.venv` riêng
cho worktree thay vì dùng interpreter dùng chung; không commit `.env` hoặc secret.

Tài khoản demo do `scripts/seed_demo_data.py` tạo:

- `khachhang / demo123`
- `nhanviencang / demo123`

Không giả định mật khẩu Admin. Nếu cần Admin trên database mới, dùng bootstrap
được tài liệu hóa và secret môi trường; không hard-code credential.

## Việc chưa hoàn thành và điều kiện chờ

### 1. Browser/UAT và Gate 5

Chưa có ảnh hoặc thao tác thật tại 1920×1080, 1366×768, 390×844. Chưa có
keyboard/screen-reader/axe test và task study theo role. Cần Claude hoặc agent
có browser chạy đúng branch, ghi URL, viewport, role, thao tác, kết quả và ảnh.

### 2. Analytics

`GET /api/reports/analytics` chưa tồn tại. Đây là tranche riêng. Trước khi code
cần Product Owner chốt chỉ số, kỳ so sánh, nguồn dữ liệu, quyền truy cập, API
contract và acceptance criteria. Không đánh dấu PASS vì frontend có fallback.

### 3. Dashboard information architecture

Attention queue đã theo role nhưng thứ tự/nhóm widget chưa được chứng minh bằng
task study. Chờ UAT trước khi tái cấu trúc để tránh sửa theo cảm tính.

### 4. Tìm kiếm không dấu

Search theo tên phương tiện hoạt động và thuyền trưởng có filter riêng. Chỉ còn
khả năng `Hai` không khớp `Hải`. Chờ xác nhận yêu cầu sản phẩm trước khi thêm
accent-insensitive search.

### 5. Production/staging

Migration mới chỉ được thử trên database local/demo và database trắng. Cần bản
sao staging, owner triển khai, backup/rollback và smoke test trước production.

## File ngoài phạm vi cần giữ nguyên

Tại thời điểm handoff có file Excel untracked trong `templates/`:

- `templates/DU_LIEU_SA_LAN_39_CHIEC.xlsx`
- Có thể xuất hiện file khóa Excel `templates/~$DU_LIEU_SA_LAN_39_CHIEC.xlsx`

Đây không phải artifact của tranche. Không add, xóa, đổi tên hoặc commit nếu
chưa có chỉ đạo rõ của người dùng.

## Trình tự tiếp quản đề nghị

1. Chạy First-Request Protocol trong `AGENTS.md` và Workspace Doctor.
2. Xác nhận cwd, branch, `git status`, commit `5e74643` có trong lịch sử.
3. Đọc bảng trạng thái trong báo cáo UX; không dùng kết luận lỗi UX-101/102 cũ.
4. Chạy migration và `pytest` trước kiểm thử browser.
5. Thu thập browser evidence cho các mục đang chờ; không sửa analytics trong
   cùng tranche.
6. Nếu có sửa code, ghi bằng chứng vào checkpoint/handoff và commit trên branch
   recovery; không merge/push nếu chưa được người dùng yêu cầu.

## Tiêu chí dừng an toàn

- Dừng nếu cwd không phải recovery worktree hoặc branch không đúng.
- Dừng nếu migration/test thất bại; không tuyên bố checkpoint hoàn tất.
- Dừng nếu cần thay đổi workflow/RBAC ngoài quy trình đã chốt; yêu cầu human
  review vì R2.
- Không đóng Gate 5 nếu thiếu browser/UAT evidence.
