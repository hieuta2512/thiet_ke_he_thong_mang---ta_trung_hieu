# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
                              QPushButton, QCheckBox, QFrame, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import db


class LoginWindow(QWidget):
    def __init__(self, on_success):
        super().__init__()
        self.on_success = on_success
        self.setWindowTitle("HSTech - Đăng nhập")
        self.resize(1000, 620)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Left banner panel
        left = QFrame()
        left.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #0B1E3F, stop:1 #15305E);
        """)
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(50, 60, 50, 60)
        logo = QLabel("◆ HSTech")
        logo.setStyleSheet("color:white; font-size:26px; font-weight:800;")
        left_l.addWidget(logo)
        left_l.addStretch()
        tagline = QLabel("Kết nối con người\nKiến tạo tương lai")
        tagline.setStyleSheet("color:white; font-size:26px; font-weight:700;")
        left_l.addWidget(tagline)
        left_l.addStretch()
        quote = QLabel('"Một đội ngũ mạnh\nlà nền tảng cho thành công"')
        quote.setStyleSheet("color:#C7D2E3; font-size:13px; font-style:italic;")
        left_l.addWidget(quote)
        root.addWidget(left, 5)

        # Right form panel
        right = QFrame()
        right.setStyleSheet("background:white;")
        right_l = QVBoxLayout(right)
        right_l.setAlignment(Qt.AlignCenter)
        form = QVBoxLayout()
        form.setSpacing(12)
        form.setContentsMargins(80, 0, 80, 0)

        title = QLabel("HỆ THỐNG CHẤM CÔNG\nNHÂN VIÊN")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        title.setStyleSheet("color:#0B1E3F; margin-bottom: 18px;")
        form.addWidget(title)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Tên đăng nhập")
        self.user_edit.setText("admin")
        self.user_edit.setMinimumHeight(38)
        form.addWidget(self.user_edit)

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Mật khẩu")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setText("123456")
        self.pass_edit.setMinimumHeight(38)
        form.addWidget(self.pass_edit)

        remember = QCheckBox("Ghi nhớ đăng nhập")
        remember.setChecked(True)
        form.addWidget(remember)

        login_btn = QPushButton("Đăng nhập")
        login_btn.setObjectName("primaryBtn")
        login_btn.setMinimumHeight(42)
        login_btn.clicked.connect(self._do_login)
        form.addWidget(login_btn)
        self.pass_edit.returnPressed.connect(self._do_login)

        right_l.addLayout(form)
        hint = QLabel("Nhân viên đăng nhập bằng Mã NV (VD: NV001) và mật khẩu được cấp.")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#94A3B8; font-size:11px; margin-top:10px;")
        right_l.addWidget(hint)
        footer = QLabel("© 2026 HSTech. All rights reserved.")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color:#94A3B8; font-size:11px; margin-top:30px;")
        right_l.addWidget(footer)

        root.addWidget(right, 4)

    def _do_login(self):
        user = db.check_login(self.user_edit.text().strip(), self.pass_edit.text())
        if user:
            self.on_success(user)
        else:
            QMessageBox.warning(self, "Đăng nhập thất bại",
                                 "Sai tên đăng nhập hoặc mật khẩu.\n(Mặc định: admin / 123456)")
