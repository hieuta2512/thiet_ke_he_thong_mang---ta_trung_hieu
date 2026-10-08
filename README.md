README -- HƯỚNG DẪN CHẠY ĐỒ ÁN

Đề tài

THIẾT KẾ HỆ THỐNG MẠNG LAN KẾT HỢP CAMERA IP CHO DOANH NGHIỆP

1. Giới thiệu

Đồ án xây dựng mô hình hệ thống mạng LAN cho doanh nghiệp, kết hợp hệ
thống camera IP nhằm phục vụ:

Kết nối Internet cho doanh nghiệp.

Kết nối các máy tính trong các phòng ban.

Phân chia mạng bằng VLAN.

Cấp phát địa chỉ IP.

Kết nối và quản lý hệ thống camera IP.

Kiểm tra khả năng kết nối và bảo mật giữa các mạng.

Sản phẩm mô phỏng chính được thực hiện trên Cisco Packet Tracer.

2. Yêu cầu phần mềm

Để chạy sản phẩm, máy tính cần cài:

Cisco Packet Tracer (khuyến nghị phiên bản 8.x hoặc tương
thích).

Hệ điều hành Windows 10/11 hoặc hệ điều hành hỗ trợ Cisco Packet
Tracer.

Không yêu cầu cài đặt cơ sở dữ liệu hoặc máy chủ Web.

3. Cấu trúc thư mục sản phẩm

Sau khi giải nén đồ án, các tệp chính gồm:

DO_AN_MANG_LAN_CAMERA_IP/
│
├── README.md
├── DO_AN_MANG_LAN_CAMERA_IP.pkt
├── SO_DO_MANG/
├── TAI_LIEU/
└── HINH_ANH/

Trong đó:

README.md: File hướng dẫn chạy và kiểm tra sản phẩm.

DO_AN_MANG_LAN_CAMERA_IP.pkt: File mô phỏng mạng Cisco Packet
Tracer.

SO_DO_MANG/: Các sơ đồ thiết kế hệ thống.

TAI_LIEU/: Báo cáo đồ án.

HINH_ANH/: Hình ảnh minh họa kết quả.

Nếu tên file trong thư mục thực tế khác tên trên, chỉ cần mở đúng file
có đuôi .pkt.

4. HƯỚNG DẪN CHẠY MÔ HÌNH

Bước 1 -- Mở file mô phỏng

Cài đặt và mở Cisco Packet Tracer.

Vào File → Open.

Chọn file:

DO_AN_MANG_LAN_CAMERA_IP.pkt

Chờ Packet Tracer tải toàn bộ mô hình.

Bước 2 -- Kiểm tra sơ đồ mạng

Sau khi mở file, kiểm tra các thành phần:

Router/Firewall.

Core Switch.

Switch các phòng ban.

Máy tính.

Server.

Access Point.

Khu vực mạng camera.

Mô hình tổng quát:

                    INTERNET
                       |
                ROUTER/FIREWALL
                       |
                  CORE SWITCH
              _________|_________
             |         |         |
          SWITCH     SWITCH    SWITCH PoE
             |         |         |
          PHÒNG BAN   WIFI     CAMERA
                                  |
                                 NVR

5. KIỂM TRA ĐỊA CHỈ IP

Trên máy tính trong Packet Tracer:

Click vào PC.

Chọn Desktop.

Chọn IP Configuration.

Kiểm tra địa chỉ IP, Subnet Mask và Default Gateway.

Các mạng được sử dụng:

VLAN      Chức năng      Địa chỉ mạng

VLAN 10   Ban giám đốc   192.168.10.0/24
VLAN 20   Nhân viên      192.168.20.0/24
VLAN 30   Server         192.168.30.0/24
VLAN 40   Camera         192.168.40.0/24
VLAN 50   Wi-Fi khách    192.168.50.0/24
VLAN 99   Quản trị       192.168.99.0/24

6. KIỂM TRA KẾT NỐI MẠNG

Cách 1 -- Dùng lệnh Ping

Chọn một PC.

Vào Desktop → Command Prompt.

Nhập:

ping 192.168.20.1

Nếu xuất hiện:

Reply from 192.168.20.1

thì kết nối thành công.

Có thể kiểm tra thêm:

ping 192.168.30.10
ping 192.168.40.10

Cách 2 -- Kiểm tra bằng Simulation

Chuyển từ Realtime sang Simulation.

Chọn Add Simple PDU.

Click máy gửi.

Click máy nhận.

Nhấn Auto Capture/Play.

Nếu gói tin truyền thành công giữa hai thiết bị thì hệ thống đã kết nối
đúng.

7. KIỂM TRA VLAN

Trên Switch, chọn:

CLI

Sau đó nhập:

enable
show vlan brief

Kiểm tra danh sách VLAN.

Kết quả cần có các VLAN:

VLAN 10
VLAN 20
VLAN 30
VLAN 40
VLAN 50
VLAN 99

Nếu các VLAN xuất hiện trong danh sách thì cấu hình VLAN đã được tạo.

8. KIỂM TRA ROUTING GIỮA CÁC VLAN

Trên thiết bị định tuyến, kiểm tra:

enable
show ip interface brief

Kiểm tra các interface/sub-interface đã có địa chỉ IP và trạng thái hoạt
động.

Có thể kiểm tra định tuyến bằng:

show ip route

Sau đó sử dụng PC ở các VLAN khác nhau để thực hiện ping.

Ví dụ:

ping 192.168.30.10

9. KIỂM TRA HỆ THỐNG CAMERA

Trong mô hình, camera được thiết kế trong:

