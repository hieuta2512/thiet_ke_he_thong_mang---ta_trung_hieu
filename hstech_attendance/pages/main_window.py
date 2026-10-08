# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QPushButton, QStackedWidget, QButtonGroup, QFrame,
                              QLineEdit, QMessageBox, QFormLayout, QSpinBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import db
from pages.dashboard import DashboardPage, EmployeeHomePage
from pages.attendance import AttendancePage
from pages.employees import EmployeesPage
from pages.history import HistoryPage
from pages.reports import ReportsPage
from face_engine import FaceEngine

NAV_ADMIN = [
    ("🏠", "Trang chủ"),
    ("⏱", "Chấm công"),
    ("👤", "Nhân viên"),
    ("📜", "Lịch sử"),
    ("📊", "Báo cáo"),
    ("⚙", "Cài đặt"),
]

NAV_EMPLOYEE = [
    ("🏠", "Trang chủ"),
    ("⏱", "Chấm công"),
    ("📜", "Lịch sử"),
    ("🧾", "Bảng chấm công"),
    ("⚙", "Cài đặt"),
]


class MainWindow(QMainWindow):
    def __init__(self, user, logout_callback):
        super().__init__()
        self.user = user
        self.is_admin = user.get("role") == "admin"
        self.logout_callback = logout_callback
        self.setWindowTitle("HSTech - Hệ thống chấm công nhân viên")
        self.resize(1300, 800)
        self.engine = FaceEngine()
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_l = QVBoxLayout(sidebar)
        side_l.setContentsMargins(0, 0, 0, 0)
        side_l.setSpacing(2)

        brand = QLabel("◆ HSTech")
        brand.setObjectName("sidebarTitle")
        side_l.addWidget(brand)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.pages = {}
        self.stack = QStackedWidget()

        if self.is_admin:
            nav_items = NAV_ADMIN
            page_map = [
                ("Trang chủ", DashboardPage(self.user, lambda: self._select_by_name("Lịch sử"))),
                ("Chấm công", AttendancePage(self.engine)),
                ("Nhân viên", EmployeesPage(self.engine)),
                ("Lịch sử", HistoryPage()),
                ("Báo cáo", ReportsPage()),
                ("Cài đặt", self._build_settings_page()),
            ]
        else:
            # Tài khoản nhân viên: chỉ xem dữ liệu của chính mình, không có
            # quyền vào Quản lý nhân viên / Báo cáo.
            nav_items = NAV_EMPLOYEE
            page_map = [
                ("Trang chủ", EmployeeHomePage(self.user, lambda: self._select_by_name("Chấm công"))),
                ("Chấm công", AttendancePage(self.engine)),
                ("Lịch sử", HistoryPage(fixed_ma_nv=self.user.get("ma_nv"))),
                ("Bảng chấm công", ReportsPage(fixed_ma_nv=self.user.get("ma_nv"),
                                               personal_title="Bảng chấm công của tôi")),
                ("Cài đặt", self._build_settings_page()),
            ]

        for (icon, label), (name, widget) in zip(nav_items, page_map):
            btn = QPushButton(f"  {icon}   {label}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, n=name: self._select_by_name(n))
            self.nav_group.addButton(btn)
            side_l.addWidget(btn)
            self.pages[name] = (btn, widget)
            self.stack.addWidget(widget)

        side_l.addStretch()
        root.addWidget(sidebar)

        # Right side: topbar + stack
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topBar")
        topbar.setFixedHeight(56)
        top_l = QHBoxLayout(topbar)
        top_l.addStretch()
        role_text = "Admin" if self.is_admin else "Nhân viên"
        user_lbl = QLabel(f"👤 {self.user.get('full_name', '')} ({role_text})")
        user_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        top_l.addWidget(user_lbl)
        logout_btn = QPushButton("Đăng xuất")
        logout_btn.setObjectName("ghostBtn")
        logout_btn.clicked.connect(self.logout_callback)
        top_l.addWidget(logout_btn)
        right.addWidget(topbar)

        content_wrap = QWidget()
        content_wrap.setObjectName("contentArea")
        content_l = QVBoxLayout(content_wrap)
        content_l.setContentsMargins(0, 0, 0, 0)
        content_l.addWidget(self.stack)
        right.addWidget(content_wrap, 1)

        right_widget = QWidget()
        right_widget.setLayout(right)
        root.addWidget(right_widget, 1)

        self._select_by_name("Trang chủ")

    def _build_settings_page(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(16)
        title = QLabel("Cài đặt")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        l.addWidget(title)

        # --- Đổi mật khẩu (mọi vai trò) ---
        pw_card = QFrame()
        pw_card.setObjectName("card")
        pw_l = QVBoxLayout(pw_card)
        pw_title = QLabel("Đổi mật khẩu đăng nhập")
        pw_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        pw_l.addWidget(pw_title)

        form = QFormLayout()
        old_pw = QLineEdit()
        old_pw.setEchoMode(QLineEdit.Password)
        new_pw = QLineEdit()
        new_pw.setEchoMode(QLineEdit.Password)
        confirm_pw = QLineEdit()
        confirm_pw.setEchoMode(QLineEdit.Password)
        form.addRow("Mật khẩu hiện tại", old_pw)
        form.addRow("Mật khẩu mới", new_pw)
        form.addRow("Nhập lại mật khẩu mới", confirm_pw)
        pw_l.addLayout(form)

        def do_change_password():
            if not old_pw.text() or not new_pw.text():
                QMessageBox.warning(w, "Thiếu thông tin", "Vui lòng nhập đầy đủ các trường.")
                return
            if new_pw.text() != confirm_pw.text():
                QMessageBox.warning(w, "Không khớp", "Mật khẩu mới nhập lại không khớp.")
                return
            ok = db.change_password(self.user["username"], old_pw.text(), new_pw.text())
            if ok:
                QMessageBox.information(w, "Thành công", "Đã đổi mật khẩu. Lần đăng nhập sau hãy dùng mật khẩu mới.")
                old_pw.clear(); new_pw.clear(); confirm_pw.clear()
            else:
                QMessageBox.warning(w, "Sai mật khẩu", "Mật khẩu hiện tại không đúng.")

        change_btn = QPushButton("Đổi mật khẩu")
        change_btn.setObjectName("primaryBtn")
        change_btn.clicked.connect(do_change_password)
        pw_l.addWidget(change_btn)
        l.addWidget(pw_card)

        if self.is_admin:
            info_card = QFrame()
            info_card.setObjectName("card")
            info_l = QVBoxLayout(info_card)
            info_title = QLabel("Thông tin hệ thống")
            info_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
            info_l.addWidget(info_title)
            info = QLabel(
                "• Mỗi nhân viên khi được thêm sẽ tự có 1 tài khoản đăng nhập "
                "(tên đăng nhập = mã NV, mật khẩu mặc định = mã NV).\n"
                "• Giờ hành chính: vào 08:00, về 17:00 — chấm vào sau 08:00 tính Đi muộn, "
                "chấm ra trước 17:00 tính Về sớm (chỉnh trong db.py → WORK_START_TIME / WORK_END_TIME).\n"
                "• Dữ liệu lưu tại thư mục data/, faces/, attendance_photos/, models/.")
            info.setStyleSheet("color:#64748B;")
            info.setWordWrap(True)
            info_l.addWidget(info)
            l.addWidget(info_card)

            # --- Độ khắt khe nhận diện khuôn mặt ---
            face_card = QFrame()
            face_card.setObjectName("card")
            face_l = QVBoxLayout(face_card)
            face_title = QLabel("Độ khắt khe nhận diện khuôn mặt")
            face_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
            face_l.addWidget(face_title)
            face_desc = QLabel(
                "Nếu hệ thống hay nhận NHẦM người khác (hoặc nhận cả ảnh chụp lại) là nhân "
                "viên đã đăng ký: giảm 'Ngưỡng nhận diện' xuống và/hoặc tăng 'Số khung hình "
                "tối thiểu' lên. Nếu hệ thống khó nhận ra đúng người: làm ngược lại.")
            face_desc.setWordWrap(True)
            face_desc.setStyleSheet("color:#64748B;")
            face_l.addWidget(face_desc)

            face_form = QFormLayout()
            self.threshold_spin = QSpinBox()
            self.threshold_spin.setRange(30, 100)
            self.threshold_spin.setValue(int(db.get_setting("face_confidence_threshold", 45)))
            self.threshold_spin.setToolTip("Càng THẤP càng khắt khe (an toàn hơn, khó nhận nhầm "
                                            "nhưng cũng khó nhận đúng hơn). Khuyến nghị: 45–65.")
            face_form.addRow("Ngưỡng nhận diện (thấp = khắt khe hơn)", self.threshold_spin)

            self.votes_spin = QSpinBox()
            self.votes_spin.setRange(3, 15)
            self.votes_spin.setValue(int(db.get_setting("min_votes_to_accept", 6)))
            self.votes_spin.setToolTip("Số khung hình liên tiếp phải khớp cùng 1 người mới chấp "
                                        "nhận kết quả. Càng cao càng chắc chắn nhưng phản ứng chậm hơn.")
            face_form.addRow("Số khung hình tối thiểu để xác nhận", self.votes_spin)
            face_l.addLayout(face_form)

            def save_face_settings():
                db.set_setting("face_confidence_threshold", self.threshold_spin.value())
                db.set_setting("min_votes_to_accept", self.votes_spin.value())
                QMessageBox.information(
                    w, "Đã lưu",
                    "Đã lưu cài đặt nhận diện. Vào trang Chấm công, bấm Tắt camera rồi Bật lại "
                    "để áp dụng ngay.")

            save_face_btn = QPushButton("Lưu cài đặt nhận diện")
            save_face_btn.setObjectName("primaryBtn")
            save_face_btn.clicked.connect(save_face_settings)
            face_l.addWidget(save_face_btn)
            l.addWidget(face_card)

        l.addStretch()
        return w

    def _select_by_name(self, name):
        btn, widget = self.pages[name]
        btn.setChecked(True)
        self.stack.setCurrentWidget(widget)
