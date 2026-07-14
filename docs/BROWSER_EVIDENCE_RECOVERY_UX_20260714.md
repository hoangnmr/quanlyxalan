# Báo cáo Browser Evidence — Recovery UX (2026-07-14)

Tài liệu này ghi nhận kết quả kiểm thử trực tiếp giao diện và hành vi trên trình duyệt của ứng dụng **Khai-bao-Cang-vu** tại branch `recovery` sau khi đã áp dụng các sửa đổi frontend.

---

## 1. Môi trường và bối cảnh kiểm thử

- **Worktree:** `D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux`
- **Branch:** `recovery/frontend-baseline-20260712`
- **HEAD kiểm thử:** mã nguồn được commit tại `a2b1ca0`
- **URL thử nghiệm:** `http://127.0.0.1:8086`
- **Thời gian thực hiện:** 2026-07-14 11:00 (Giờ hệ thống)
- **Môi trường DB:** Database SQLite sạch (`data/cang_vu.db`), nâng cấp bằng `alembic upgrade head`, seed dữ liệu demo bằng `seed_demo_data.py`, bootstrap tài khoản admin bằng `bootstrap_admin.py`.
- **Tài khoản sử dụng:**
  - Khách hàng: `khachhang` / `demo123`
  - Nhân viên Cảng: `nhanviencang` / `demo123`
  - Quản trị viên: `admin` / `demo123`

---

## 2. Ma trận Viewport × Role × Scenario (ĐÃ PASS TOÀN BỘ)

| Role | Viewport | Kịch bản / Luồng chính | Kết quả | Chi tiết / Screenshot |
|---|---|---|---|---|
| **CUSTOMER** | Desktop (1920×1080) | Đăng nhập & xem Dashboard | **PASS** | `customer_1920x1080_dashboard_pass.png` |
| | | Tạo phiếu / Mở wizard | **PASS — phạm vi mở Bước 1** | Wizard mở ra thành công ở Bước 1. `customer_1920x1080_wizard-step1_pass.png` |
| | | Trang Báo cáo (Ẩn panel ngoài) | **PASS** | Ẩn hoàn toàn panel Kết nối ngoài. `customer_1920x1080_reports-no-errors_pass.png` |
| | Laptop (1366×768) | Xem Dashboard | **PASS** | `customer_1366x768_dashboard_pass.png` |
| | | Trang Báo cáo | **PASS** | Ẩn panel kết nối ngoài thành công. `customer_1366x768_reports-no-errors_pass.png` |
| | Mobile (390×844) | Xem Dashboard | **PASS** | `customer_390x844_dashboard_pass.png` |
| | | Menu điều hướng (hamburger) | **PASS** | Menu co gọn icon 16px, nút Đăng xuất hiển thị tốt. `customer_390x844_menu-open_pass.png` |
| | | Trang Báo cáo | **PASS** | Ẩn panel kết nối ngoài thành công. `customer_390x844_reports_pass.png` |
| **PORT_STAFF**| Desktop (1920×1080) | Xem Dashboard & Menu ẩn | **PASS** | Không thấy nút tạo phiếu/import. `port-staff_1920x1080_dashboard_pass.png` |
| | | Chi tiết & timeline phiếu | **PASS** | Thấy timeline và form thao tác Cảng. |
| | | Thao tác Yêu cầu bổ sung | **PASS** | Chặn nếu note rỗng (`port-staff_1920x1080_request-changes_fail.png`); lưu được nếu điền note (`port-staff_1920x1080_request-changes_pass.png`). |
| | | Khách hàng xem lại lý do | **PASS** | Khách hàng thấy lý do phản hồi. `customer_1920x1080_view-changes-request_pass.png` |
| | Laptop (1366×768) | Chi tiết phiếu | **PASS** | `port-staff_1366x768_details_pass.png` |
| | Mobile (390×844) | Chi tiết phiếu | **PASS** | Layout modal co giãn phù hợp. `port-staff_390x844_details_pass.png` |
| **ADMIN** | Desktop (1920×1080) | Dashboard quản trị & backup | **PASS** | `admin_1920x1080_dashboard_pass.png` |
| | | Quyền hạn & Giới hạn duyệt | **PASS** | Không thấy nút tạo phiếu, không duyệt thay Port Staff. |
| | | Trang Báo cáo | **PASS** | Panel tích hợp hiện cho Admin, gọi API thành công không bị 403. `admin_1920x1080_reports_pass.png` |

---

## 3. Danh sách Screenshot Evidence

Tất cả các screenshot được lưu trữ tại thư mục:
`docs/evidence/recovery-ux-20260714/`

