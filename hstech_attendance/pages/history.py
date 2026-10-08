# -*- coding: utf-8 -*-
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                              QPushButton, QDateEdit, QTableWidget, QTableWidgetItem,
                              QHeaderView, QDialog)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QPixmap

import db


class PhotoDialog(QDialog):
    def __init__(self, title, path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ảnh chấm công")
        self.resize(360, 420)
        layout = QVBoxLayout(self)
        t = QLabel(title)
        t.setFont(QFont("Segoe UI", 11, QFont.Bold))
        layout.addWidget(t)
        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setMinimumSize(320, 320)
        img_lbl.setStyleSheet("background:#0B1E3F; border-radius:8px;")
        if path and os.path.exists(path):
            pix = QPixmap(path).scaled(320, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            img_lbl.setPixmap(pix)
        else:
            img_lbl.setText("Không có ảnh")
            img_lbl.setStyleSheet("background:#0B1E3F; color:white; border-radius:8px;")
        layout.addWidget(img_lbl)
        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("ghostBtn")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class HistoryPage(QWidget):
    def __init__(self, fixed_ma_nv=None):
        super().__init__()
        # fixed_ma_nv: nếu được truyền vào (tài khoản nhân viên), khóa bộ lọc
        # về đúng nhân viên đó, ẩn ô chọn "Nhân viên" để họ không xem được
        # lịch sử của người khác.
        self.fixed_ma_nv = fixed_ma_nv
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("Lịch sử chấm công")
        title.setFont(QFont("Segoe UI", 15, QFont.Bold))
        root.addWidget(title)

        filter_row = QHBoxLayout()
        self.tu_ngay = QDateEdit(calendarPopup=True)
        self.tu_ngay.setDate(QDate.currentDate().addMonths(-1))
        self.den_ngay = QDateEdit(calendarPopup=True)
        self.den_ngay.setDate(QDate.currentDate())
        self.nv_combo = QComboBox()
        self.trangthai_combo = QComboBox()
        self.trangthai_combo.addItems(["Tất cả", "Đúng giờ", "Đi muộn", "Về sớm", "Đi muộn & Về sớm"])

        filter_row.addWidget(QLabel("Từ ngày"))
        filter_row.addWidget(self.tu_ngay)
        filter_row.addWidget(QLabel("Đến ngày"))
        filter_row.addWidget(self.den_ngay)
        if not self.fixed_ma_nv:
            filter_row.addWidget(QLabel("Nhân viên"))
            filter_row.addWidget(self.nv_combo)
        filter_row.addWidget(QLabel("Trạng thái"))
        filter_row.addWidget(self.trangthai_combo)
        search_btn = QPushButton("Tìm kiếm")
        search_btn.setObjectName("primaryBtn")
        search_btn.clicked.connect(self.refresh)
        filter_row.addWidget(search_btn)
        root.addLayout(filter_row)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["STT", "Mã NV", "Họ tên", "Ngày", "Giờ vào", "Giờ ra", "Trạng thái",
             "Ảnh vào", "Ảnh ra"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.table)

    def refresh(self):
        self.nv_combo.blockSignals(True)
        current = self.nv_combo.currentText() if self.nv_combo.count() else "Tất cả"
        self.nv_combo.clear()
        self.nv_combo.addItem("Tất cả")
        for e in db.get_employees():
            self.nv_combo.addItem(e["ma_nv"])
        idx = self.nv_combo.findText(current)
        if idx >= 0:
            self.nv_combo.setCurrentIndex(idx)
        self.nv_combo.blockSignals(False)

        ma_nv_filter = self.fixed_ma_nv if self.fixed_ma_nv else self.nv_combo.currentText()
        rows = db.get_history(
            tu_ngay=self.tu_ngay.date().toPyDate() and self._qdate_to_dt(self.tu_ngay.date()),
            den_ngay=self._qdate_to_dt(self.den_ngay.date()),
            ma_nv=ma_nv_filter,
            trang_thai=self.trangthai_combo.currentText())

        self.table.setRowCount(0)
        for i, row in enumerate(rows, start=1):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(i)))
            self.table.setItem(r, 1, QTableWidgetItem(row["ma_nv"]))
            self.table.setItem(r, 2, QTableWidgetItem(row["ho_ten"]))
            self.table.setItem(r, 3, QTableWidgetItem(row["ngay"]))
            self.table.setItem(r, 4, QTableWidgetItem(row["gio_vao"] or "-"))
            self.table.setItem(r, 5, QTableWidgetItem(row["gio_ra"] or "-"))
            self.table.setItem(r, 6, QTableWidgetItem(row["trang_thai"] or ""))

            in_btn = QPushButton("Xem")
            in_btn.setObjectName("ghostBtn")
            in_btn.clicked.connect(
                lambda _, p=row["anh_vao"], n=row["ho_ten"]: self._show_photo(f"{n} - Ảnh vào", p))
            self.table.setCellWidget(r, 7, in_btn)

            out_btn = QPushButton("Xem")
            out_btn.setObjectName("ghostBtn")
            out_btn.clicked.connect(
                lambda _, p=row["anh_ra"], n=row["ho_ten"]: self._show_photo(f"{n} - Ảnh ra", p))
            self.table.setCellWidget(r, 8, out_btn)

    @staticmethod
    def _qdate_to_dt(qdate):
        from datetime import datetime
        return datetime(qdate.year(), qdate.month(), qdate.day())

    def _show_photo(self, title, path):
        PhotoDialog(title, path, self).exec_()
