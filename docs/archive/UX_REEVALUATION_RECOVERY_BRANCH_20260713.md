# Đánh giá lại UX — Recovery Checkpoint

## Trạng thái kiểm soát — 2026-07-14

- Branch: `recovery/frontend-baseline-20260712`
- Application code under test: `a2b1ca0`
- Full-flow browser evidence: `3574128`
- Automated regression: `67 passed`; `node --check frontend/app.js` PASS.
- Gate 5: **CLOSED (PASS)** cho phạm vi Recovery UX.
- Analytics và production/staging readiness: ngoài phạm vi đóng Gate 5 này.

## Sổ trạng thái hiện hành

| Mã | Trạng thái | Kết luận hiện hành | Phạm vi còn lại |
|---|---|---|---|
| CRIT-001 | **PASS** | Runtime chỉ còn `PORT_APPROVE` và `REQUEST_CHANGES`; action CV/QLC/BP cũ trả HTTP 410; migration dùng `PORT_STAFF` và `port_approval`. | Rehearsal trên bản sao staging trước production. |
| UX-101 | **ĐÍNH CHÍNH — KHÔNG PHẢI LỖI NHƯ BÁO CÁO GỐC** | API tìm theo `vessel_name`; thuyền trưởng có filter `master_name`. UX-101 không phải finding typography. | Product Owner quyết định có cần tìm kiếm không dấu (`Hai` → `Hải`). |
| UX-102 | **PASS — ĐÃ CÓ SẴN** | Phân trang hoạt động khi gửi `page`; response mảng khi thiếu `page` là tương thích ngược có chủ ý. | Performance test với tập dữ liệu tham chiếu nếu mở tranche riêng. |
| UX-103 | **PASS** | UI/audit dùng “Xác nhận & gửi”, không dùng “Nộp/nộp” cho khách hàng. | Không còn việc trong Recovery UX. |
| UX-104 | **CHƯA ĐÓNG — NGOÀI GATE NÀY** | Dashboard đã ẩn chức năng theo role và có attention queue. | Task study để xác định thứ tự widget; không tái cấu trúc theo cảm tính. |
| UX-105 | **PASS** | Full-flow browser UAT xác nhận validation, error summary, focus recovery và wizard không crash. | Không còn việc trong Recovery UX. |
| UX-108 | **FOLLOW-UP — KHÔNG CHẶN GATE** | Error summary là tiếng Việt nhưng browser-native field messages trong ảnh validation vẫn hiện tiếng Anh, ví dụ “Please fill out this field”. | Chuẩn hóa thông báo validation theo tiếng Việt trong tranche polish nội dung. |
| UX-106 | **PASS** | “Crew List” đã Việt hóa; Bước 4 hiển thị đúng nội dung tiếng Việt. | Không còn việc trong Recovery UX. |
| UX-107 | **PASS** | Không còn stage CV/QLC/BP trong UI/runtime; deny-list và regression test chặn client cũ. | Không xóa deny-list/test. |
| UX-002 cũ | **PASS** | Nhãn “Nháp cục bộ · chưa gửi” phản ánh đúng trạng thái lưu. | Task study đại diện nếu cần đo mức độ hiểu. |
| UX-004 cũ | **PASS** | Checkbox checklist thay native `select multiple`; thao tác bàn phím được browser tester xác nhận tại Bước 4. | Không còn việc trong Recovery UX. |
| Browser Finding 1 | **PASS** | Wizard mở và đi đủ Bước 1→6, submit thành công. | Retest nếu wizard code thay đổi. |
| Browser Finding 2 | **PASS** | Panel tích hợp ẩn với CUSTOMER/PORT_STAFF, hiện với ADMIN. | Retest nếu logic role/CSS thay đổi. |
| Browser Finding 3 | **PASS** | Sidebar mobile 390×844 hiển thị Đăng xuất và icon đúng kích thước. | Retest nếu navigation/CSS thay đổi. |
| Analytics | **CHƯA XỬ LÝ — NGOÀI TRANCHE** | UI báo “Thống kê sản lượng chưa khả dụng”; PL.01–PL.03 hoạt động độc lập. | Work order riêng gồm metrics, API contract, RBAC và acceptance criteria. |
| Gate 5 | **CLOSED (PASS)** | Đủ evidence Bước 1–6, validation, checklist, review/send, submit, console/network và đa viewport. | Không suy diễn thành production release approval. |

## Truy vết đánh giá

- Báo cáo đánh giá gốc: checkpoint `cfc2d84` trong lịch sử Git.
- Browser evidence FAIL ban đầu: `c58c73a`.
- Remediation code: `7c5431d` và `a2b1ca0`.
- Evidence reconciliation: `82b81f9`.
- Full six-step UAT evidence: `3574128`.

Các bản lịch sử được giữ trong Git để truy vết nguyên nhân, remediation và thay
đổi kết luận. Gate 5 CLOSED chỉ áp dụng cho Recovery UX tại code under test;
không đóng Analytics, staging rehearsal hoặc production release gate.
