# -*- coding: utf-8 -*-
import os
import cv2
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
                              QPushButton, QComboBox, QDateEdit, QMessageBox, QFileDialog,
                              QFormLayout)
from PyQt5.QtCore import Qt, QTimer, QDate
from PyQt5.QtGui import QImage, QPixmap, QFont

import db
from face_engine import FaceEngine

DEPARTMENTS = ["Kế toán", "IT", "Nhân sự", "Kinh doanh", "Marketing", "Sản xuất"]
POSITIONS = ["Nhân viên", "Developer", "Trưởng phòng", "Quản lý", "Thực tập sinh"]
STATUSES = ["Đang làm", "Nghỉ phép", "Đã nghỉ việc"]
NEEDED_SAMPLES = 20      # số ảnh khuyến nghị để nhận diện chính xác, đa dạng góc mặt
MIN_SAMPLES_WARN = 8     # dưới mức này sẽ cảnh báo trước khi lưu (nhân viên mới)

CAPTURE_ERROR_MSG = {
    "no_face": "Không thấy khuôn mặt nào trong khung hình. Vui lòng nhìn thẳng vào camera.",
    "multiple_faces": "Phát hiện hơn 1 khuôn mặt trong khung hình. Chỉ để 1 người trong khung rồi chụp lại.",
    "too_small": "Khuôn mặt trong khung hình quá nhỏ. Hãy ngồi gần camera hơn.",
    "blurry": "Ảnh bị mờ/rung. Giữ yên và chụp lại cho rõ nét.",
}


