# Đánh giá độc lập UX/Product — Quản Lý Xalan

Ngày: 2026-07-13

Vai đánh giá: chuyên gia UX/Product độc lập

Phạm vi: khả năng hoàn thành công việc, độ dễ học, tải nhận thức, phản hồi lỗi,
accessibility và trải nghiệm theo vai trò.

## 1. Ranh giới bằng chứng

Đánh giá ban đầu này là heuristic review dựa trên cấu trúc giao diện, mã
frontend và tài liệu người dùng. Phiên trình duyệt tương tác không khả dụng tại
thời điểm đánh giá, vì vậy các nhận định dưới đây là **giả thuyết cần kiểm chứng**,
không phải kết quả usability test với người dùng thật.

Không được dùng tài liệu này để tuyên bố Gate 5 đã đóng. Gate 5 chỉ được đánh giá
lại sau khi có task study, accessibility audit, responsive matrix và performance
traces thực tế.

## 2. Nhận định UX/Product ban đầu

Điểm tham chiếu heuristic: **5,5/10**. Đây không phải điểm UAT.

### Điểm mạnh cần giữ

- Wizard khai báo sáu bước, có xem lại trước khi nộp.
- Tự động điền dữ liệu phương tiện và gợi ý từ lượt gần nhất.
- Lưu nháp, trạng thái đang xử lý và thông báo kết quả.
- Empty state, responsive table, focus indicator và reduced-motion hook đã có.
- Dashboard có hàng đợi cần chú ý theo vai trò.

### Giả thuyết UX cần kiểm chứng

1. Wizard chưa khớp mô hình tư duy người khai: thứ tự bước hiển thị khác thứ tự
   nhãn hồ sơ `A → E → B → C/D`, bước đầu còn quá dày thông tin.
2. Điều hướng chưa đủ theo vai trò; người dùng vẫn phải tự lọc danh sách để tìm
   việc cần xử lý.
3. Lỗi chủ yếu qua toast/native validation; người dùng có thể không biết trường
   nào cần sửa trong biểu mẫu dài.
4. Dòng chữ “Tự lưu trên trình duyệt” có thể khiến người dùng tưởng nháp đã được
   lưu an toàn trên hệ thống.
5. `select multiple` cho thuyền viên có thể khó dùng trên mobile và với người
   không quen thao tác bàn phím.
6. Một số hook accessibility đã có nhưng thanh bước wizard và một số thao tác
   click cần kiểm chứng bằng bàn phím/screen reader.
7. Dashboard đang trộn tổng quan, hàng đợi, cấu hình cá nhân, quản trị và backup,
   làm giảm độ ưu tiên thị giác.
8. Thuật ngữ Việt/Anh (`Crew List`, `Import`, `Backup`, `API`, `payload`) chưa
   hoàn toàn nhất quán với ngôn ngữ người dùng cuối.

## 3. Kịch bản test thực tế cho Claude

Sử dụng dữ liệu mẫu đã được cho phép, không dùng dữ liệu production thật. Ghi rõ
browser, hệ điều hành, viewport, tài khoản/role, số dòng dữ liệu và thời điểm.

| Role | Kịch bản bắt buộc | Kết quả cần quan sát |
|---|---|---|
| CUSTOMER | Tạo, lưu nháp, quay lại sửa và nộp một khai báo có phương tiện, thuyền trưởng, hàng hóa và một file đính kèm | Người dùng có biết bước tiếp theo, hiểu trường bắt buộc, nhận biết nháp đã lưu và hoàn tất không cần trợ giúp |
| CUSTOMER | Chuyển giữa phương tiện đã có hồ sơ và phương tiện mới | Người dùng có hiểu dữ liệu nào được tự điền, dữ liệu nào sẽ được lưu mới và có bị mất dữ liệu đã nhập không |
| CV | Tìm phiếu chờ xử lý, mở chi tiết, yêu cầu bổ sung với lý do | Có tìm được đúng hàng đợi trong thời gian ngắn; lý do và trạng thái sau thao tác có rõ không |
| QLC | Tìm phiếu đúng trạng thái và duyệt | Không thao tác nhầm phiếu; hệ thống giải thích rõ khi hành động không được phép |
| BP | Hoàn tất duyệt/cấp phép và kiểm tra timeline | Người dùng có hiểu trạng thái cuối, số permit và tác động của thao tác không |
| ADMIN | Xem attention queue, lọc dữ liệu, kiểm tra backup và trạng thái tích hợp | Khu vực quản trị có tách biệt khỏi công việc nghiệp vụ thường ngày không |

