# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                              QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QMessageBox, QDialog, QFormLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

import db
from pages.add_employee import AddEmployeeDialog, DEPARTMENTS, STATUSES


class AccountDialog(QDialog):
    """Xem / tạo / đặt lại mật khẩu tài khoản đăng nhập của 1 nhân viên."""

    def __init__(self, ma_nv, ho_ten, parent=None):
        super().__init__(parent)
        self.ma_nv = ma_nv
        self.ho_ten = ho_ten
        self.setWindowTitle(f"Tài khoản đăng nhập - {ho_ten}")
        self.resize(380, 220)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel(f"Tài khoản của {self.ho_ten} ({self.ma_nv})")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setWordWrap(True)
        layout.addWidget(title)

        exists = db.has_account(self.ma_nv)
        status = QLabel("✅ Đã có tài khoản." if exists else "⚠️ Chưa có tài khoản đăng nhập.")
        status.setStyleSheet(f"color:{'#16A34A' if exists else '#DC2626'}; font-weight:600;")
        layout.addWidget(status)

        form = QFormLayout()
        form.addRow("Tên đăng nhập", QLabel(self.ma_nv))
        self.new_pw = QLineEdit()
        self.new_pw.setPlaceholderText("Để trống = đặt về mặc định (mã NV)")
        form.addRow("Mật khẩu mới", self.new_pw)
        form_wrap = QWidget()
        form_wrap.setLayout(form)
        layout.addWidget(form_wrap)

        btn_text = "Đặt lại mật khẩu" if exists else "Tạo tài khoản"
        action_btn = QPushButton(btn_text)
        action_btn.setObjectName("primaryBtn")
        action_btn.clicked.connect(self._do_action)
        layout.addWidget(action_btn)

        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("ghostBtn")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def _do_action(self):
        pw = self.new_pw.text().strip() or self.ma_nv
        if db.has_account(self.ma_nv):
            db.reset_employee_password(self.ma_nv, pw)
        else:
            db.create_employee_account(self.ma_nv, self.ho_ten, pw)
        QMessageBox.information(
            self, "Đã lưu",
            f"Tên đăng nhập: {self.ma_nv}\nMật khẩu: {pw}\n\nHãy gửi thông tin này cho nhân viên.")
        self.accept()


