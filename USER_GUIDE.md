# Hướng Dẫn Sử Dụng - Port Declaration System

Chào mừng đến với hệ thống khai báo cảng vụ của **TAN THUAN PORT**. Tài liệu này hướng dẫn bạn cách sử dụng các tính năng chính của ứng dụng.

---

## 🚀 Các Tính Năng Thông Minh Hỗ Trợ User

Ứng dụng được thiết kế với nhiều **tính năng thông minh** giúp bạn làm việc nhanh chóng và chính xác:

### ✨ **Tự Động Điền Thông Tin (Auto-Suggest)**
- Khi chọn tàu trong khai báo mới, hệ thống **tự động tìm kiếm khai báo trước đó** của tàu đó
- Các thông tin như cảng, hàng hóa, thuyền viên sẽ **được điền sẵn**
- Bạn chỉ cần **kiểm tra & cập nhật** những gì thay đổi
- ⏱️ **Tiết kiệm thời gian**: Không cần nhập lại toàn bộ thông tin

### ⚠️ **Cảnh Báo Thông Minh (Smart Warnings)**
- Hệ thống **tự động theo dõi** ngày hết hạn chứng chỉ thuyền viên
- **Cảnh báo khi sắp hết hạn** (còn < 3 tháng) - bạn có thời gian chuẩn bị
- **Cảnh báo khi đã hết hạn** - ngăn chặn thuyền viên không thể làm việc
- Hiển thị rõ ràng trên Dashboard với biểu tượng 🟢🟡🔴

### 🔄 **Quản Lý Trạng Thái Thông Minh (Smart Workflow)**
- Ứng dụng **chỉ cho phép chỉnh sửa ở trạng thái phù hợp**
  - DRAFT: Chỉnh sửa tự do
  - PENDING_REVIEW: Khóa chỉnh sửa (đang chờ xem xét)
  - CHANGES_REQUESTED: Mở khóa để bạn sửa theo yêu cầu
  - APPROVED/ISSUED: Khóa hoàn toàn (khai báo cuối cùng)
- Ngăn chặn sai sót và mất dữ liệu

### 📊 **Báo Cáo Tự Động (Auto-Filtering Reports)**
- Báo cáo **tự động lọc chỉ các khai báo được phê duyệt**
- **Loại trừ các nháp** và khai báo chưa hoàn tất
- Đảm bảo báo cáo luôn chính xác và tuân thủ quy định
- Hỗ trợ **xuất Excel** và **in PDF** một cú nhấp chuột

### 🔍 **Tìm Kiếm & Lọc Nhanh (Smart Search & Filter)**
- **Lọc khai báo** theo trạng thái, tàu, ngày tháng
- **Tìm kiếm nhanh** danh sách tàu và thuyền viên
- **Phân trang thông minh** cho danh sách lớn
- Tiết kiệm thời gian tìm kiếm thông tin cần thiết

### ✅ **Xác Thực Dữ Liệu (Smart Validation)**
- **Kiểm tra tự động** các trường bắt buộc
- **Cảnh báo lỗi** trước khi gửi khai báo
- Hỗ trợ **người dùng phát hiện và sửa lỗi** trước khi gửi
- Giảm lỗi nhập liệu

### 📱 **Giao Diện Thân Thiện (User-Friendly Interface)**
- **Wizard hướng dẫn từng bước** cho khai báo mới
- **Thanh điều hướng rõ ràng** dễ tìm chức năng
- **Thông báo và cảnh báo** trực quan và rõ ràng
- **Biểu tượng trạng thái** dễ nhận biết ngay tức thì

### 🔐 **Bảo Mật Phiên Đăng Nhập (Session Security)**
- **Tự động phát hiện hết phiên** và yêu cầu đăng nhập lại
- **Bảo vệ dữ liệu** khỏi truy cập không được phép
- **Token xác thực** được mã hóa và bảo mật

---

## 📋 Mục Lục

