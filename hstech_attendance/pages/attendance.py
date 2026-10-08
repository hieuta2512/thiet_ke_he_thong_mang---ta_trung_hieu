# -*- coding: utf-8 -*-
import os
import cv2
from collections import deque, Counter
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
                              QPushButton, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap, QFont

import db
from face_engine import FaceEngine

ATT_PHOTOS_DIR = db.ATT_PHOTOS_DIR
HISTORY_LEN = 15          # số khung hình gần nhất dùng để "bỏ phiếu"
MIN_VOTES_TO_ACCEPT_DEFAULT = 6   # cần ít nhất bấy nhiêu khung khớp cùng 1 mã NV mới chốt kết quả


def cv_to_qpixmap(frame_bgr):
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg)


class AttendancePage(QWidget):
    def __init__(self, engine: FaceEngine = None):
        super().__init__()
        # Dùng chung 1 FaceEngine với các trang khác (Nhân viên) thay vì tạo
        # bản riêng — nếu không, model vừa huấn luyện ở trang Nhân viên sẽ
        # không được trang này biết tới.
        self.engine = engine or FaceEngine()
        self.cap = None
        self.current_ma_nv = None
        self.last_face_box = None
        # Đệm kết quả nhận diện của vài khung hình gần nhất để tránh nhấp
        # nháy "không nhận diện được" chỉ vì 1 frame bị mờ/lệch góc thoáng qua.
        self.match_history = deque(maxlen=HISTORY_LEN)
        self.min_votes = self._load_min_votes()
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Camera panel
        cam_card = QFrame()
        cam_card.setObjectName("card")
        cam_l = QVBoxLayout(cam_card)
        cam_title = QLabel("Camera trực tiếp")
        cam_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        cam_l.addWidget(cam_title)

        self.cam_label = QLabel()
        self.cam_label.setMinimumSize(480, 360)
        self.cam_label.setStyleSheet("background:#0B1E3F; border-radius:10px;")
        self.cam_label.setAlignment(Qt.AlignCenter)
        self.cam_label.setText("Camera chưa bật")
        self.cam_label.setStyleSheet("background:#0B1E3F; color:white; border-radius:10px;")
        self.cam_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cam_l.addWidget(self.cam_label, 1)

        cam_footer = QHBoxLayout()
        self.time_lbl = QLabel("--:--:--")
        cam_footer.addWidget(self.time_lbl)
        cam_footer.addStretch()
        self.recog_status_lbl = QLabel("Đang tìm khuôn mặt...")
        self.recog_status_lbl.setStyleSheet("color:#F59E0B; font-weight:600;")
        cam_footer.addWidget(self.recog_status_lbl)
        cam_l.addLayout(cam_footer)

        toggle_row = QHBoxLayout()
        self.toggle_btn = QPushButton("Bật camera")
        self.toggle_btn.setObjectName("primaryBtn")
        self.toggle_btn.clicked.connect(self.toggle_camera)
        toggle_row.addWidget(self.toggle_btn)
        cam_l.addLayout(toggle_row)
        root.addWidget(cam_card, 3)

        # Info panel
        info_card = QFrame()
        info_card.setObjectName("card")
        info_l = QVBoxLayout(info_card)
        info_title = QLabel("Thông tin nhân viên")
        info_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        info_l.addWidget(info_title)

        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(90, 90)
        self.avatar_lbl.setStyleSheet("background:#E2E8F0; border-radius:45px;")
        self.avatar_lbl.setAlignment(Qt.AlignCenter)
        info_l.addWidget(self.avatar_lbl, alignment=Qt.AlignHCenter)

        self.name_lbl = QLabel("—")
        self.name_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.name_lbl.setAlignment(Qt.AlignHCenter)
        info_l.addWidget(self.name_lbl)

        self.detail_lbl = QLabel("")
        self.detail_lbl.setAlignment(Qt.AlignHCenter)
        self.detail_lbl.setStyleSheet("color:#64748B;")
        info_l.addWidget(self.detail_lbl)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignHCenter)
        self.status_lbl.setStyleSheet("color:#2563EB; font-weight:700;")
        info_l.addWidget(self.status_lbl)

        info_l.addSpacing(10)
        btn_row = QHBoxLayout()
        self.in_btn = QPushButton("Chấm công vào")
        self.in_btn.setObjectName("greenBtn")
        self.in_btn.clicked.connect(self.do_check_in)
        self.out_btn = QPushButton("Chấm công ra")
        self.out_btn.setObjectName("redBtn")
        self.out_btn.clicked.connect(self.do_check_out)
        btn_row.addWidget(self.in_btn)
        btn_row.addWidget(self.out_btn)
        info_l.addLayout(btn_row)

        self.result_banner = QLabel("")
        self.result_banner.setWordWrap(True)
        self.result_banner.setAlignment(Qt.AlignCenter)
        self.result_banner.setStyleSheet(
            "background:#DCFCE7; color:#16A34A; border-radius:8px; padding:12px; font-weight:600;")
        self.result_banner.hide()
        info_l.addWidget(self.result_banner)
        info_l.addStretch()
        root.addWidget(info_card, 2)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

    @staticmethod
    def _load_min_votes():
        try:
            return int(db.get_setting("min_votes_to_accept", MIN_VOTES_TO_ACCEPT_DEFAULT))
        except Exception:
            return MIN_VOTES_TO_ACCEPT_DEFAULT

    def toggle_camera(self):
        if self.cap is None:
            # Luôn tải lại model + ngưỡng nhận diện mới nhất trước khi bắt đầu,
            # phòng trường hợp vừa thêm/sửa nhân viên hoặc đổi cài đặt ở trang khác.
            self.engine.reload()
            self.min_votes = self._load_min_votes()
            self.match_history.clear()
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.cam_label.setText("Không tìm thấy camera.\nKiểm tra kết nối webcam.")
                self.cap = None
                return
            self.timer.start(30)
            self.toggle_btn.setText("Tắt camera")
        else:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.cam_label.setText("Camera chưa bật")
            self.toggle_btn.setText("Bật camera")

    def _update_frame(self):
        if self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok:
            return
        ma_nv, box, conf = self.engine.recognize(frame)
        self.last_face_box = box
        if box is not None:
            x, y, w, h = box
            color = (22, 163, 74) if ma_nv else (37, 99, 235)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            self.match_history.append(ma_nv)  # ma_nv có thể là None (không khớp)
        else:
            self.match_history.clear()

        now = datetime.now()
        self.time_lbl.setText(now.strftime("%d/%m/%Y %H:%M:%S"))

        if box is None:
            # Không thấy mặt nào trong khung hình -> reset hẳn về trạng thái chờ
            self.current_ma_nv = None
            self._clear_employee()
            self.recog_status_lbl.setText("Đang tìm khuôn mặt...")
            self.recog_status_lbl.setStyleSheet("color:#F59E0B; font-weight:600;")
        else:
            stable_ma_nv = self._majority_match()
            if stable_ma_nv:
                if stable_ma_nv != self.current_ma_nv:
                    self.current_ma_nv = stable_ma_nv
                    self._show_employee(stable_ma_nv)
                else:
                    self.recog_status_lbl.setText("Nhận diện thành công")
                    self.recog_status_lbl.setStyleSheet("color:#16A34A; font-weight:600;")
            elif len(self.match_history) >= self.match_history.maxlen:
                # Đã đủ số khung hình để kết luận chắc chắn là không khớp ai cả
                self.current_ma_nv = None
                self._clear_employee()
                self.recog_status_lbl.setText("Không nhận diện được — thử lại")
                self.recog_status_lbl.setStyleSheet("color:#DC2626; font-weight:600;")
            else:
                # Đang thu thập thêm khung hình, chưa vội kết luận
                self.recog_status_lbl.setText("Đang nhận diện...")
                self.recog_status_lbl.setStyleSheet("color:#F59E0B; font-weight:600;")

        cv2.putText(frame, now.strftime("%d/%m/%Y %H:%M:%S"), (10, frame.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        pix = cv_to_qpixmap(frame).scaled(self.cam_label.width(), self.cam_label.height(),
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cam_label.setPixmap(pix)

    def _majority_match(self):
        """Trả về mã NV xuất hiện nhiều nhất trong các khung hình gần đây,
        nếu đạt đủ số phiếu tối thiểu (self.min_votes). Bỏ qua None."""
        votes = [m for m in self.match_history if m]
        if not votes:
            return None
        ma_nv, count = Counter(votes).most_common(1)[0]
        return ma_nv if count >= self.min_votes else None

    def _show_employee(self, ma_nv):
        emp = db.get_employee(ma_nv)
        if not emp:
            return
        self.recog_status_lbl.setText("Nhận diện thành công")
        self.recog_status_lbl.setStyleSheet("color:#16A34A; font-weight:600;")
        self.name_lbl.setText(emp["ho_ten"])
        self.detail_lbl.setText(
            f"Mã NV: {emp['ma_nv']}\nPhòng ban: {emp['phong_ban']}\nChức vụ: {emp['chuc_vu']}")
        att = db.get_today_attendance(ma_nv)
        if att and att["gio_ra"]:
            self.status_lbl.setText("Đã chấm công đủ hôm nay")
        elif att:
            self.status_lbl.setText("Đã chấm công vào")
        else:
            self.status_lbl.setText("Chưa chấm công hôm nay")

    def _clear_employee(self):
        self.name_lbl.setText("—")
        self.detail_lbl.setText("")
        self.status_lbl.setText("")

    def _save_snapshot(self, ma_nv, tag):
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok:
            return None
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(ATT_PHOTOS_DIR, f"{ma_nv}_{tag}_{ts}.jpg")
        cv2.imwrite(path, frame)
        return path

    def do_check_in(self):
        if not self.current_ma_nv:
            self._flash_banner("Chưa nhận diện được nhân viên.", ok=False)
            return
        photo = self._save_snapshot(self.current_ma_nv, "in")
        success, result = db.check_in(self.current_ma_nv, photo)
        if success:
            self._flash_banner(f"Chấm công thành công!\nThời gian: {result}", ok=True)
        else:
            self._flash_banner(result, ok=False)
        self._show_employee(self.current_ma_nv)

    def do_check_out(self):
        if not self.current_ma_nv:
            self._flash_banner("Chưa nhận diện được nhân viên.", ok=False)
            return
        photo = self._save_snapshot(self.current_ma_nv, "out")
        success, result = db.check_out(self.current_ma_nv, photo)
        if success:
            self._flash_banner(f"Chấm công ra thành công!\nThời gian: {result}", ok=True)
        else:
            self._flash_banner(result, ok=False)
        self._show_employee(self.current_ma_nv)

    def _flash_banner(self, text, ok=True):
        self.result_banner.setText(text)
        if ok:
            self.result_banner.setStyleSheet(
                "background:#DCFCE7; color:#16A34A; border-radius:8px; padding:12px; font-weight:600;")
        else:
            self.result_banner.setStyleSheet(
                "background:#FEE2E2; color:#DC2626; border-radius:8px; padding:12px; font-weight:600;")
        self.result_banner.show()

    def hideEvent(self, event):
        # tắt camera khi rời trang để tiết kiệm tài nguyên
        if self.cap is not None:
            self.timer.stop()
            self.cap.release()
            self.cap = None
            self.toggle_btn.setText("Bật camera")
            self.cam_label.setText("Camera chưa bật")
        super().hideEvent(event)