class EmployeesPage(QWidget):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Danh sách nhân viên")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        bulk_btn = QPushButton("🔑 Tạo TK cho NV còn thiếu")
        bulk_btn.setObjectName("ghostBtn")
        bulk_btn.clicked.connect(self.bulk_create_accounts)
        header.addWidget(bulk_btn)

        check_btn = QPushButton("🔍 Kiểm tra chất lượng nhận diện")
        check_btn.setObjectName("ghostBtn")
        check_btn.clicked.connect(self.check_face_quality)
        header.addWidget(check_btn)

        add_btn = QPushButton("+ Thêm nhân viên")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.open_add_dialog)
        header.addWidget(add_btn)
        root.addLayout(header)

        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Tìm kiếm theo tên, mã nhân viên...")
        self.search_edit.textChanged.connect(self.refresh)
        filter_row.addWidget(self.search_edit, 2)

        self.dept_combo = QComboBox()
        self.dept_combo.addItems(["Tất cả phòng ban"] + DEPARTMENTS)
        self.dept_combo.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.dept_combo, 1)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Tất cả trạng thái"] + STATUSES)
        self.status_combo.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.status_combo, 1)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
            ["STT", "Mã NV", "Họ tên", "Phòng ban", "Chức vụ", "Ngày vào làm",
             "Trạng thái", "Tài khoản", "Sửa", "Xóa"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.table)

    def refresh(self):
        rows = db.get_employees(self.search_edit.text().strip(),
                                 self.dept_combo.currentText(),
                                 self.status_combo.currentText())
        self.table.setRowCount(0)
        for i, emp in enumerate(rows, start=1):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(i)))
            self.table.setItem(r, 1, QTableWidgetItem(emp["ma_nv"]))
            self.table.setItem(r, 2, QTableWidgetItem(emp["ho_ten"]))
            self.table.setItem(r, 3, QTableWidgetItem(emp["phong_ban"] or ""))
            self.table.setItem(r, 4, QTableWidgetItem(emp["chuc_vu"] or ""))
            self.table.setItem(r, 5, QTableWidgetItem(emp["ngay_vao_lam"] or ""))
            status_item = QTableWidgetItem("● " + (emp["trang_thai"] or ""))
            status_item.setForeground(QColor("#16A34A" if emp["trang_thai"] == "Đang làm" else "#F59E0B"))
            self.table.setItem(r, 6, status_item)

            has_acc = db.has_account(emp["ma_nv"])
            acc_btn = QPushButton("✅ TK" if has_acc else "⚠️ Tạo TK")
            acc_btn.setObjectName("ghostBtn")
            acc_btn.clicked.connect(lambda _, ma=emp["ma_nv"], ten=emp["ho_ten"]: self.open_account_dialog(ma, ten))
            self.table.setCellWidget(r, 7, acc_btn)

            edit_btn = QPushButton("Sửa")
            edit_btn.setObjectName("ghostBtn")
            edit_btn.clicked.connect(lambda _, ma=emp["ma_nv"]: self.open_edit_dialog(ma))
            self.table.setCellWidget(r, 8, edit_btn)

            del_btn = QPushButton("Xóa")
            del_btn.setStyleSheet("background:#FEE2E2; color:#DC2626; border-radius:6px; padding:4px 10px;")
            del_btn.clicked.connect(lambda _, ma=emp["ma_nv"]: self.delete_employee(ma))
            self.table.setCellWidget(r, 9, del_btn)

    def open_add_dialog(self):
        dlg = AddEmployeeDialog(self.engine, self)
        if dlg.exec_():
            self.refresh()

    def open_edit_dialog(self, ma_nv):
        emp = db.get_employee(ma_nv)
        dlg = AddEmployeeDialog(self.engine, self, employee=emp)
        if dlg.exec_():
            self.refresh()

    def open_account_dialog(self, ma_nv, ho_ten):
        dlg = AccountDialog(ma_nv, ho_ten, self)
        if dlg.exec_():
            self.refresh()

    def check_face_quality(self):
        employees = db.get_employees()
        label_map = {e["ma_nv"]: e["label_id"] for e in employees}
        if not self.engine.trained:
            QMessageBox.information(self, "Chưa có dữ liệu",
                                     "Chưa có nhân viên nào có ảnh khuôn mặt để kiểm tra.")
            return
        results = self.engine.self_test(label_map)
        if not results:
            QMessageBox.information(self, "Chưa có dữ liệu",
                                     "Chưa có nhân viên nào có ảnh khuôn mặt để kiểm tra.")
            return
        name_by_ma = {e["ma_nv"]: e["ho_ten"] for e in employees}
        weak = sorted([(ma, r) for ma, r in results.items() if r[2] < 70], key=lambda x: x[1][2])
        good = [(ma, r) for ma, r in results.items() if r[2] >= 70]
        lines = []
        if weak:
            lines.append("⚠️ DỄ BỊ NHẬN NHẦM — nên chụp lại thêm ảnh (đủ sáng, nhiều góc mặt):")
            for ma, r in weak:
                lines.append(f"  - {name_by_ma.get(ma, ma)} ({ma}): {r[0]}/{r[1]} ảnh nhận đúng ({r[2]}%)")
        else:
            lines.append("✅ Không có nhân viên nào có dấu hiệu dễ nhận nhầm.")
        lines.append(f"\nTổng: {len(good)}/{len(results)} nhân viên có chất lượng nhận diện tốt (≥70%).")
        QMessageBox.information(self, "Kết quả kiểm tra chất lượng nhận diện", "\n".join(lines))

    def bulk_create_accounts(self):
        missing = db.employees_without_account()
        if not missing:
            QMessageBox.information(self, "Đã đủ tài khoản",
                                     "Tất cả nhân viên đều đã có tài khoản đăng nhập.")
            return
        names = "\n".join(f"- {e['ma_nv']} ({e['ho_ten']})" for e in missing)
        confirm = QMessageBox.question(
            self, "Tạo tài khoản hàng loạt",
            f"Tạo tài khoản đăng nhập (mật khẩu mặc định = mã NV) cho {len(missing)} "
            f"nhân viên sau?\n\n{names}")
        if confirm != QMessageBox.Yes:
            return
        created = db.bulk_create_accounts()
        lines = "\n".join(f"{ma} / {pw}" for ma, ten, pw in created)
        QMessageBox.information(
            self, "Đã tạo tài khoản",
            f"Đã tạo {len(created)} tài khoản (Tên đăng nhập / Mật khẩu):\n\n{lines}\n\n"
            f"Hãy gửi thông tin đăng nhập cho từng nhân viên và nhắc họ đổi mật khẩu.")
        self.refresh()

    def delete_employee(self, ma_nv):
        confirm = QMessageBox.question(self, "Xác nhận xóa",
                                        f"Bạn có chắc muốn xóa nhân viên {ma_nv}?")
        if confirm == QMessageBox.Yes:
            db.delete_employee(ma_nv)
            self.refresh()
