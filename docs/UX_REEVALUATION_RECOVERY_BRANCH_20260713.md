# Đánh giá lại UX — Recovery Checkpoint

## Trạng thái kiểm soát — 2026-07-14

- Branch: `recovery/frontend-baseline-20260712`
- Browser retest/frontend follow-up: `a2b1ca0`
- Automated regression: `67 passed`; `node --check frontend/app.js` PASS.
- Ba finding browser trực tiếp: **PASS**.
- Gate 5: **OPEN — chờ UAT wizard đủ sáu bước**.
- Analytics: ngoài tranche, chưa triển khai.

Báo cáo browser tại `docs/BROWSER_EVIDENCE_RECOVERY_UX_20260714.md` chứng minh
wizard mở được ở Bước 1, panel tích hợp hiển thị đúng CUSTOMER/PORT_STAFF/ADMIN
và menu mobile truy cập được Đăng xuất. Báo cáo chưa có ảnh Bước 4, Bước 6 hay
console/network xuyên suốt toàn bộ wizard, nên không được diễn giải thành bằng
chứng đóng toàn bộ Gate 5.

## Sổ trạng thái hiện hành

| Mã | Trạng thái | Kết luận hiện hành | Còn thiếu hoặc cần chờ |
|---|---|---|---|
| CRIT-001 | **ĐÃ XỬ LÝ** | Runtime chỉ còn `PORT_APPROVE` và `REQUEST_CHANGES`; action CV/QLC/BP cũ trả HTTP 410; migration dùng `PORT_STAFF` và `port_approval`. | Rehearsal trên bản sao staging trước production. |
| UX-101 | **ĐÍNH CHÍNH** | API đã tìm theo `vessel_name`; thuyền trưởng có filter `master_name`. Đây không phải finding typography. | Product Owner quyết định có cần tìm kiếm không dấu (`Hai` → `Hải`). |
| UX-102 | **ĐÃ CÓ SẴN** | Phân trang hoạt động khi gửi `page`; response mảng khi thiếu `page` là tương thích ngược có chủ ý. | Performance test với tập dữ liệu tham chiếu nếu Gate 5 yêu cầu. |
| UX-103 | **ĐÃ XỬ LÝ** | UI/audit dùng “Xác nhận & gửi”, không dùng “Nộp/nộp” cho khách hàng. | Rà soát lại trong full-flow UAT. |
| UX-104 | **CHƯA ĐÓNG** | Dashboard đã ẩn chức năng theo role và có attention queue. | Task study/UAT để xác định thứ tự widget; không tái cấu trúc theo cảm tính. |
| UX-105 | **MỘT PHẦN PASS** | Wizard mở được ở Bước 1; crash null đã hết. | Đi đủ sáu bước, kiểm tra validation, error summary và focus recovery. |
| UX-106 | **ĐÃ XỬ LÝ** | “Crew List” đã Việt hóa. | Quan sát lại tại Bước 4. |
| UX-107 | **PASS** | Không còn stage CV/QLC/BP trong UI/runtime; deny-list và regression test được giữ để chặn client cũ. | Không xóa deny-list/test. |
| UX-002 cũ | **ĐÃ XỬ LÝ** | Nhãn “Nháp cục bộ · chưa gửi” phản ánh đúng trạng thái lưu. | Xác nhận cách hiểu trong UAT đại diện. |
| UX-004 cũ | **CHỜ FULL-FLOW UAT** | Checkbox checklist đã thay native `select multiple`; code và regression PASS. | Ảnh/thao tác Tab/Space tại Bước 4. |
| Browser Finding 1 | **PASS** | Wizard mở thành công tại Bước 1 trên browser thật. | Không đồng nghĩa toàn bộ wizard đã PASS. |
| Browser Finding 2 | **PASS** | Panel tích hợp ẩn với CUSTOMER, hiện với ADMIN; không thấy lỗi 403/404 trong scenario báo cáo. | Retest nếu logic role/CSS thay đổi. |
| Browser Finding 3 | **PASS** | Sidebar mobile 390×844 hiển thị Đăng xuất và icon đúng kích thước. | Retest nếu navigation/CSS thay đổi. |
| Analytics | **CHƯA XỬ LÝ — NGOÀI TRANCHE** | UI báo “Thống kê sản lượng chưa khả dụng”; PL.01–PL.03 hoạt động độc lập. | Work order riêng gồm metrics, API contract, RBAC và acceptance criteria. |
| Gate 5 | **OPEN** | Ba regression finding đã PASS. | Bổ sung evidence Bước 4, Bước 6 và console/network cho hành trình sáu bước. |

## Truy vết đánh giá

- Báo cáo đánh giá gốc: checkpoint `cfc2d84` trong lịch sử Git.
- Browser evidence FAIL ban đầu: `c58c73a`.
- Remediation code: `7c5431d`.
- Ledger/handoff trước browser retest: `5686fd2`.
- Browser retest và frontend follow-up: `a2b1ca0`.

Các bản lịch sử không bị coi là trạng thái hiện hành, nhưng phải được giữ trong
Git để truy vết nguyên nhân, thay đổi kết luận và phạm vi bằng chứng.

## Điều kiện đóng Gate 5

1. CUSTOMER đi đủ Bước 1 → Bước 6 trên HEAD hiện hành.
2. Ghi bằng chứng checkbox thuyền viên ở Bước 4 và Xem lại & Gửi ở Bước 6.
3. Xác nhận validation/focus recovery và không có lỗi console/network trong
   toàn bộ hành trình.
4. Cập nhật browser report, checkpoint, session handoff và `AGENT_HANDOFF.md`
   trong cùng một commit; không dùng trạng thái vừa `CLOSED` vừa `chờ retest`.
5. Không gộp Analytics hoặc production/staging rehearsal vào tuyên bố UX PASS.
