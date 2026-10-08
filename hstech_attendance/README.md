# HSTech - Hệ thống chấm công nhân viên (Python + OpenCV + PyQt5)

Ứng dụng desktop chấm công bằng nhận diện khuôn mặt, mô phỏng theo bản demo
giao diện HSTech gồm 8 màn hình: Đăng nhập, Trang chủ (Dashboard), Chấm công
bằng camera, Quản lý nhân viên, Thêm nhân viên (lưu ảnh khuôn mặt), Lịch sử
chấm công, Xem ảnh chấm công, Báo cáo/Xuất Excel.

## 1. Công nghệ sử dụng
- **Giao diện:** PyQt5 (tự vẽ theo theme navy/blue giống bản demo, không cần file ảnh/icon rời)
- **Nhận diện khuôn mặt:** OpenCV thuần (Haar Cascade để phát hiện khuôn mặt +
  LBPH — Local Binary Patterns Histograms — để nhận diện). Không cần dlib/face_recognition
  nên cài đặt nhẹ và nhanh hơn.
- **Cơ sở dữ liệu:** SQLite (file `data/hstech.db`, tự tạo khi chạy lần đầu)
- **Xuất báo cáo:** openpyxl (xuất file .xlsx có định dạng màu giống bản demo)

## 2. Cài đặt
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
```

## 3. Chạy ứng dụng
```bash
python main.py
```
Tài khoản đăng nhập mặc định: **admin / 123456**
(được tạo tự động trong SQLite ở lần chạy đầu tiên — bạn có thể đổi trong `db.py`)

Ứng dụng tự sinh sẵn 5 nhân viên demo (NV001–NV005) giống bản mockup để bạn
thấy ngay Dashboard, Quản lý nhân viên, Báo cáo có dữ liệu — nhưng các nhân
viên demo này **chưa có dữ liệu khuôn mặt** nên camera sẽ chưa nhận diện được
họ. Để nhận diện thật, bạn cần thêm nhân viên mới và chụp ảnh khuôn mặt (xem mục 4).

## 4. Quy trình sử dụng
1. **Đăng nhập** ở màn hình đầu tiên.
2. Vào **Nhân viên → + Thêm nhân viên**: điền thông tin, bấm **Bật camera**,
   nhìn thẳng vào camera và bấm **Chụp ảnh** ~15 lần ở nhiều góc mặt khác
   nhau (nghiêng trái/phải/lên/xuống nhẹ) để tăng độ chính xác nhận diện,
   sau đó bấm **Lưu** — hệ thống sẽ tự huấn luyện lại mô hình LBPH.
3. Vào **Chấm công**, bấm **Bật camera**. Khi hệ thống nhận ra khuôn mặt đã
   đăng ký, thông tin nhân viên hiện bên phải → bấm **Chấm công vào** /
   **Chấm công ra**. Ảnh chụp lúc chấm công được lưu vào `attendance_photos/`.
4. **Trang chủ**: xem thống kê tổng quan, biểu đồ tròn tình trạng, hoạt động
   gần đây theo thời gian thực (đồng hồ chạy trực tiếp).
5. **Lịch sử chấm công**: lọc theo ngày/nhân viên/trạng thái, bấm **Xem** để
   mở ảnh chấm công vào/ra.
6. **Báo cáo**: chọn tháng/phòng ban → **⬇ Xuất Excel** để tải file .xlsx.

## 5. Cấu trúc thư mục
```
hstech_attendance/
├── main.py              # điểm khởi chạy
├── db.py                # SQLite: nhân viên, chấm công, tài khoản
├── face_engine.py        # phát hiện + nhận diện khuôn mặt (OpenCV)
├── style.py              # theme màu / QSS
├── pages/
│   ├── login.py           # Màn 1: Đăng nhập
│   ├── main_window.py      # Sidebar + khung chứa các trang
│   ├── dashboard.py        # Màn 2: Trang chủ
│   ├── attendance.py       # Màn 3: Chấm công camera
│   ├── employees.py        # Màn 4: Quản lý nhân viên
│   ├── add_employee.py     # Màn 5: Thêm/sửa nhân viên + chụp khuôn mặt
│   ├── history.py          # Màn 6+7: Lịch sử & xem ảnh chấm công
│   └── reports.py          # Màn 8: Báo cáo & xuất Excel
├── widgets/
│   ├── stat_card.py        # thẻ số liệu thống kê
│   └── donut_chart.py      # biểu đồ tròn vẽ bằng QPainter
├── faces/                # ảnh khuôn mặt từng nhân viên (train LBPH)
├── models/                # model LBPH đã huấn luyện (lbph_model.yml)
├── attendance_photos/     # ảnh chụp mỗi lần chấm công
└── data/hstech.db          # cơ sở dữ liệu SQLite
```

## 6. Tùy chỉnh nhanh
- Giờ vào ca / giờ tính "đi muộn": hàm `check_in()` trong `db.py` (mặc định 08:30).
- Ngưỡng nhận diện khuôn mặt (càng thấp càng khắt khe): `FaceEngine(confidence_threshold=75)`
  trong `pages/attendance.py` và `pages/main_window.py`.
- Danh sách phòng ban / chức vụ: đầu file `pages/add_employee.py`.
- Toàn bộ màu sắc giao diện: `style.py`.

## 7. Lưu ý
- Cần webcam hoạt động; nếu máy có nhiều camera, đổi `cv2.VideoCapture(0)`
  thành chỉ số camera khác trong `attendance.py` / `add_employee.py`.
- LBPH nhận diện tốt nhất khi mỗi nhân viên có 15–30 ảnh mặt ở nhiều điều
  kiện ánh sáng/góc độ khác nhau.
- Đây là bản mô phỏng phục vụ học tập/demo nội bộ — nếu triển khai thực tế
  cho công ty, nên bổ sung mã hóa mật khẩu mạnh hơn, phân quyền người dùng,
  và cân nhắc dùng mô hình nhận diện khuôn mặt hiện đại hơn (deep learning)
  nếu cần độ chính xác cao với số lượng nhân viên lớn.
