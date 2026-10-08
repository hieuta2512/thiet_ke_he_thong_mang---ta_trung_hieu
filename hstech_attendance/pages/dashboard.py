# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                              QTableWidget, QTableWidgetItem, QHeaderView, QPushButton)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime
import db
from widgets.stat_card import StatCard
from widgets.donut_chart import DonutChart

WEEKDAYS_VN = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]


class DashboardPage(QWidget):
    def __init__(self, user, goto_history):
        super().__init__()
        self.user = user
        self.goto_history = goto_history
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        greet_box = QVBoxLayout()
        hello = QLabel(f"Xin chào, {self.user.get('full_name', 'Admin')}!")
        hello.setFont(QFont("Segoe UI", 18, QFont.Bold))
        sub = QLabel("Chúc bạn một ngày làm việc hiệu quả.")
        sub.setStyleSheet("color:#64748B;")
        greet_box.addWidget(hello)
        greet_box.addWidget(sub)
        header.addLayout(greet_box)
        header.addStretch()

        clock_box = QVBoxLayout()
        clock_box.setAlignment(Qt.AlignRight)
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("color:#64748B;")
        self.date_lbl.setAlignment(Qt.AlignRight)
        self.time_lbl = QLabel()
        self.time_lbl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.time_lbl.setAlignment(Qt.AlignRight)
        clock_box.addWidget(self.date_lbl)
        clock_box.addWidget(self.time_lbl)
        header.addLayout(clock_box)
        root.addLayout(header)

        # Stat cards
        cards_row = QHBoxLayout()
        self.card_total = StatCard("👥", "Tổng nhân viên", "0", "#2563EB")
        self.card_present = StatCard("✅", "Đang có mặt", "0", "#16A34A")
        self.card_late = StatCard("⏰", "Đi muộn", "0", "#F59E0B")
        self.card_absent = StatCard("🔴", "Vắng mặt", "0", "#DC2626")
        for c in (self.card_total, self.card_present, self.card_late, self.card_absent):
            cards_row.addWidget(c)
        root.addLayout(cards_row)

        # Middle: donut chart + activity table
        mid = QHBoxLayout()
        mid.setSpacing(16)

        donut_card = QFrame()
        donut_card.setObjectName("card")
        donut_l = QVBoxLayout(donut_card)
        donut_title = QLabel("Tình trạng nhân viên hôm nay")
        donut_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        donut_l.addWidget(donut_title)
        self.donut = DonutChart()
        donut_l.addWidget(self.donut)
        legend = QHBoxLayout()
        for text, color in [("Có mặt", "#16A34A"), ("Đi muộn", "#F59E0B"), ("Vắng mặt", "#DC2626")]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{color};")
            legend.addWidget(dot)
            legend.addWidget(QLabel(text))
        legend.addStretch()
        donut_l.addLayout(legend)
        mid.addWidget(donut_card, 2)

        activity_card = QFrame()
        activity_card.setObjectName("card")
        act_l = QVBoxLayout(activity_card)
        act_header = QHBoxLayout()
        act_title = QLabel("Hoạt động gần đây")
        act_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        act_header.addWidget(act_title)
        act_header.addStretch()
        view_all = QPushButton("Xem tất cả")
        view_all.setStyleSheet("border:none; color:#2563EB; font-weight:600;")
        view_all.setCursor(Qt.PointingHandCursor)
        view_all.clicked.connect(self.goto_history)
        act_header.addWidget(view_all)
        act_l.addLayout(act_header)

        self.activity_table = QTableWidget(0, 3)
        self.activity_table.setHorizontalHeaderLabels(["Thời gian", "Nhân viên", "Trạng thái"])
        self.activity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.activity_table.verticalHeader().setVisible(False)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        act_l.addWidget(self.activity_table)
        mid.addWidget(activity_card, 3)

        root.addLayout(mid, 1)

    def _tick(self):
        now = datetime.now()
        self.date_lbl.setText(f"{WEEKDAYS_VN[now.weekday()]}, {now.strftime('%d/%m/%Y')}")
        self.time_lbl.setText(now.strftime("%H:%M:%S"))

    def refresh(self):
        stats = db.get_today_stats()
        self.card_total.set_value(stats["total"])
        self.card_present.set_value(stats["present"])
        self.card_late.set_value(stats["late"])
        self.card_absent.set_value(stats["absent"])

        self.donut.set_data([
            (max(stats["present"] - stats["late"], 0), QColor("#16A34A"), "Có mặt"),
            (stats["late"], QColor("#F59E0B"), "Đi muộn"),
            (stats["absent"], QColor("#DC2626"), "Vắng mặt"),
        ], center_title=f"{stats['total']}\nNhân viên")

        activity = db.get_recent_activity(8)
        self.activity_table.setRowCount(0)
        for row in activity:
            r = self.activity_table.rowCount()
            self.activity_table.insertRow(r)
            self.activity_table.setItem(r, 0, QTableWidgetItem(row["gio_vao"] or ""))
            self.activity_table.setItem(r, 1, QTableWidgetItem(row["ho_ten"]))
            status_item = QTableWidgetItem("● Chấm công vào" if not row["gio_ra"] else "● Chấm công ra")
            status_item.setForeground(QColor("#16A34A"))
            self.activity_table.setItem(r, 2, status_item)

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)


