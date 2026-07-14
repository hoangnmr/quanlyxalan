# Session Handoff: Recovery UX branch — 2026-07-13

- **Branch**: `recovery/frontend-baseline-20260712`
- **Status**: Recovery Wizard UX remains CLOSED; Data, Reporting & Sidebar is REOPENED pending import retest.
- **Date**: 2026-07-14
- **Gate 5 Status**: Wizard UX PASS; follow-up data/reporting tranche NOT CLOSED.
- **Active Code Commits**: `0b2ba72`, `5e74643`, `7c5431d`, `a2b1ca0`, `82b81f9` và `1a2ae22`

## Kết quả UAT mới nhất (2026-07-14)
- **Wizard CUSTOMER (1-6):** Đã kiểm thử và lưu screenshot đầy đủ tại `docs/evidence/recovery-ux-20260714/`.
- **Data, Reporting and Sidebar:** Sidebar, analytics, responsive và API Prep có bằng chứng PASS. Independent review phát hiện ảnh Smart Excel Import thực tế chỉ đạt 38/39, làm lộ lỗi SQL nội bộ; kết luận CLOSED của commit `8eb3c92` bị thu hồi.
- **Báo cáo chi tiết:** [docs/BROWSER_EVIDENCE_DATA_REPORTING_SIDEBAR_20260714.md](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/BROWSER_EVIDENCE_DATA_REPORTING_SIDEBAR_20260714.md)

## Corrective action after evidence review

- Mapping nâng lên `KBCV-IMPORT-1.2`.
- Ô số chứa nhiều cấu hình, ví dụ `2723.79 / 2912.57`, dùng giá trị đầu tiên làm giá trị chính và lưu nguyên ô nguồn trong `notes`.
- Preview đánh dấu `mappingWarnings` thay vì âm thầm chuyển đổi.
- UI không còn hiển thị exception/SQL/parameters; chi tiết chỉ ghi server log.
- Asset cache tag nâng lên `?v=1.1.1`.
- Parser check trên file untracked: 39 dòng, 0 thiếu trường bắt buộc, 0 giá trị còn sai kiểu số; dòng 15 có hai cảnh báo chuẩn hóa có truy vết.
- Automated tests phải được chạy lại trước commit. Browser retest bắt buộc dùng DB sạch: import lần đầu phải `39/0`; lần hai phải `idempotent = true` và tổng số phương tiện không tăng.

Không merge/push và không stage `templates/DU_LIEU_SA_LAN_39_CHIEC.xlsx`.

- **Retest corrective commit 1a2ae22:** UI xác nhận import 39 bản ghi và không còn lộ SQL. Independent review phát hiện ảnh idempotency giống hệt ảnh import lần đầu; preview chưa hiển thị dòng 15; chưa có artifact trực tiếp cho TN-0963/notes. Tranche vẫn REOPENED, chỉ cần bổ sung targeted evidence thay vì chạy lại toàn bộ ma trận.
- UX follow-up: re-import now renders a distinct “File đã được nhập trước đó — Không tạo thêm bản ghi” state with the original result and import job id; asset tag is `?v=1.1.2`. Browser evidence must target this new state.
