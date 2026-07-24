# Hướng dẫn sử dụng — Quản Lý Xalan

> Cập nhật theo chức năng ứng dụng ngày 24/07/2026.

## 1. Vai trò và phạm vi sử dụng

| Vai trò | Phạm vi chính |
|---|---|
| `CUSTOMER` | Quản lý thuyền viên và phiếu khai báo của doanh nghiệp mình |
| `PORT_STAFF` | Xử lý nghiệp vụ trong các đơn vị báo cáo được phân công |
| `PLATFORM_ADMIN` | Quản trị toàn nền tảng; phải chọn rõ đơn vị trước khi thao tác dữ liệu của Cảng |

Ứng dụng không còn vai trò admin riêng trong từng Cảng. Nghiệp vụ tại Cảng do
`PORT_STAFF` thực hiện; quản trị toàn hệ thống do `PLATFORM_ADMIN` thực hiện.

## 2. Đăng nhập và chọn đơn vị báo cáo

1. Mở địa chỉ ứng dụng do quản trị viên cung cấp.
2. Nhập tài khoản, mật khẩu và chọn **Đăng nhập**.
3. Với `PORT_STAFF` hoặc `PLATFORM_ADMIN`, mở tên Cảng ở cuối thanh bên trái để
   chọn đơn vị báo cáo đang thao tác.

Mọi danh sách, import và báo cáo sau đó đều thuộc đơn vị đang chọn.
`PLATFORM_ADMIN` có thể chọn **+ Tạo đơn vị mới** trong danh sách này. Nếu phiên
đăng nhập hết hạn, đăng nhập lại rồi chọn lại đơn vị nếu cần.

## 3. Menu chính

- **Tổng quan**: các số liệu và công việc cần chú ý.
- **Phiếu khai báo**: tạo, gửi và xử lý phiếu.
- **Hồ sơ phương tiện**: dữ liệu phương tiện phục vụ khai báo của khách hàng.
- **Sổ theo dõi Salan**: danh sách phương tiện nội bộ của đơn vị báo cáo.
- **Danh sách thuyền viên**: hồ sơ và thời hạn chứng chỉ.
- **Import dữ liệu**: import vận hành hoặc dữ liệu lịch sử/TOS.
- **Báo cáo hoạt động**: dashboard, PL.01–PL.03 và xuất Excel.

Tài khoản `CUSTOMER` chỉ thấy các chức năng phù hợp với phạm vi khách hàng.

## 4. Phiếu khai báo

### Tạo và gửi phiếu

1. Mở **Phiếu khai báo** và chọn tạo phiếu mới.
2. Chọn phương tiện; kiểm tra lại thông tin được kế thừa từ hồ sơ đã có.
3. Chọn thuyền viên và nhập thông tin chuyến, thời gian, hàng hóa, hành khách.
4. Kiểm tra bản xem lại.
5. Chọn **Lưu nháp** để làm tiếp sau hoặc **Gửi** để chuyển cho Cảng xử lý.

`PORT_STAFF` cũng tạo được phiếu mới (ví dụ khi nhận thông tin qua điện thoại/giấy
từ khách hàng), nhưng chỉ **Lưu nháp** — bước **Gửi** (xác nhận nộp phiếu) vẫn chỉ
`CUSTOMER` hoặc `PLATFORM_ADMIN` thực hiện được.

### Trạng thái

| Trạng thái | Ý nghĩa | Khách hàng có thể sửa? |
|---|---|---|
| **Nháp** | Chưa gửi | Có |
| **Chờ Cảng xử lý** | Đã gửi, đang chờ xem xét | Không |
| **Cần bổ sung** | Cảng trả lại kèm yêu cầu | Có |
| **Đã duyệt** | Hoàn tất quy trình | Không |

Khi phiếu ở trạng thái **Cần bổ sung**, mở phiếu, sửa theo nội dung Cảng yêu
cầu và gửi lại. Lịch sử thao tác được lưu trong sự kiện của phiếu.

### Xử lý phiếu tại Cảng