class AddEmployeeDialog(QDialog):
    def __init__(self, engine: FaceEngine, parent=None, employee=None):
        super().__init__(parent)
        self.engine = engine
        self.editing = employee is not None
        self.employee = employee
        self.cap = None
        self.captured = 0
        self.setWindowTitle("Sửa nhân viên" if self.editing else "Thêm nhân viên")
        self.resize(760, 520)
        self._build_ui()
        if self.editing:
            self._fill_form(employee)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

    def _build_ui(self):
        root = QHBoxLayout(self)

        form_box = QVBoxLayout()
        title = QLabel("Thêm nhân viên" if not self.editing else "Sửa nhân viên")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        form_box.addWidget(title)

        form = QFormLayout()
        self.ma_nv_edit = QLineEdit(db.next_ma_nv())
        if self.editing:
            self.ma_nv_edit.setReadOnly(True)
        self.ho_ten_edit = QLineEdit()
        self.ngay_sinh_edit = QDateEdit(calendarPopup=True)
        self.ngay_sinh_edit.setDate(QDate(2000, 1, 1))
        self.sdt_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phong_ban_combo = QComboBox()
        self.phong_ban_combo.addItems(DEPARTMENTS)
        self.chuc_vu_combo = QComboBox()
        self.chuc_vu_combo.addItems(POSITIONS)
        self.ngay_vao_edit = QDateEdit(calendarPopup=True)
        self.ngay_vao_edit.setDate(QDate.currentDate())
        self.trang_thai_combo = QComboBox()
        self.trang_thai_combo.addItems(STATUSES)

        form.addRow("Mã NV *", self.ma_nv_edit)
        form.addRow("Họ và tên *", self.ho_ten_edit)
        form.addRow("Ngày sinh", self.ngay_sinh_edit)
        form.addRow("Số điện thoại", self.sdt_edit)
        form.addRow("Email", self.email_edit)
        form.addRow("Phòng ban", self.phong_ban_combo)
        form.addRow("Chức vụ", self.chuc_vu_combo)
        form.addRow("Ngày vào làm", self.ngay_vao_edit)
        form.addRow("Trạng thái", self.trang_thai_combo)
        form_box.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Lưu")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.setObjectName("ghostBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        form_box.addLayout(btn_row)
        root.addLayout(form_box, 3)

        # Face capture panel
        face_box = QVBoxLayout()
        face_title = QLabel("Ảnh khuôn mặt")
        face_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        face_box.addWidget(face_title)

        self.cam_label = QLabel("Camera chưa bật")
        self.cam_label.setFixedSize(260, 260)
        self.cam_label.setAlignment(Qt.AlignCenter)
        self.cam_label.setStyleSheet("background:#0B1E3F; color:white; border-radius:10px;")
        face_box.addWidget(self.cam_label, alignment=Qt.AlignHCenter)

        self.progress_lbl = QLabel(f"Đã chụp: 0/{NEEDED_SAMPLES}")
        self.progress_lbl.setAlignment(Qt.AlignHCenter)
        face_box.addWidget(self.progress_lbl)

        hint_lbl = QLabel("Chụp nhiều góc: nhìn thẳng, nghiêng trái/phải, hơi cúi/ngẩng, "
                           "để nhận diện chính xác và tránh nhận nhầm người khác.")
        hint_lbl.setWordWrap(True)
        hint_lbl.setStyleSheet("color:#64748B; font-size:11px;")
        face_box.addWidget(hint_lbl)

        cam_toggle_btn = QPushButton("Bật camera")
        cam_toggle_btn.setObjectName("ghostBtn")
        cam_toggle_btn.clicked.connect(self._toggle_camera)
        face_box.addWidget(cam_toggle_btn)

        capture_btn = QPushButton("Chụp ảnh")
        capture_btn.setObjectName("primaryBtn")
        capture_btn.clicked.connect(self._capture_face)
        face_box.addWidget(capture_btn)

        choose_btn = QPushButton("Chọn ảnh")
        choose_btn.setObjectName("ghostBtn")
        choose_btn.clicked.connect(self._choose_image)
        face_box.addWidget(choose_btn)

        face_box.addStretch()
        root.addLayout(face_box, 2)

    def _fill_form(self, emp):
        self.ho_ten_edit.setText(emp["ho_ten"])
        self.sdt_edit.setText(emp.get("sdt") or "")
        self.email_edit.setText(emp.get("email") or "")
        if emp.get("phong_ban") in DEPARTMENTS:
            self.phong_ban_combo.setCurrentText(emp["phong_ban"])
        if emp.get("chuc_vu") in POSITIONS:
            self.chuc_vu_combo.setCurrentText(emp["chuc_vu"])
        if emp.get("trang_thai") in STATUSES:
            self.trang_thai_combo.setCurrentText(emp["trang_thai"])

    def _toggle_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "Lỗi", "Không tìm thấy camera.")
                self.cap = None
                return
            self.timer.start(30)
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.cam_label.setText("Camera chưa bật")

    def _update_frame(self):
        if self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok:
            return
        faces, _ = self.engine.detect_faces(frame)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (37, 99, 235), 2)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg).scaled(260, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cam_label.setPixmap(pix)
        self._last_frame = frame

    def _capture_face(self):
        ma_nv = self.ma_nv_edit.text().strip()
        if not ma_nv:
            QMessageBox.warning(self, "Thiếu thông tin", "Nhập Mã NV trước khi chụp ảnh.")
            return
        if self.cap is None or not hasattr(self, "_last_frame"):
            QMessageBox.warning(self, "Lỗi", "Bật camera trước khi chụp ảnh.")
            return
        result = self.engine.save_face_samples(ma_nv, self._last_frame, self.captured)
        if result == "ok":
            self.captured += 1
            self.progress_lbl.setText(f"Đã chụp: {self.captured}/{NEEDED_SAMPLES}")
        else:
            QMessageBox.information(self, "Chưa lưu được ảnh này",
                                     CAPTURE_ERROR_MSG.get(result, "Vui lòng thử lại."))

    def _choose_image(self):
        ma_nv = self.ma_nv_edit.text().strip()
        if not ma_nv:
            QMessageBox.warning(self, "Thiếu thông tin", "Nhập Mã NV trước.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh khuôn mặt", "",
                                               "Ảnh (*.jpg *.jpeg *.png)")
        if not path:
            return
        img = cv2.imread(path)
        if img is None:
            return
        result = self.engine.save_face_samples(ma_nv, img, self.captured)
        if result == "ok":
            self.captured += 1
            self.progress_lbl.setText(f"Đã chụp: {self.captured}/{NEEDED_SAMPLES}")
        else:
            QMessageBox.information(self, "Chưa lưu được ảnh này",
                                     CAPTURE_ERROR_MSG.get(result, "Vui lòng thử lại."))

    def _save(self):
        ma_nv = self.ma_nv_edit.text().strip()
        ho_ten = self.ho_ten_edit.text().strip()
        if not ma_nv or not ho_ten:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Mã NV và Họ tên.")
            return

        # Cảnh báo nếu nhân viên MỚI có quá ít ảnh khuôn mặt -> dễ bị nhận
        # nhầm với người khác khi chấm công thật.
        if not self.editing and self.captured < MIN_SAMPLES_WARN:
            confirm = QMessageBox.question(
                self, "Ảnh khuôn mặt còn ít",
                f"Bạn mới chụp {self.captured}/{NEEDED_SAMPLES} ảnh. Chụp quá ít ảnh (đặc biệt "
                f"nếu chỉ có 1 góc mặt) sẽ khiến hệ thống DỄ NHẬN NHẦM với người khác khi chấm "
                f"công thật.\n\nBạn có muốn quay lại chụp thêm không? (Chọn 'No' để vẫn lưu.)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if confirm == QMessageBox.Yes:
                return

        data = {
            "ma_nv": ma_nv,
            "ho_ten": ho_ten,
            "ngay_sinh": self.ngay_sinh_edit.date().toString("dd/MM/yyyy"),
            "sdt": self.sdt_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "phong_ban": self.phong_ban_combo.currentText(),
            "chuc_vu": self.chuc_vu_combo.currentText(),
            "ngay_vao_lam": self.ngay_vao_edit.date().toString("dd/MM/yyyy"),
            "trang_thai": self.trang_thai_combo.currentText(),
        }
        if self.editing:
            db.update_employee(ma_nv, data)
            if db.has_account(ma_nv):
                db.create_employee_account(ma_nv, ho_ten)  # đồng bộ lại họ tên nếu có sửa
        else:
            existing = db.get_employee(ma_nv)
            if existing:
                QMessageBox.warning(self, "Trùng mã", "Mã nhân viên đã tồn tại.")
                return
            data["label_id"] = db.next_label_id()
            db.add_employee(data)
            # Tự động tạo tài khoản đăng nhập cho nhân viên (username = mã NV,
            # mật khẩu mặc định = mã NV) để họ tự đăng nhập xem chấm công của mình.
            username, plain_password = db.create_employee_account(ma_nv, ho_ten)

        # huấn luyện lại model nếu có ảnh khuôn mặt mới, và kiểm tra chất
        # lượng nhận diện ngay sau khi huấn luyện để cảnh báo sớm nếu có
        # nhân viên nào dễ bị nhận nhầm (kể cả những người đã thêm trước đó,
        # vì dữ liệu mới có thể làm mô hình khó phân biệt hơn).
        quality_warning = ""
        if self.captured > 0:
            employees = db.get_employees()
            label_map = {e["ma_nv"]: e["label_id"] for e in employees}
            self.engine.train(label_map)
            results = self.engine.self_test(label_map)
            weak = [(ma, r) for ma, r in results.items() if r[2] < 70]
            if weak:
                lines = "\n".join(f"- {ma}: nhận đúng {r[0]}/{r[1]} ảnh ({r[2]}%)" for ma, r in weak)
                quality_warning = (
                    "\n\n⚠️ CẢNH BÁO chất lượng nhận diện — những nhân viên sau có tỉ lệ tự nhận "
                    f"diện thấp, dễ bị nhận nhầm với người khác:\n{lines}\n\nNên chụp lại thêm ảnh "
                    "cho những người này (đủ sáng, nhiều góc mặt khác nhau, không đeo khẩu trang/kính râm).")

        if self.cap is not None:
            self.timer.stop()
            self.cap.release()
            self.cap = None

        if not self.editing:
            QMessageBox.information(
                self, "Đã tạo tài khoản nhân viên",
                f"Đã thêm nhân viên và tạo tài khoản đăng nhập:\n\n"
                f"Tên đăng nhập: {username}\nMật khẩu mặc định: {plain_password}\n\n"
                f"Hãy gửi thông tin này cho nhân viên và nhắc họ đổi mật khẩu "
                f"trong mục Cài đặt sau khi đăng nhập lần đầu.{quality_warning}")
        elif quality_warning:
            QMessageBox.warning(self, "Cảnh báo chất lượng nhận diện", quality_warning.strip())
        self.accept()

    def closeEvent(self, event):
        if self.cap is not None:
            self.timer.stop()
            self.cap.release()
        super().closeEvent(event)
