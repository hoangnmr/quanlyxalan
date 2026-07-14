# Session Handoff — Recovery UX — 2026-07-14

## Trạng thái

- Worktree: `D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux`
- Branch: `recovery/frontend-baseline-20260712`
- Phase: REVIEW completed for Recovery UX; integration remains a human decision.
- Risk: R2 because workflow/RBAC/migration behavior is present in the branch.
- Gate 5 Recovery UX: **CLOSED (PASS)**.
- Application code under test: `a2b1ca0`.
- Full-flow evidence commit: `3574128`.
- Live governance evidence remains mandatory for any CVF-governance claim;
  browser screenshots here prove product UX behavior only.

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

## Chuỗi triển khai và bằng chứng

- `0b2ba72`: workflow/RBAC/migration và wizard sáu bước nền.
- `5e74643`: tránh Analytics 404, integration 403 và entry-point sai role.
- `7c5431d`: sửa crash wizard, CSS hidden và sidebar mobile scroll.
- `a2b1ca0`: frontend follow-up, role display, asset cache-busting và icon mobile.
- `82b81f9`: đối soát phạm vi evidence, yêu cầu full six-step UAT.
- `3574128`: ảnh Bước 1–6, validation, checklist, review/send và submit thành công.

Bằng chứng nằm tại `docs/evidence/recovery-ux-20260714/` và được diễn giải tại
`docs/BROWSER_EVIDENCE_RECOVERY_UX_20260714.md`.

## Kết quả xác minh

- `python -m pytest -q`: `67 passed`.
- `node --check frontend/app.js`: PASS.
- `git diff --check`: PASS.
- CUSTOMER đi đủ Bước 1→6 và submit thành công sang `PENDING_REVIEW`.
- Validation/focus recovery, checklist thuyền viên và review summary: PASS.
- Console không có uncaught JavaScript error trong full-flow UAT.
- Network không có HTTP 4xx/5xx ngoài validation có chủ ý.
- Integration visibility theo role và sidebar mobile: PASS.

## Cách chạy đúng worktree

```powershell
$python = 'D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu\.venv\Scripts\python.exe'
$env:SECRET_KEY = '<secret ngẫu nhiên cục bộ, không commit>'
& $python -m alembic upgrade head
& $python -m uvicorn backend.app:app --host 127.0.0.1 --port 8086 --reload
```

Tài khoản demo từ seed: `khachhang / demo123` và
`nhanviencang / demo123`. Không giả định mật khẩu Admin trên database khác;
không hard-code hoặc commit secret.

## Ngoài phạm vi Gate 5 đã đóng

- Analytics API/metrics: cần work order riêng với contract, RBAC và acceptance criteria.
- Dashboard information architecture: chờ task study nếu Product Owner muốn tái cấu trúc.
- Tìm kiếm không dấu: chờ quyết định sản phẩm.
- Validation locale: error summary đã là tiếng Việt nhưng một số thông báo
  native của trình duyệt còn tiếng Anh; đây là polish follow-up, không chặn Gate 5.
- Production/staging: cần backup, migration rehearsal, rollback và owner triển khai.
- Merge/push/release: chưa được tự động cho phép bởi việc đóng UX Gate 5.

## File ngoài phạm vi phải giữ nguyên

- `templates/DU_LIEU_SA_LAN_39_CHIEC.xlsx` đang untracked.
- Không add, xóa, đổi tên hoặc commit nếu chưa có chỉ đạo rõ của người dùng.

## Tiếp quản

1. Chạy First-Request Protocol và Workspace Doctor.
2. Xác nhận đúng worktree/branch và đọc checkpoint, browser report, UX ledger.
3. Không lặp lại UAT đã đóng nếu application code không thay đổi.
4. Nếu code wizard, role display hoặc navigation thay đổi, mở lại regression
   tương ứng và cập nhật evidence trước khi giữ trạng thái PASS.
5. Không merge hoặc push nếu người dùng chưa yêu cầu.