VLAN 40 – CAMERA
Network: 192.168.40.0/24

Các camera mẫu có thể sử dụng dải:

192.168.40.101
192.168.40.102
192.168.40.103
...
192.168.40.116

Kiểm tra bằng cách:

Chọn thiết bị camera.

Kiểm tra địa chỉ IP.

Kiểm tra kết nối đến mạng camera.

Từ thiết bị quản lý, thực hiện ping đến địa chỉ camera.

Ví dụ:

ping 192.168.40.101

Nếu nhận được phản hồi thì camera đã kết nối vào mạng.

Lưu ý: Cisco Packet Tracer không mô phỏng đầy đủ chức năng ghi hình và
xem video của hệ thống camera IP thực tế. Phần camera trong đồ án được
thể hiện chủ yếu ở mức kiến trúc mạng, địa chỉ IP, VLAN và kết nối.
Việc ghi hình được mô tả bằng mô hình Camera IP → Switch PoE → Core
Switch → NVR trong báo cáo.

10. KIỂM TRA WI-FI

Trong mô hình có thể kiểm tra Access Point bằng cách:

Chọn thiết bị không dây.

Kiểm tra tên mạng Wi-Fi (SSID).

Kiểm tra kết nối của thiết bị đầu cuối.

Kiểm tra địa chỉ IP được cấp.

Thực hiện ping đến Gateway.

Mạng Wi-Fi khách sử dụng:

VLAN 50
192.168.50.0/24

Mạng khách được thiết kế để hạn chế truy cập vào các tài nguyên nội bộ.

11. QUY TRÌNH DEMO CHO GIẢNG VIÊN

Có thể trình bày sản phẩm theo thứ tự sau:

Bước 1

Mở file .pkt.

Bước 2

Giới thiệu sơ đồ tổng thể:

Internet
   ↓
Router/Firewall
   ↓
Core Switch
   ↓
Switch
   ↓
PC / Server / Wi-Fi / Camera

Bước 3

Giới thiệu các VLAN:

VLAN 10 -- Ban giám đốc.

VLAN 20 -- Nhân viên.

VLAN 30 -- Server.

VLAN 40 -- Camera.

VLAN 50 -- Wi-Fi khách.

VLAN 99 -- Quản trị.

Bước 4

Mở một PC → Desktop → Command Prompt.

Thực hiện:

ipconfig

để kiểm tra IP.

Bước 5

Thực hiện:

ping 192.168.20.1

để kiểm tra Gateway.

Bước 6

Kiểm tra VLAN trên Switch:

enable
show vlan brief

Bước 7

Kiểm tra camera:

ping 192.168.40.101

Bước 8

Chuyển sang Simulation Mode để minh họa đường đi của gói tin.

12. KẾT QUẢ MONG ĐỢI

Sau khi chạy và kiểm tra, hệ thống cần đạt các kết quả:

Các thiết bị trong cùng mạng có thể kết nối với nhau.

Các VLAN được tạo đúng.

Thiết bị nhận đúng địa chỉ IP.

Các Gateway hoạt động.

Các mạng được định tuyến theo thiết kế.

Mạng camera được tách riêng bằng VLAN 40.

Camera có thể kết nối tới hệ thống mạng.

Mạng khách được tách khỏi mạng nội bộ.

Mô hình có khả năng mở rộng thêm thiết bị.

13. XỬ LÝ LỖI THƯỜNG GẶP

Lỗi 1: Không mở được file .pkt

Kiểm tra:

Đã cài Cisco Packet Tracer chưa.

File có bị đổi phần mở rộng không.

Thử mở Cisco Packet Tracer trước rồi chọn File → Open.

Lỗi 2: Ping không thành công

Kiểm tra:

Địa chỉ IP.

Subnet Mask.

Default Gateway.

Cáp kết nối.

Trạng thái interface.

VLAN.

Cấu hình routing.

Lỗi 3: VLAN không hoạt động

Trên Switch chạy:

enable
show vlan brief

Kiểm tra VLAN cần thiết đã được tạo và cổng thiết bị đã được gán đúng
VLAN.

Lỗi 4: Interface bị tắt

Trên thiết bị mạng có thể sử dụng:

enable
configure terminal
interface <tên-interface>
no shutdown

Sau đó kiểm tra lại bằng:

show ip interface brief

14. LƯU Ý KHI NỘP VÀ DEMO

Không đổi tên hoặc xóa file .pkt.

Nên mở file mô phỏng trước khi thuyết trình để kiểm tra.

Kiểm tra Ping trước khi demo.

Đảm bảo Cisco Packet Tracer đã được cài đặt.

Báo cáo và file .pkt nên đặt cùng thư mục.

Nếu sử dụng máy tính khác, cần kiểm tra lại phiên bản Cisco Packet
Tracer.

15. TÓM TẮT SẢN PHẨM ĐẦU RA

Sản phẩm của đồ án gồm:

1. Báo cáo đồ án 4 chương

2. Sơ đồ hệ thống mạng LAN

3. File mô phỏng Cisco Packet Tracer (.pkt)

4. Thiết kế hệ thống Camera IP

5. Bảng địa chỉ IP và VLAN

6. Cấu hình và kiểm tra kết nối

7. Kết quả kiểm thử hệ thống

Người thực hiện

Đề tài: Thiết kế hệ thống mạng LAN kết hợp camera IP cho doanh
nghiệp.

Mục tiêu: Xây dựng và mô phỏng một hệ thống mạng doanh nghiệp có khả
năng kết nối, phân chia mạng, bảo mật và tích hợp camera IP.