1. [Đăng Nhập](#đăng-nhập)
2. [Bảng Điều Khiển (Dashboard)](#bảng-điều-khiển-dashboard)
3. [Quản Lý Tàu (Vessels)](#quản-lý-tàu-vessels)
4. [Quản Lý Thuyền Viên (Crew)](#quản-lý-thuyền-viên-crew)
5. [Khai Báo Cảng Vụ (Declarations)](#khai-báo-cảng-vụ-declarations)
6. [Báo Cáo (Reports)](#báo-cáo-reports)
7. [Các Mẹo & Thủ Thuật](#các-mẹo--thủ-thuật)

---

## Đăng Nhập

### Bước 1: Truy Cập Ứng Dụng
- Mở trình duyệt web của bạn
- Nhập địa chỉ: `http://127.0.0.1:8080`

### Bước 2: Nhập Thông Tin Đăng Nhập
- **Username**: Tên tài khoản của bạn
- **Password**: Mật khẩu của bạn
- Nhấn nút **"Đăng Nhập"**

### Lưu Ý:
- Phiên đăng nhập sẽ hết hạn sau một thời gian không hoạt động
- Nếu bạn thấy thông báo "Phiên đăng nhập đã hết hạn", hãy đăng nhập lại

---

## Bảng Điều Khiển (Dashboard)

Sau khi đăng nhập, bạn sẽ được đưa đến bảng điều khiển chính.

### Các Thành Phần Chính:

#### **1. Thông Tin Khách Hàng (Customer Info)**
- Hiển thị tên công ty/tổ chức của bạn
- Hiển thị số điện thoại liên hệ

#### **2. Danh Sách Khai Báo (Declarations)**
- Xem tất cả các khai báo cảng vụ của bạn
- Mỗi khai báo hiển thị:
  - Tên tàu (Vessel)
  - Ngày khai báo
  - Trạng thái khai báo

#### **3. Cảnh Báo Chứng Chỉ (Certificate Warnings)**
- Hiển thị cảnh báo về chứng chỉ thuyền viên sắp hết hạn hoặc đã hết hạn
- Biểu tượng ⚠️ cho biết có vấn đề cần xử lý

#### **4. Thanh Điều Hướng (Navigation)**
- **THÔNG TIN KHÁCH HÀNG** - Xem/chỉnh sửa thông tin công ty
- **DANH SÁCH THUYỀN VIÊN** - Quản lý danh sách thuyền viên
- **DANH SÁCH TÀU** - Quản lý danh sách tàu
- **KHAI BÁO CẢNG VỤ** - Xem và tạo khai báo cảng vụ
- **BÁO CÁO** - Xem báo cáo khai báo

---

## Quản Lý Tàu (Vessels)

### Xem Danh Sách Tàu

1. Nhấn vào **"DANH SÁCH TÀU"** trong menu trên cùng
2. Bạn sẽ thấy danh sách tất cả tàu của công ty bạn
3. Mỗi tàu hiển thị:
   - **Tên tàu** (Vessel Name)
   - **Quốc gia** (Country)
   - **Loại tàu** (Vessel Type)
   - **Cảng đăng ký** (Port of Registry)
   - **IMO/Flag State**

### Thêm Tàu Mới

1. Trong danh sách tàu, nhấn nút **"Thêm Tàu"** hoặc **"➕"**
2. Điền các thông tin bắt buộc:
   - **Tên tàu** (Vessel Name)
   - **Quốc gia** (Country)
   - **Loại tàu** (Vessel Type)
   - **Cảng đăng ký** (Port of Registry)
3. Các trường tùy chọn:
   - **IMO** (Quốc tế Tàu)
   - **Flag State** (Quốc gia cấp cờ)
   - **Chiều dài** (Length)
   - **Chiều rộng** (Beam)
   - **Năm đóng** (Year Built)
4. Nhấn **"Lưu"** để thêm tàu

### Chỉnh Sửa Thông Tin Tàu

1. Nhấn vào tên tàu hoặc nút **"Chỉnh Sửa"** 
2. Thay đổi thông tin cần thiết
3. Nhấn **"Cập Nhật"** để lưu thay đổi

---

## Quản Lý Thuyền Viên (Crew)

### Xem Danh Sách Thuyền Viên

1. Nhấn vào **"DANH SÁCH THUYỀN VIÊN"** trong menu trên cùng
2. Bạn sẽ thấy danh sách tất cả thuyền viên
3. Mỗi thuyền viên hiển thị:
   - **Tên** (Full Name)
   - **Vị trí công việc** (Position)
   - **Quốc gia** (Nationality)
   - **Tình trạng chứng chỉ** (Certificate Status)

### Tình Trạng Chứng Chỉ

- 🟢 **VALID** - Chứng chỉ còn hiệu lực
- 🟡 **EXPIRING** - Chứng chỉ sắp hết hạn (trong 3 tháng)
- 🔴 **EXPIRED** - Chứng chỉ đã hết hạn
- ⚪ **UNKNOWN** - Không xác định được tình trạng

### Thêm Thuyền Viên Mới

1. Trong danh sách thuyền viên, nhấn **"Thêm Thuyền Viên"** hoặc **"➕"**
2. Điền các thông tin:
   - **Tên** (Full Name) - *Bắt buộc*
   - **Vị trí công việc** (Position) - *Bắt buộc*
   - **Quốc gia** (Nationality) - *Bắt buộc*
   - **Số chứng minh thư** (ID Number)
   - **Ngày cấp chứng chỉ** (Certificate Issue Date)
   - **Ngày hết hạn chứng chỉ** (Certificate Expiry Date)
3. Nhấn **"Lưu"** để thêm thuyền viên

### Chỉnh Sửa Thông Tin Thuyền Viên

1. Nhấn vào tên thuyền viên hoặc nút **"Chỉnh Sửa"**
2. Cập nhật thông tin (đặc biệt là ngày hết hạn chứng chỉ)
3. Nhấn **"Cập Nhật"** để lưu

### Cảnh Báo Chứng Chỉ

Ứng dụng sẽ tự động cảnh báo nếu:
- Chứng chỉ sắp hết hạn (< 3 tháng)
- Chứng chỉ đã hết hạn
- Trạng thái chứng chỉ không rõ ràng

---

## Khai Báo Cảng Vụ (Declarations)

### Xem Danh Sách Khai Báo

1. Nhấn vào **"KHAI BÁO CẢNG VỤ"** trong menu trên cùng
2. Bạn sẽ thấy danh sách tất cả khai báo
3. Mỗi khai báo hiển thị:
   - **Tên tàu** (Vessel)
   - **Ngày khai báo** (Declaration Date)
   - **Trạng thái** (Status)

### Trạng Thái Khai Báo

- **DRAFT** - Nháp, chưa gửi
- **PENDING_REVIEW** - Đang chờ xem xét từ cảng vụ
- **CHANGES_REQUESTED** - Cảng vụ yêu cầu thay đổi
- **APPROVED** - Đã được phê duyệt ✅
- **ISSUED** - Đã cấp phép
- **REVOKED** - Đã bị thu hồi
- **PENDING_QLC/PENDING_BP** - Trạng thái cũ (lịch sử)

### Tạo Khai Báo Mới

#### **Bước 1: Khởi Động Wizard**
1. Nhấn nút **"Tạo Khai Báo"** hoặc **"➕ Khai Báo Mới"**
2. Wizard (trợ thủ hình ảnh) sẽ xuất hiện

#### **Bước 2: Chọn Tàu**
- Chọn tàu từ danh sách thả xuống
- **Tính năng Auto-Suggest**: Nếu tàu này đã có khai báo trước đó, các thông tin sẽ được tự động điền lại
- Nhấn **"Tiếp Theo"** (Next)

#### **Bước 3: Chọn Thuyền Viên**
- Danh sách thuyền viên sẽ xuất hiện
- Chọn thuyền viên cho chuyến này
- Có thể thêm thuyền viên mới nếu cần bằng cách nhấn **"Thêm Thuyền Viên"**
- Nhấn **"Tiếp Theo"** (Next)

#### **Bước 4: Nhập Thông Tin Khai Báo**
Điền các thông tin về cảng, hàng hóa, hành khách:
- **Cảng đến/Từ** (Port Arrival/Departure)
- **Ngày/Giờ** (Date & Time)
- **Loại hàng hóa** (Cargo Type)
- **Số lượng hành khách** (Number of Passengers)
- **Ghi chú** (Notes)

#### **Bước 5: Xem Lại & Gửi**
- Kiểm tra lại tất cả thông tin
- Nhấn **"Gửi"** (Submit) để gửi khai báo
- Hoặc nhấn **"Lưu Nháp"** (Save Draft) để lưu và sửa sau

### Chỉnh Sửa Khai Báo

**Chỉ có thể chỉnh sửa khai báo ở trạng thái DRAFT hoặc CHANGES_REQUESTED**

1. Nhấn vào khai báo cần chỉnh sửa
2. Nhấn nút **"Chỉnh Sửa"**
3. Cập nhật thông tin
4. Nhấn **"Cập Nhật"** hoặc gửi lại

### Xem Chi Tiết Khai Báo

1. Nhấn vào một khai báo từ danh sách
2. Bạn sẽ thấy:
   - Tất cả thông tin chi tiết
   - Danh sách thuyền viên tham gia
   - Lịch sử thay đổi (Declaration Events)
   - Tệp đính kèm (nếu có)

---

## Báo Cáo (Reports)

### Xem Báo Cáo

1. Nhấn vào **"BÁO CÁO"** trong menu trên cùng
2. Chọn **khoảng thời gian** để báo cáo:
   - Ngày bắt đầu (From Date)
   - Ngày kết thúc (To Date)
3. Nhấn **"Tạo Báo Cáo"** (Generate Report)

### Nội Dung Báo Cáo

Báo cáo bao gồm **ba phần chính**:

#### **Phần I: Danh Sách Khai Báo (Appendix 1)**
- Chi tiết từng khai báo trong khoảng thời gian
- Tên tàu, ngày, cảng, hàng hóa

#### **Phần II: Thống Kê Tổng Hợp (Appendix 2)**
- Tổng số tàu đến/đi
- Phân loại hàng hóa
- Số lượng hành khách

#### **Phần III: Chi Tiết Vận Động (Appendix 3)**
- Từng bản ghi chi tiết theo loại vận động (hàng hóa vào/ra, hành khách)

### Lưu Báo Cáo

- Báo cáo có thể được **xuất ra Excel** hoặc **in ra PDF**
- Nhấn nút **"Xuất Excel"** hoặc **"In"** để tải về

### Lưu Ý

- **Chỉ báo cáo các khai báo đã được phê duyệt** (APPROVED hoặc ISSUED status)
- Khai báo dưới dạng DRAFT không được bao gồm trong báo cáo

---

## Các Mẹo & Thủ Thuật

### 💡 Mẹo 1: Tính Năng Auto-Suggest
Khi bạn chọn một tàu đã có khai báo trước đó:
- Các thông tin như hàng hóa, cảng, thuyền viên sẽ được **tự động điền lại**
- Bạn chỉ cần kiểm tra và cập nhật những thông tin thay đổi
- Điều này **tiết kiệm thời gian** đáng kể

### 💡 Mẹo 2: Lưu Nháp
- Luôn lưu khai báo nháp trước khi gửi
- Nếu bạn quên thông tin gì, có thể quay lại sửa
- Sau khi gửi, chỉ có thể sửa nếu cảng vụ yêu cầu thay đổi

### 💡 Mẹo 3: Kiểm Tra Chứng Chỉ Thường Xuyên
- Vào **Dashboard** để xem cảnh báo chứng chỉ
- Cập nhật ngày hết hạn chứng chỉ thuyền viên kịp thời
- Tránh tình trạng thuyền viên không thể làm việc vì chứng chỉ hết hạn

### 💡 Mẹo 4: Phân Loại Khai Báo
- Sử dụng bộ lọc (Filter) để tìm khai báo nhanh chóng
- Lọc theo trạng thái, tàu, hoặc ngày khai báo

### 💡 Mẹo 5: Yêu Cầu Thay Đổi
Nếu cảng vụ yêu cầu thay đổi (CHANGES_REQUESTED):
- Bạn sẽ thấy thông báo yêu cầu
- Quay lại sửa khai báo theo yêu cầu
- Gửi lại khai báo để được xem xét

### 💡 Mẹo 6: Tệp Đính Kèm
- Bạn có thể đính kèm các tài liệu (PDF, hình ảnh, Excel)
- Những tài liệu này là bằng chứng cho khai báo
- Đảm bảo tệp được quét sạch virus trước khi tải lên

---

## ❓ Câu Hỏi Thường Gặp (FAQ)

### **Q: Tôi quên mật khẩu phải làm sao?**
A: Liên hệ với quản trị viên hệ thống hoặc bộ phận IT để đặt lại mật khẩu.

### **Q: Tôi có thể xóa một khai báo không?**
A: Không thể xóa hoàn toàn. Bạn chỉ có thể lưu nháp và không gửi, hoặc liên hệ quản trị viên.

### **Q: Khai báo của tôi gửi lên rồi nhưng vẫn là DRAFT?**
A: Thử làm mới trang (F5) hoặc đóng/mở lại trình duyệt. Nếu vẫn có vấn đề, hãy liên hệ bộ phận IT.

### **Q: Tôi có thể xem lịch sử thay đổi khai báo không?**
A: Có, vào chi tiết khai báo, bạn sẽ thấy phần "Lịch Sử Thay Đổi" (Declaration Events) với tất cả các lần cập nhật.

### **Q: Báo cáo bao gồm những khai báo nào?**
A: Chỉ khai báo ở trạng thái **APPROVED** hoặc **ISSUED** được bao gồm trong báo cáo. Các nháp và khai báo chưa được phê duyệt sẽ không xuất hiện.

### **Q: Tôi có thể chỉnh sửa khai báo đã gửi không?**
A: Tùy thuộc vào trạng thái:
- **DRAFT**: Có thể chỉnh sửa bất cứ lúc nào
- **PENDING_REVIEW**: Không thể chỉnh sửa (đang chờ xem xét)
- **CHANGES_REQUESTED**: Có thể chỉnh sửa theo yêu cầu
- **APPROVED/ISSUED**: Không thể chỉnh sửa

---

## 📞 Liên Hệ & Hỗ Trợ

Nếu bạn gặp vấn đề hoặc có câu hỏi:
- **Email**: thanh_long081@yahoo.com
- **Bộ Phận IT**: Liên hệ quản trị viên hệ thống

---

**Cảm ơn bạn đã sử dụng Port Declaration System!** 🎉
