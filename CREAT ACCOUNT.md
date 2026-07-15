Để đăng nhập vào ứng dụng trong môi trường phát triển cục bộ (local dev), bạn sử dụng tài khoản thử nghiệm (demo) hoặc tự tạo tài khoản quản trị (admin). Chi tiết được quy định tại

docs/DEMO_DATA_POLICY.md
 như sau:

1. Tài khoản thử nghiệm (Demo)
Trước tiên, bạn cần khởi tạo dữ liệu mẫu vào cơ sở dữ liệu bằng cách chạy lệnh sau trong terminal:

powershell
python scripts/seed_demo_data.py
(Lưu ý: Lệnh này được định nghĩa tại file

scripts/seed_demo_data.py
)

Sau khi chạy lệnh seed thành công, bạn có thể sử dụng hai tài khoản mặc định dưới đây:

Vai trò (Role)	Tên đăng nhập (Username)	Mật khẩu mặc định (Password)
Khách hàng (Customer / Vessel owner)	khachhang	demo123
Nhân viên Cảng (Port employee)	nhanviencang	demo123
2. Tạo tài khoản quản trị hệ thống (Admin)
Nếu bạn cần một tài khoản có vai trò ADMIN, bạn có thể chạy kịch bản

scripts/bootstrap_admin.py
 bằng cách thiết lập các biến môi trường và thực thi lệnh:

powershell
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD="supersecurepassword"
python scripts/bootstrap_admin.py
(Thay thế admin và supersecurepassword bằng thông tin đăng nhập mong muốn của bạn).