`PORT_STAFF` hoặc `PLATFORM_ADMIN` đang thao tác trong một đơn vị báo cáo có thể:

- xem phiếu thuộc đơn vị đó;
- yêu cầu khách hàng bổ sung và ghi rõ lý do;
- duyệt phiếu hợp lệ.

Phiếu đã duyệt là nguồn dữ liệu LIVE cho báo cáo định kỳ.

## 5. Phương tiện và thuyền viên

### Hồ sơ phương tiện

Đây là hồ sơ dùng trong khai báo khách hàng. Khi thêm hoặc sửa, kiểm tra tên
phương tiện, số đăng ký, loại/cấp và các thông số khai thác trước khi lưu.

### Sổ theo dõi Salan

Đây là sổ nội bộ của từng đơn vị báo cáo. Danh sách dùng cùng thực thể phương
tiện chuẩn, nhưng chỉ hiển thị các phương tiện đã được đưa vào sổ của Cảng.
Số thứ tự được tính thống nhất theo thứ tự danh sách đang hiển thị.

### Danh sách thuyền viên

Thêm hoặc cập nhật họ tên, chức danh và thông tin chứng chỉ. Trạng thái chứng
chỉ cho biết còn hạn, sắp hết hạn, hết hạn hoặc chưa đủ thông tin.

## 6. Import dữ liệu vận hành

Trong **Import dữ liệu**, chọn tab **Dữ liệu vận hành** khi nhập dữ liệu phục vụ
công việc hiện tại:

- hồ sơ phương tiện khách hàng gửi;
- danh sách thuyền viên;
- phiếu khai báo.

Cả ba loại đều mở cho `PORT_STAFF` và `PLATFORM_ADMIN`. Với phiếu khai báo, tên
doanh nghiệp trong file sẽ được dùng để xác định (hoặc tạo mới) khách hàng
thuộc đơn vị báo cáo đang chọn.

Chọn file, xem preview và lỗi theo từng dòng, sau đó mới xác nhận import. Dữ
liệu chưa xác nhận không trở thành dữ liệu vận hành. Nếu file sai, hủy lượt
import, sửa file nguồn và tải lại.

## 7. Import lịch sử/TOS

Chọn tab **Lịch sử / TOS** để nhập dữ liệu phục vụ đối soát và báo cáo lịch sử.
Hệ thống nhận dạng loại workbook theo cấu trúc sheet/cột, không phụ thuộc tên
file. Có thể chọn nhiều file cùng lúc và không bắt buộc tải theo thứ tự.

Ba nguồn được hỗ trợ:

- **TOS Berth**: lượt cập/rời bến, mã bến, ATB và ATD.
- **Chi tiết container**: chuyến, phương án xếp/dỡ, nội/ngoại, TEU và tấn.
- **PL.03 cũ**: bổ sung thông tin phương tiện lịch sử còn thiếu.

### Quy trình kiểm tra

1. Chọn một hoặc nhiều file Excel.
2. Mỗi file tạo một lượt import riêng trong bảng **Lượt import**.
3. Chọn **Xem** để mở preview.
4. Lọc **Cần xử lý** để xem từng dòng, lý do và hướng xử lý.
5. Xác nhận nguồn hợp lệ. Khi có nguồn liên quan được xác nhận, hệ thống tự đối
   soát lại các lượt import cùng đơn vị và cùng kỳ.
6. Nếu phương tiện chưa ghép được, xử lý tại danh sách liên kết phương tiện.
7. Nếu dữ liệu trùng với bản đã lưu, chọn rõ giữ bản đang dùng hay tạo revision
   mới; hệ thống không tự ghi đè âm thầm.

Không cần sửa lỗi chỉ vì dấu phẩy thập phân Việt Nam: ví dụ `331,47` được hiểu
là `331.47` tấn. Cảnh báo chỉ biến mất khi dữ liệu liên quan đã được xác nhận,
đối soát lại và không còn điều kiện gây cảnh báo.

### Thứ tự ưu tiên dữ liệu