class EmployeeHomePage(QWidget):
    """Trang chủ rút gọn dành cho tài khoản nhân viên: chỉ hiện thông tin và
    trạng thái chấm công của chính họ, không lộ số liệu toàn công ty."""

    def __init__(self, user, goto_attendance):
        super().__init__()
        self.user = user
        self.goto_attendance = goto_attendance
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        greet_box = QVBoxLayout()
        hello = QLabel(f"Xin chào, {self.user.get('full_name', '')}!")
        hello.setFont(QFont("Segoe UI", 18, QFont.Bold))
        sub = QLabel(f"Mã nhân viên: {self.user.get('ma_nv', '')}")
        sub.setStyleSheet("color:#64748B;")
        greet_box.addWidget(hello)
        greet_box.addWidget(sub)
        header.addLayout(greet_box)
        header.addStretch()

        clock_box = QVBoxLayout()
        clock_box.setAlignment(Qt.AlignRight)
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("color:#64748B;")
        self.date_lbl.setAlignment(Qt.AlignRight)
        self.time_lbl = QLabel()
        self.time_lbl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.time_lbl.setAlignment(Qt.AlignRight)
        clock_box.addWidget(self.date_lbl)
        clock_box.addWidget(self.time_lbl)
        header.addLayout(clock_box)
        root.addLayout(header)

        status_card = QFrame()
        status_card.setObjectName("card")
        status_l = QVBoxLayout(status_card)
        status_title = QLabel("Chấm công hôm nay")
        status_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        status_l.addWidget(status_title)

        self.status_lbl = QLabel("—")
        self.status_lbl.setFont(QFont("Segoe UI", 14, QFont.Bold))
        status_l.addWidget(self.status_lbl)

        self.detail_lbl = QLabel("")
        self.detail_lbl.setStyleSheet("color:#64748B;")
        status_l.addWidget(self.detail_lbl)

        go_btn = QPushButton("Đi tới Chấm công →")
        go_btn.setObjectName("primaryBtn")
        go_btn.clicked.connect(self.goto_attendance)
        status_l.addWidget(go_btn)
        status_l.addStretch()
        root.addWidget(status_card)
        root.addStretch()

    def _tick(self):
        now = datetime.now()
        self.date_lbl.setText(f"{WEEKDAYS_VN[now.weekday()]}, {now.strftime('%d/%m/%Y')}")
        self.time_lbl.setText(now.strftime("%H:%M:%S"))

    def refresh(self):
        ma_nv = self.user.get("ma_nv")
        att = db.get_today_attendance(ma_nv) if ma_nv else None
        if not att:
            self.status_lbl.setText("Chưa chấm công vào")
            self.status_lbl.setStyleSheet("color:#DC2626;")
            self.detail_lbl.setText("Hãy sang mục Chấm công và đưa mặt vào camera.")
        elif not att["gio_ra"]:
            self.status_lbl.setText(f"Đã chấm công vào lúc {att['gio_vao']}")
            self.status_lbl.setStyleSheet("color:#16A34A;")
            self.detail_lbl.setText(f"Trạng thái: {att['trang_thai']}. Đừng quên chấm công ra khi về.")
        else:
            self.status_lbl.setText(f"Đã chấm công đủ: {att['gio_vao']} → {att['gio_ra']}")
            self.status_lbl.setStyleSheet("color:#16A34A;")
            self.detail_lbl.setText(f"Trạng thái: {att['trang_thai']}")

    def showEvent(self, event):
        self.refresh()
        super().showEvent(event)
