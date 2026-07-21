# Báo cáo Browser Evidence — Recovery UX (2026-07-14)

Tài liệu này ghi nhận kết quả kiểm thử trực tiếp giao diện và hành vi trên trình duyệt của ứng dụng **Quan-Ly-Xalan** tại branch `recovery` cho vai trò CUSTOMER và các bước của Wizard.

---

## 1. Môi trường và bối cảnh kiểm thử

- **Worktree:** `D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux`
- **Branch:** `recovery/frontend-baseline-20260712`
- **Application code under test:** `a2b1ca0`
- **Evidence reconciliation base:** `82b81f9`
- **Full-flow evidence commit:** `3574128`
- **URL thử nghiệm:** `http://127.0.0.1:8086`
- **Môi trường DB:** Database SQLite sạch (`data/cang_vu.db`)
- **Tài khoản sử dụng:** Khách hàng: `khachhang` / `demo123`

---

## 2. Kết quả kiểm thử hành trình Wizard CUSTOMER (Steps 1–6)

### Bước 1 — Phương tiện: **PASS**
- **Hành vi:** Mở wizard qua nút "+ Tạo phiếu" tại trang Phiếu khai báo. Khi bấm "Tiếp tục" không chọn phương tiện, validation hoạt động và báo lỗi. Khi chọn "Sà lan SG-168", dữ liệu tự điền và bị khóa (locked-field class).
- **Screenshot:** `customer_1920x1080_wizard-step1-validation_pass.png` và `customer_1920x1080_wizard-step1_pass.png`

### Bước 2 — Hành trình: **PASS**
- **Hành vi:** Nhập dữ liệu hợp lệ (Vũng Tàu → Tân Thuận, ETA 2026-07-20 08:00, ETD 2026-07-21 08:00). Nút "Tiếp tục" hoạt động chuyển sang Bước 3 không có lỗi console.
- **Screenshot:** `customer_1920x1080_wizard-step2_pass.png`

### Bước 3 — Hàng hóa: **PASS**
- **Hành vi:** Nhập dữ liệu hàng dỡ là "Hàng tổng hợp", hàng xếp là "Container rỗng". Validation hoạt động bình thường.
- **Screenshot:** `customer_1920x1080_wizard-step3_pass.png`

### Bước 4 — Thuyền trưởng và thuyền viên: **PASS**
- **Hành vi:** Checkbox checklist hiển thị thay thế hoàn toàn cho native select multiple. Bàn phím Tab/Shift+Tab và Space hoạt động tốt để chọn/bỏ chọn thành viên.
- **Screenshot:** `customer_1920x1080_wizard-step4-crew-checklist_pass.png`

### Bước 5 — Đính kèm: **PASS**
- **Hành vi:** Hiển thị khu vực đính kèm file hỗ trợ ảnh/PDF/Word/Excel. Thao tác và giao diện chuẩn theo dữ liệu demo.
- **Screenshot:** `customer_1920x1080_wizard-step5_pass.png`

### Bước 6 — Xem lại & Gửi: **PASS**
- **Hành vi:** Hiển thị thông tin tổng hợp đầy đủ của các bước trước. Thuật ngữ là "Xác nhận & gửi", không có từ "Nộp".
- **Screenshot:** `customer_1920x1080_wizard-step6-review_pass.png`

### Submit & Phản hồi thành công: **PASS**
- **Hành vi:** Bấm "Xác nhận & gửi" thực hiện gửi dữ liệu thành công. Wizard đóng lại, toast thông báo thành công và phiếu mới xuất hiện trong danh sách ở trạng thái PENDING_REVIEW.
- **Screenshot:** `customer_1920x1080_wizard-submit-success_pass.png`

---

## 3. Nhật ký kiểm tra Console & Network
- Không có lỗi uncaught JavaScript error trong suốt luồng.
- Không có lỗi HTTP 4xx/5xx ngoài các kiểm thử validation có chủ ý.
- Focus recovery hoạt động đúng và đưa tiêu điểm về lỗi đầu tiên khi validation thất bại.
- CUSTOMER không nhìn thấy panel tích hợp (style.display = none).
- Không xuất hiện bất kỳ chuỗi role/stage cũ nào như "Chờ CV", "Chờ QLC", "Chờ BP".

---

## 4. Kết luận Gate 5
> [!NOTE]
> **GATE 5 STATUS: CLOSED (PASS)**
>
> Đã thu thập đầy đủ bằng chứng kiểm thử trực quan trên trình duyệt thật cho toàn bộ 6 bước của wizard tạo phiếu của khách hàng. Mọi yêu cầu kỹ thuật và chất lượng UAT đều đã được đáp ứng. Nhánh recovery đã đủ điều kiện đóng Gate 5.