## 4. Ma trận usability cần thu thập

Cho mỗi kịch bản, ghi:

- thời gian hoàn thành;
- tỷ lệ hoàn thành không trợ giúp;
- số lỗi và số lần quay lại bước trước;
- số lần người test hỏi “tiếp theo làm gì?”;
- số lần bấm lặp hoặc gửi nhầm;
- mức tự tin sau thao tác, thang 1–5;
- lỗi nghiêm trọng, nghiêm trọng vừa, trung bình, nhỏ;
- trích dẫn ngắn của người dùng giải thích điểm khó hiểu.

Mốc tham chiếu đề xuất:

- CUSTOMER: ≥90% hoàn thành không trợ giúp, ≤8 phút;
- CV: ≥90%, ≤3 phút;
- QLC: ≥90%, ≤2 phút;
- BP: ≥90%, ≤2 phút;
- ADMIN: ≥90%, ≤4 phút.

Nếu không đạt, ghi rõ điều kiện test và tạo finding riêng; không tự điều chỉnh
ngưỡng sau khi thấy kết quả.

## 5. Accessibility và responsive evidence

Kiểm tra tối thiểu:

1. Keyboard-only: skip link, thứ tự focus, wizard step, dialog mở/đóng, submit và
   focus sau lỗi.
2. Screen reader: page context, nhãn trường, toast lỗi, trạng thái busy, bảng và
   trạng thái workflow.
3. Zoom 200% và reduced motion.
4. Viewport 375×667, 768×1024 và 1440×900.
5. Không có overflow ngang ngoài bảng có chủ đích; dialog vẫn thao tác được ở
   375px.
6. Với mỗi role, thử một thao tác bị ẩn trên UI bằng HTTP trực tiếp; API phải từ
   chối đúng và UI phải giải thích được kết quả.

Gate 5 không đạt nếu còn lỗi accessibility mức critical hoặc serious.

## 6. Performance evidence

Chạy warm local run, ba mẫu cho mỗi chỉ số và lấy median:

- dashboard API: ≤500 ms;
- danh sách phiếu đã lọc 25 dòng: ≤750 ms;
- render 25 dòng sau API: ≤250 ms;
- lưu nháp tới thông báo thành công: ≤1 giây;
- document + JS + CSS trước dữ liệu người dùng: ≤750 KB.

Đính kèm trace, kích thước dataset, số dòng database và trạng thái cache cho mọi
chỉ số không đạt.

## 7. Mẫu kết luận sau test

Claude cần trả về một bảng gồm:

| Finding | Bằng chứng | Mức độ | Role bị ảnh hưởng | Khuyến nghị | Có cần sửa trước Gate 5? |
|---|---|---|---|---|---|
| UX-xxx | screenshot/trace/task sheet | critical/serious/moderate/minor | role | thay đổi cụ thể | yes/no |

Kết luận cuối phải tách ba lớp:

1. **Đã chứng minh** — có task result hoặc trace lặp lại được.
2. **Chưa chứng minh** — có giả thuyết nhưng chưa đủ mẫu/bằng chứng.
3. **Ngoài phạm vi** — cần owner, môi trường hoặc quyết định sản phẩm.

## 8. Liên kết quản trị

- Quy trình Gate 5: `docs/T5_GATE5_EVIDENCE_PROTOCOL.md`.
- Roadmap ưu tiên kỹ thuật và UX: `docs/EA_EVALUATION_ROADMAP.md`.
- Hướng dẫn người dùng: `USER_GUIDE.md`.

Không đánh dấu Gate 5 hoặc Production UX readiness là CLOSED chỉ từ review mã,
screenshot đơn lẻ hoặc test với dữ liệu do chính người phát triển thao tác.