- ATB/ATD và bến: lấy từ TOS Berth.
- TEU, tấn và luồng/phương án hàng: lấy từ chi tiết container.
- PL.03 cũ chỉ bổ sung trường phương tiện còn thiếu; không được dùng ETA cũ để
  ghi đè thời gian TOS.
- Nếu Berth chỉ có một mã bến, dùng chung cho bến đến và bến rời; nhân viên Cảng
  chỉnh lại trường hợp hiếm có dịch chuyển bến.
- Trọng lượng container rỗng vẫn được tính vào tấn hàng, đồng thời được tách ở
  chỉ tiêu container rỗng.

File nguồn được đọc để tạo dữ liệu có provenance; hệ thống không sửa workbook
gốc và không đưa dữ liệu lịch sử vào phiếu khai báo LIVE.

### Xuất PL.03 tổng hợp

Sau khi các nguồn đã được xác nhận và đối soát:

1. Chọn tháng, năm tại khối **PL.03 tổng hợp từ TOS**.
2. Chọn **Xuất PL.03 tổng hợp**.
3. Kiểm tra workbook được tạo, đặc biệt các dòng còn thiếu liên kết phương tiện.

File này được tổng hợp lại từ dữ liệu chuẩn TOS và thông tin phương tiện được
ghép, thay vì sao chép nguyên số liệu thủ công của PL.03 cũ.

## 8. Báo cáo hoạt động

### Dashboard sản lượng

`PORT_STAFF` và `PLATFORM_ADMIN` có thể chọn:

- **LIVE**: phiếu đã duyệt trong ứng dụng;
- **LỊCH SỬ**: dữ liệu TOS đã xác nhận;
- **KẾT HỢP**: cộng hai nguồn khi các kỳ không chồng lấn.

Nếu LIVE và LỊCH SỬ chồng lấn trong cùng kỳ, hệ thống chặn việc cộng trùng và
hiển thị mức độ dữ liệu có thể sử dụng. `CUSTOMER` chỉ xem dữ liệu LIVE thuộc
phạm vi của mình.

### Xuất báo cáo

- Chọn tuần, tháng, quý hoặc năm theo nhu cầu.
- Chọn **Xuất Excel** cho dashboard tổng hợp.
- Các biểu PL.01, PL.02 và PL.03 vận hành tiếp tục được tạo từ phiếu đã duyệt.
- PL.03 tái tạo từ TOS được xuất tại tab **Lịch sử / TOS** như hướng dẫn ở trên.

PL.02 cho phép nhân viên Cảng ghi một điều chỉnh có lý do. Điều chỉnh được lưu
như delta có dấu vết và không sửa phiếu khai báo gốc.

## 9. Xử lý tình huống thường gặp

| Tình huống | Cách xử lý |
|---|---|
| Không thấy dữ liệu của Cảng | Kiểm tra đơn vị báo cáo đang chọn ở thanh bên trái |
| Phiếu không sửa được | Kiểm tra trạng thái; chỉ **Nháp** và **Cần bổ sung** được sửa |
| Import vẫn còn cảnh báo sau khi mở lại | Xác nhận nguồn liên quan, chọn **Làm mới**, rồi mở lại preview; cảnh báo tồn tại nếu điều kiện chưa được xử lý |
| Chi tiết container báo chưa ghép lượt | Xác nhận Berth cùng đơn vị/kỳ; hệ thống sẽ tự đối soát lại |
| Báo cáo KẾT HỢP chỉ có một phần | Kiểm tra kỳ bị chồng lấn hoặc lượt import vẫn còn dòng cần xử lý |
| Không xuất được PL.03 tổng hợp | Kiểm tra tháng/năm, trạng thái các nguồn và liên kết phương tiện |
| Hết phiên đăng nhập | Đăng nhập lại; thao tác chưa xác nhận cần được kiểm tra lại |

Khi lỗi vẫn còn, cung cấp cho quản trị viên mã lượt import hoặc mã phiếu, thời
điểm xảy ra và ảnh màn hình; không gửi mật khẩu hay file chứa bí mật hệ thống.