1. [customer_1920x1080_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_dashboard_pass.png)
2. [customer_1920x1080_wizard-step1_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_wizard-step1_pass.png)
3. [customer_1920x1080_reports-no-errors_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_reports-no-errors_pass.png)
4. [customer_1366x768_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1366x768_dashboard_pass.png)
5. [customer_1366x768_reports-no-errors_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1366x768_reports-no-errors_pass.png)
6. [customer_390x844_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_390x844_dashboard_pass.png)
7. [customer_390x844_menu-open_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_390x844_menu-open_pass.png)
8. [customer_390x844_reports_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_390x844_reports_pass.png)
9. [port-staff_1920x1080_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1920x1080_dashboard_pass.png)
10. [port-staff_1920x1080_request-changes_fail.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1920x1080_request-changes_fail.png)
11. [port-staff_1920x1080_request-changes_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1920x1080_request-changes_pass.png)
12. [customer_1920x1080_view-changes-request_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_view-changes-request_pass.png)
13. [port-staff_1366x768_details_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1366x768_details_pass.png)
14. [port-staff_390x844_details_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_390x844_details_pass.png)
15. [admin_1920x1080_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/admin_1920x1080_dashboard_pass.png)
16. [admin_1920x1080_reports_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/admin_1920x1080_reports_pass.png)

---

## 4. Console & Network Evidence (Sau khi vá lỗi)

### A. Sự cố Wizard (Đã khắc phục)
- **Kết quả:** Khi bấm nút **"+ Tạo phiếu"** hoặc **"Mở phiếu"** (đối với nháp), wizard mở ra bình thường không còn crash.
- **Giải pháp áp dụng:** Cấu hình biến check `crewContainer` trong `reviewSummaryHtml()` của `frontend/app.js` an toàn trước khi gọi selector đếm thuyền viên, tránh việc query trên phần tử DOM chưa tồn tại.

### B. Network & Display (Sau khi vá lỗi)
- **Tích hợp ngoài:** Sử dụng inline style `display: none` / `display: grid` trong `app.js` dòng 1234. Giải pháp này đảm bảo ghi đè hoàn toàn rule `.integration-panel` của CSS, panel tích hợp bị ẩn tuyệt đối cho vai trò CUSTOMER và PORT_STAFF mà không bị rò rỉ. Không có lệnh gọi API mạng bị chặn hay lỗi 403/404 phát sinh.

---

## 5. Keyboard & Accessibility Evidence

- **Tab/Shift+Tab:** Hoạt động tốt trên navigation menu và trường form. Thao tác chuyển focus rõ ràng.
- **Focus Ring:** Vòng focus có viền màu xanh (teal) hiển thị rõ ràng trên các nút và input nhờ CSS selector `:focus-visible` trong `styles.css`.
- **Nút Đăng xuất Mobile (Đã khắc phục):** Sửa lỗi co gọn kích thước icon SVG trong menu sidebar về đúng kích thước chuẩn 16px. Điều này giúp dọn sạch không gian thừa bị lấn chiếm bởi icon khổng lồ, toàn bộ sidebar co gọn đẹp mắt và nút Đăng xuất hiển thị đầy đủ ngay trong tầm nhìn và tiêu điểm bàn phím ở mobile viewport (390×844) mà không cần cuộn dọc.

---

## 6. Danh sách Findings và Phân lớp Kết luận

- **Finding 1 (Wizard JS Crash):** **RESOLVED (PASS)**
- **Finding 2 (CSS Hidden Leak):** **RESOLVED (PASS)**
- **Finding 3 (Mobile Sidebar Scroll/Icons layout):** **RESOLVED (PASS)**

---

## 7. Trạng thái Gate 5 và Đánh giá cuối cùng

### Kết luận Gate 5:
> [!NOTE]
> **REMEDIATION STATUS: PASS — GATE 5 CLOSURE PENDING**
> 
> Sau khi áp dụng các bản vá frontend, ba finding trực tiếp đã PASS trên trình
> duyệt thật: wizard mở được, panel tích hợp hiển thị đúng theo role và menu
> mobile truy cập được Đăng xuất. Tuy nhiên evidence hiện chỉ ghi nhận wizard
> tại Bước 1, chưa đi đủ sáu bước đến màn Xem lại & Gửi. Vì vậy chưa dùng báo
> cáo này để tuyên bố đóng toàn bộ Gate 5 hoặc tích hợp branch.

### Bằng chứng còn thiếu để đóng Gate 5

1. Đi đủ sáu bước wizard bằng tài khoản CUSTOMER trên HEAD `a2b1ca0`.
2. Xác nhận validation/focus recovery, checklist thuyền viên và màn Xem lại & Gửi.
3. Ghi ảnh hoặc video tối thiểu tại Bước 4 và Bước 6; ghi rõ console/network
   không có lỗi trong toàn bộ hành trình.
